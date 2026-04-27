"""
安全沙箱与权限系统 - Docker隔离与审计
支持：细粒度权限控制、资源限制、审计日志、敏感信息检测、沙箱隔离
"""

import os
import re
import json
import time
import hashlib
import logging
import subprocess
import tempfile
import signal
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
from functools import wraps
import threading

# 尝试导入resource模块（Unix/Linux）
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False
    resource = None

# 尝试导入docker
try:
    import docker
    from docker.errors import DockerException
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False
    docker = None
    DockerException = Exception


class PermissionLevel(Enum):
    """权限等级"""
    NONE = "none"           # 无权限
    READONLY = "readonly"   # 只读
    LIMITED = "limited"     # 受限
    STANDARD = "standard"   # 标准
    ELEVATED = "elevated"   # 提升
    ADMIN = "admin"         # 管理员


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    TIME = "time"


class AuditEventType(Enum):
    """审计事件类型"""
    CODE_EXECUTION = "code_execution"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    API_CALL = "api_call"
    PERMISSION_CHANGE = "permission_change"
    RESOURCE_USAGE = "resource_usage"
    SECURITY_ALERT = "security_alert"


@dataclass
class PermissionPolicy:
    """权限策略"""
    file_read: bool = True
    file_write: bool = False
    file_paths: List[str] = field(default_factory=list)  # 允许访问的路径
    network_access: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    code_execution: bool = True
    allowed_languages: List[str] = field(default_factory=lambda: ["python"])
    max_execution_time: int = 30  # 秒
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    allow_shell: bool = False
    allow_subprocess: bool = False
    allow_imports: List[str] = field(default_factory=list)  # 允许导入的模块
    blocked_imports: List[str] = field(default_factory=lambda: ["os.system", "subprocess"])


@dataclass
class ResourceLimits:
    """资源限制"""
    max_cpu_time: int = 30  # CPU时间限制（秒）
    max_memory_mb: int = 512  # 内存限制（MB）
    max_processes: int = 10  # 最大进程数
    max_file_size_mb: int = 100  # 最大文件大小
    max_open_files: int = 100  # 最大打开文件数
    max_network_connections: int = 0  # 最大网络连接数


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    timestamp: float
    event_type: AuditEventType
    user_id: Optional[str]
    session_id: str
    action: str
    resource: str
    status: str  # success, failure, blocked
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0  # 风险评分 0-100


@dataclass
class SecurityAlert:
    """安全告警"""
    alert_id: str
    timestamp: float
    severity: str  # low, medium, high, critical
    category: str  # injection, leak, bypass, anomaly
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""


class SensitiveInfoDetector:
    """敏感信息检测器"""
    
    # 敏感信息模式
    PATTERNS = {
        "api_key": [
            r'[a-zA-Z0-9]{32,}',  # 通用API密钥
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI API密钥
            r'AK[0-9A-Z]{16,}',  # 阿里云AccessKey
        ],
        "password": [
            r'password\s*[=:]\s*["\'][^"\']+["\']',
            r'passwd\s*[=:]\s*["\'][^"\']+["\']',
            r'pwd\s*[=:]\s*["\'][^"\']+["\']',
        ],
        "secret": [
            r'secret[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
            r'private[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
        ],
        "token": [
            r'token\s*[=:]\s*["\'][^"\']{20,}["\']',
            r'access[_-]?token\s*[=:]\s*["\'][^"\']+["\']',
        ],
        "credit_card": [
            r'\b4[0-9]{12}(?:[0-9]{3})?\b',  # Visa
            r'\b5[1-5][0-9]{14}\b',  # MasterCard
        ],
        "email": [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        "phone": [
            r'1[3-9]\d{9}',  # 中国手机号
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # 国际电话
        ]
    }
    
    def scan_text(self, text: str) -> List[Dict[str, Any]]:
        """扫描文本中的敏感信息"""
        findings = []
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    finding = {
                        "category": category,
                        "pattern": pattern,
                        "matched_text": match.group(),
                        "position": (match.start(), match.end()),
                        "risk_level": self._assess_risk(category, match.group())
                    }
                    findings.append(finding)
        
        return findings
    
    def scan_file(self, file_path: str) -> List[Dict[str, Any]]:
        """扫描文件中的敏感信息"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            findings = self.scan_text(content)
            
            # 添加文件信息
            for finding in findings:
                finding["file_path"] = file_path
            
            return findings
        except Exception as e:
            return [{"error": str(e), "file_path": file_path}]
    
    def _assess_risk(self, category: str, matched_text: str) -> str:
        """评估风险等级"""
        high_risk = ["api_key", "secret", "password", "token"]
        medium_risk = ["credit_card", "email"]
        
        if category in high_risk:
            # 检查是否是示例/占位符
            if any(x in matched_text.lower() for x in ["example", "test", "placeholder", "xxx"]):
                return "low"
            return "high"
        elif category in medium_risk:
            return "medium"
        return "low"
    
    def mask_sensitive_info(self, text: str) -> str:
        """脱敏处理"""
        masked = text
        
        for category, patterns in self.PATTERNS.items():
            for pattern in patterns:
                def mask_match(match):
                    matched = match.group()
                    if len(matched) <= 8:
                        return "***"
                    return matched[:4] + "***" + matched[-4:]
                
                masked = re.sub(pattern, mask_match, masked, flags=re.IGNORECASE)
        
        return masked


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_dir: str = "audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置日志文件
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        
        # 内存中的事件缓存
        self.event_cache: List[AuditEvent] = []
        self.cache_lock = threading.Lock()
        self.max_cache_size = 10000
    
    def log_event(self, event: AuditEvent):
        """记录审计事件"""
        # 写入文件
        event_dict = asdict(event)
        self.logger.info(json.dumps(event_dict, ensure_ascii=False))
        
        # 添加到缓存
        with self.cache_lock:
            self.event_cache.append(event)
            if len(self.event_cache) > self.max_cache_size:
                self.event_cache = self.event_cache[-self.max_cache_size:]
    
    def query_events(self, start_time: float = None, end_time: float = None,
                     event_type: AuditEventType = None, user_id: str = None,
                     limit: int = 100) -> List[AuditEvent]:
        """查询审计事件"""
        with self.cache_lock:
            events = self.event_cache.copy()
        
        # 过滤
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        return events[-limit:]
    
    def get_statistics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """获取审计统计"""
        cutoff_time = time.time() - (time_range_hours * 3600)
        
        with self.cache_lock:
            recent_events = [e for e in self.event_cache if e.timestamp >= cutoff_time]
        
        stats = {
            "total_events": len(recent_events),
            "event_types": {},
            "users": {},
            "success_rate": 0,
            "high_risk_events": 0
        }
        
        for event in recent_events:
            # 事件类型统计
            event_type = event.event_type.value
            stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
            
            # 用户统计
            if event.user_id:
                stats["users"][event.user_id] = stats["users"].get(event.user_id, 0) + 1
            
            # 高风险事件
            if event.risk_score > 70:
                stats["high_risk_events"] += 1
        
        # 成功率
        if recent_events:
            success_count = sum(1 for e in recent_events if e.status == "success")
            stats["success_rate"] = success_count / len(recent_events)
        
        return stats


class DockerSandbox:
    """Docker沙箱执行环境"""
    
    def __init__(self, image: str = "python:3.9-slim"):
        self.image = image
        self.client = None
        self.containers: Dict[str, Any] = {}
        
        try:
            self.client = docker.from_env()
        except DockerException:
            print("警告: Docker未安装或未运行")
    
    def create_container(self, container_id: str = None, 
                         resource_limits: ResourceLimits = None) -> str:
        """创建隔离容器"""
        if not self.client:
            raise Exception("Docker未可用")
        
        container_id = container_id or f"sandbox_{int(time.time())}"
        
        # 资源限制
        mem_limit = f"{resource_limits.max_memory_mb}m" if resource_limits else "512m"
        cpu_limit = resource_limits.max_cpu_percent / 100 if resource_limits else 0.5
        
        try:
            container = self.client.containers.run(
                self.image,
                name=container_id,
                command="sleep 3600",  # 保持运行1小时
                detach=True,
                mem_limit=mem_limit,
                cpu_quota=int(cpu_limit * 100000),
                cpu_period=100000,
                network_mode="none",  # 禁用网络
                read_only=True,  # 只读根文件系统
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],  # 丢弃所有能力
                pids_limit=resource_limits.max_processes if resource_limits else 10,
                stdin_open=True,
                tty=True
            )
            
            self.containers[container_id] = container
            return container_id
            
        except Exception as e:
            raise Exception(f"创建容器失败: {e}")
    
    def execute_code(self, container_id: str, code: str, 
                     language: str = "python", timeout: int = 30) -> Dict[str, Any]:
        """在容器中执行代码"""
        if container_id not in self.containers:
            raise Exception(f"容器 {container_id} 不存在")
        
        container = self.containers[container_id]
        
        # 根据语言选择执行命令
        if language == "python":
            cmd = ["python", "-c", code]
        elif language == "bash":
            cmd = ["bash", "-c", code]
        else:
            cmd = [language, "-c", code]
        
        try:
            result = container.exec_run(
                cmd,
                stdout=True,
                stderr=True,
                timeout=timeout
            )
            
            return {
                "exit_code": result.exit_code,
                "stdout": result.output.decode('utf-8', errors='replace') if result.output else "",
                "stderr": "",
                "success": result.exit_code == 0
            }
            
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }
    
    def destroy_container(self, container_id: str):
        """销毁容器"""
        if container_id in self.containers:
            try:
                container = self.containers[container_id]
                container.stop()
                container.remove(force=True)
                del self.containers[container_id]
            except Exception as e:
                print(f"销毁容器失败: {e}")
    
    def cleanup_all(self):
        """清理所有容器"""
        for container_id in list(self.containers.keys()):
            self.destroy_container(container_id)


class SecureCodeExecutor:
    """安全代码执行器"""
    
    def __init__(self, use_docker: bool = False):
        self.use_docker = use_docker
        self.docker_sandbox = DockerSandbox() if use_docker else None
        self.sensitive_detector = SensitiveInfoDetector()
        self.audit_logger = AuditLogger()
        
        # 默认权限策略
        self.default_policy = PermissionPolicy()
        
        # 资源限制
        self.default_limits = ResourceLimits()
    
    def execute(self, code: str, language: str = "python",
                policy: PermissionPolicy = None, 
                user_id: str = None,
                session_id: str = None) -> Dict[str, Any]:
        """
        安全执行代码
        
        Args:
            code: 要执行的代码
            language: 编程语言
            policy: 权限策略
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            执行结果
        """
        policy = policy or self.default_policy
        session_id = session_id or f"session_{int(time.time())}"
        
        # 步骤1: 敏感信息检测
        sensitive_findings = self.sensitive_detector.scan_text(code)
        if sensitive_findings:
            high_risk = [f for f in sensitive_findings if f["risk_level"] == "high"]
            if high_risk:
                # 记录安全告警
                alert = SecurityAlert(
                    alert_id=f"alert_{int(time.time())}",
                    timestamp=time.time(),
                    severity="high",
                    category="leak",
                    description=f"检测到{len(high_risk)}个高风险敏感信息",
                    evidence={"findings": high_risk}
                )
                
                # 记录审计事件
                event = AuditEvent(
                    event_id=f"evt_{int(time.time())}",
                    timestamp=time.time(),
                    event_type=AuditEventType.SECURITY_ALERT,
                    user_id=user_id,
                    session_id=session_id,
                    action="code_execution_blocked",
                    resource="code",
                    status="blocked",
                    details={"alert": asdict(alert)},
                    risk_score=90.0
                )
                self.audit_logger.log_event(event)
                
                return {
                    "success": False,
                    "error": "代码包含敏感信息，执行被阻止",
                    "findings": sensitive_findings,
                    "alert": asdict(alert)
                }
        
        # 步骤2: 代码安全检查
        security_check = self._security_check(code, policy)
        if not security_check["passed"]:
            event = AuditEvent(
                event_id=f"evt_{int(time.time())}",
                timestamp=time.time(),
                event_type=AuditEventType.CODE_EXECUTION,
                user_id=user_id,
                session_id=session_id,
                action="code_execution_blocked",
                resource="code",
                status="blocked",
                details={"reason": security_check["reason"]},
                risk_score=80.0
            )
            self.audit_logger.log_event(event)
            
            return {
                "success": False,
                "error": security_check["reason"]
            }
        
        # 步骤3: 执行代码
        start_time = time.time()
        
        try:
            if self.use_docker and self.docker_sandbox:
                result = self._execute_in_docker(code, language, policy)
            else:
                result = self._execute_in_subprocess(code, language, policy)
            
            execution_time = time.time() - start_time
            
            # 记录成功事件
            event = AuditEvent(
                event_id=f"evt_{int(time.time())}",
                timestamp=time.time(),
                event_type=AuditEventType.CODE_EXECUTION,
                user_id=user_id,
                session_id=session_id,
                action="code_execution",
                resource="code",
                status="success" if result["success"] else "failure",
                details={
                    "language": language,
                    "execution_time": execution_time,
                    "code_size": len(code)
                },
                risk_score=10.0 if result["success"] else 50.0
            )
            self.audit_logger.log_event(event)
            
            result["execution_time"] = execution_time
            return result
            
        except Exception as e:
            # 记录失败事件
            event = AuditEvent(
                event_id=f"evt_{int(time.time())}",
                timestamp=time.time(),
                event_type=AuditEventType.CODE_EXECUTION,
                user_id=user_id,
                session_id=session_id,
                action="code_execution",
                resource="code",
                status="failure",
                details={"error": str(e)},
                risk_score=60.0
            )
            self.audit_logger.log_event(event)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _security_check(self, code: str, policy: PermissionPolicy) -> Dict[str, Any]:
        """安全检查"""
        # 检查禁止的导入
        for blocked in policy.blocked_imports:
            if blocked in code:
                return {
                    "passed": False,
                    "reason": f"代码包含禁止的导入: {blocked}"
                }
        
        # 检查Shell命令
        if not policy.allow_shell:
            shell_patterns = [
                r'os\.system\s*\(',
                r'subprocess\.call\s*\(',
                r'subprocess\.run\s*\(',
                r'eval\s*\(',
                r'exec\s*\(',
            ]
            for pattern in shell_patterns:
                if re.search(pattern, code):
                    return {
                        "passed": False,
                        "reason": "代码包含危险的系统调用"
                    }
        
        # 检查语言支持
        if policy.allowed_languages and language not in policy.allowed_languages:
            return {
                "passed": False,
                "reason": f"不支持的语言: {language}"
            }
        
        return {"passed": True}
    
    def _execute_in_subprocess(self, code: str, language: str, 
                                policy: PermissionPolicy) -> Dict[str, Any]:
        """在子进程中执行代码"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 设置资源限制（仅在Unix/Linux系统）
            kwargs = {}
            if HAS_RESOURCE:
                def set_limits():
                    # CPU时间限制
                    resource.setrlimit(resource.RLIMIT_CPU, 
                                     (policy.max_execution_time, policy.max_execution_time + 1))
                    # 内存限制
                    max_memory = policy.max_memory_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
                    # 进程数限制
                    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
                kwargs['preexec_fn'] = set_limits
            
            # 执行代码
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=policy.max_execution_time,
                **kwargs
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"执行超时（超过{policy.max_execution_time}秒）"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            os.unlink(temp_file)
    
    def _execute_in_docker(self, code: str, language: str, 
                           policy: PermissionPolicy) -> Dict[str, Any]:
        """在Docker中执行代码"""
        if not self.docker_sandbox:
            return {
                "success": False,
                "error": "Docker沙箱未启用"
            }
        
        container_id = None
        try:
            # 创建容器
            limits = ResourceLimits(
                max_cpu_time=policy.max_execution_time,
                max_memory_mb=policy.max_memory_mb
            )
            container_id = self.docker_sandbox.create_container(
                resource_limits=limits
            )
            
            # 执行代码
            result = self.docker_sandbox.execute_code(
                container_id, code, language, policy.max_execution_time
            )
            
            return result
            
        finally:
            if container_id:
                self.docker_sandbox.destroy_container(container_id)


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.user_policies: Dict[str, PermissionPolicy] = {}
        self.role_policies: Dict[str, PermissionPolicy] = {
            "guest": PermissionPolicy(
                file_read=True,
                file_write=False,
                network_access=False,
                code_execution=True,
                max_execution_time=10,
                max_memory_mb=128
            ),
            "user": PermissionPolicy(
                file_read=True,
                file_write=True,
                file_paths=["/tmp", "/home/user"],
                network_access=True,
                allowed_hosts=["api.openai.com", "github.com"],
                code_execution=True,
                max_execution_time=30,
                max_memory_mb=512
            ),
            "developer": PermissionPolicy(
                file_read=True,
                file_write=True,
                network_access=True,
                code_execution=True,
                allow_shell=True,
                allow_subprocess=True,
                max_execution_time=60,
                max_memory_mb=1024
            ),
            "admin": PermissionPolicy(
                file_read=True,
                file_write=True,
                network_access=True,
                code_execution=True,
                allow_shell=True,
                allow_subprocess=True,
                max_execution_time=300,
                max_memory_mb=2048
            )
        }
    
    def get_policy(self, user_id: str, role: str = None) -> PermissionPolicy:
        """获取用户权限策略"""
        if user_id in self.user_policies:
            return self.user_policies[user_id]
        
        if role and role in self.role_policies:
            return self.role_policies[role]
        
        return self.role_policies["guest"]
    
    def set_user_policy(self, user_id: str, policy: PermissionPolicy):
        """设置用户权限策略"""
        self.user_policies[user_id] = policy
    
    def check_permission(self, user_id: str, action: str, 
                         resource: str, role: str = None) -> bool:
        """检查权限"""
        policy = self.get_policy(user_id, role)
        
        if action == "file_read":
            return policy.file_read
        elif action == "file_write":
            return policy.file_write
        elif action == "network_access":
            return policy.network_access
        elif action == "code_execution":
            return policy.code_execution
        elif action == "shell":
            return policy.allow_shell
        
        return False


# ==================== 装饰器 ====================

def require_permission(action: str, resource: str):
    """权限检查装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取权限管理器
            permission_manager = kwargs.get('permission_manager') or PermissionManager()
            user_id = kwargs.get('user_id')
            role = kwargs.get('role')
            
            if not permission_manager.check_permission(user_id, action, resource, role):
                raise PermissionError(f"用户 {user_id} 没有 {action} 权限")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def audit_log(event_type: AuditEventType):
    """审计日志装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取审计日志记录器
            audit_logger = kwargs.get('audit_logger') or AuditLogger()
            user_id = kwargs.get('user_id')
            session_id = kwargs.get('session_id')
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                status = "success"
                error = None
                return result
            except Exception as e:
                status = "failure"
                error = str(e)
                raise
            finally:
                # 记录审计事件
                event = AuditEvent(
                    event_id=f"evt_{int(time.time())}",
                    timestamp=time.time(),
                    event_type=event_type,
                    user_id=user_id,
                    session_id=session_id,
                    action=func.__name__,
                    resource=resource,
                    status=status,
                    details={"error": error} if error else {},
                    risk_score=0.0
                )
                audit_logger.log_event(event)
        
        return wrapper
    return decorator


# ==================== 便捷函数 ====================

def secure_execute(code: str, language: str = "python", 
                   user_id: str = None, role: str = "guest") -> Dict[str, Any]:
    """便捷的安全执行函数"""
    executor = SecureCodeExecutor(use_docker=False)
    
    permission_manager = PermissionManager()
    policy = permission_manager.get_policy(user_id, role)
    
    return executor.execute(
        code=code,
        language=language,
        policy=policy,
        user_id=user_id
    )


def scan_code_security(code: str) -> List[Dict[str, Any]]:
    """扫描代码安全性"""
    detector = SensitiveInfoDetector()
    return detector.scan_text(code)


if __name__ == "__main__":
    # 测试代码
    print("安全沙箱系统测试")
    
    # 测试敏感信息检测
    test_code = """
api_key = "sk-1234567890abcdef1234567890abcdef"
password = "my_secret_password_123"
"""
    
    findings = scan_code_security(test_code)
    print(f"\n检测到 {len(findings)} 个敏感信息:")
    for finding in findings:
        print(f"  - {finding['category']}: {finding['risk_level']}")
    
    # 测试安全执行
    safe_code = """
print("Hello, World!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
    
    print("\n执行安全代码:")
    result = secure_execute(safe_code, user_id="test_user")
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"输出: {result['stdout']}")
    else:
        print(f"错误: {result.get('error')}")
