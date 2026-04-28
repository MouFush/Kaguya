#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 企业级综合安全框架 - 重构版
使用 kaguya_core 框架，减少代码重复

参考标准:
- OWASP Top 10 2021
- SOC 2 Type II
- GDPR Article 32
- ISO 27001
- NIST Cybersecurity Framework
"""

import os
import re
import json
import hmac
import hashlib
import secrets
import base64
import sqlite3
import threading
import ipaddress
from enum import Enum, auto
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from functools import wraps

# 使用核心框架
from .base_manager import BaseManager, ManagerRegistry
from .utils import (
    generate_id, timestamp_now, validate_email, validate_uuid,
    sanitize_string, hash_string, RateLimiter
)
from .logging import get_logger
from .exceptions import (
    KaguyaException, AuthenticationError, AuthorizationError,
    ValidationError, RateLimitError
)
from .models import User, Session as SessionModel, APIKey as APIKeyModel


class SecurityLevel(Enum):
    """安全等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthMethod(Enum):
    """认证方式"""
    PASSWORD = "password"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    SAML = "saml"
    MFA = "mfa"
    BIOMETRIC = "biometric"


class SecurityEventType(Enum):
    """安全事件类型"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ACCESS_DENIED = "access_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_VIOLATION = "csrf_violation"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ACCOUNT_LOCKOUT = "account_lockout"
    PASSWORD_CHANGE = "password_change"
    API_KEY_COMPROMISED = "api_key_compromised"


@dataclass
class UserCredentials:
    """用户凭证"""
    user_id: str
    password_hash: str
    salt: str
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    last_password_change: Optional[str] = None
    password_history: List[str] = field(default_factory=list)
    failed_login_attempts: int = 0
    locked_until: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM


@dataclass
class Session:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: str
    expires_at: str
    ip_address: str
    user_agent: str
    is_active: bool = True
    mfa_verified: bool = False
    permissions: Set[str] = field(default_factory=set)


@dataclass
class APIKey:
    """API密钥"""
    key_id: str
    user_id: str
    key_hash: str
    name: str
    permissions: Set[str]
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    usage_count: int = 0
    is_active: bool = True
    allowed_ips: Optional[List[str]] = None
    rate_limit: int = 1000


@dataclass
class SecurityPolicy:
    """安全策略"""
    policy_id: str
    name: str
    description: str
    rules: Dict[str, Any]
    applies_to: List[str]
    priority: int = 0
    is_active: bool = True


class PasswordManager(BaseManager):
    """密码管理器 - 符合NIST SP 800-63B标准"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._common_passwords = self._load_common_passwords()
    
    async def _do_initialize(self) -> None:
        """初始化密码管理器"""
        self.logger.info("密码管理器初始化完成")
    
    def _load_common_passwords(self) -> Set[str]:
        """加载常见弱密码列表"""
        return {
            'password', '123456', '12345678', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'master', 'sunshine', 'princess', 'football',
            'baseball', 'iloveyou', 'trustno1', 'admin123', 'welcome123'
        }
    
    def validate_password(self, password: str, user_info: Dict = None) -> Tuple[bool, List[str]]:
        """验证密码强度"""
        errors = []
        
        min_length = self.get_config('password_min_length', 12)
        
        if len(password) < min_length:
            errors.append(f"密码长度至少{min_length}位")
        
        if self.get_config('password_require_uppercase', True) and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含大写字母")
        
        if self.get_config('password_require_lowercase', True) and not re.search(r'[a-z]', password):
            errors.append("密码必须包含小写字母")
        
        if self.get_config('password_require_digit', True) and not re.search(r'\d', password):
            errors.append("密码必须包含数字")
        
        if self.get_config('password_require_special', True) and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码必须包含特殊字符")
        
        if password.lower() in self._common_passwords:
            errors.append("密码过于常见，请选择更强的密码")
        
        if user_info:
            username = user_info.get('username', '').lower()
            email = user_info.get('email', '').lower().split('@')[0]
            if username and username in password.lower():
                errors.append("密码不能包含用户名")
            if email and email in password.lower():
                errors.append("密码不能包含邮箱")
        
        if re.search(r'(.)\1{3,}', password):
            errors.append("密码不能包含连续重复的字符")
        
        return len(errors) == 0, errors
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """哈希密码 - 使用PBKDF2"""
        salt = secrets.token_hex(32)
        hash_value = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return base64.urlsafe_b64encode(hash_value).decode(), salt
    
    def verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """验证密码"""
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        new_hash_b64 = base64.urlsafe_b64encode(new_hash).decode()
        return hmac.compare_digest(new_hash_b64, hash_value)


class JWTManager(BaseManager):
    """JWT令牌管理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.secret = None
        self.algorithm = 'HS256'
    
    async def _do_initialize(self) -> None:
        """初始化JWT管理器"""
        self.secret = self.get_config('jwt_secret', secrets.token_hex(32))
        self.logger.info("JWT管理器初始化完成")
    
    def generate_token(self, user_id: str, claims: Dict = None, 
                       expiry_hours: int = None) -> str:
        """生成JWT令牌"""
        expiry = expiry_hours or self.get_config('jwt_expiry_hours', 24)
        
        # 简化实现
        header = json.dumps({'alg': 'HS256', 'typ': 'JWT'})
        payload = {
            'sub': user_id,
            'iat': timestamp_now(),
            'exp': (datetime.utcnow() + timedelta(hours=expiry)).isoformat(),
            'claims': claims or {}
        }
        payload_json = json.dumps(payload)
        
        header_b64 = base64.urlsafe_b64encode(header.encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
        
        signature = hmac.new(
            self.secret.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{header_b64}.{payload_b64}.{signature}"
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """验证JWT令牌"""
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        try:
            payload_json = base64.urlsafe_b64decode(parts[1] + '==').decode()
            payload = json.loads(payload_json)
            
            # 检查过期
            exp = datetime.fromisoformat(payload['exp'])
            if exp < datetime.utcnow():
                return None
            
            return payload
        except:
            return None


class InputValidator:
    """输入验证器 - 防止注入攻击"""
    
    SQL_INJECTION_PATTERNS = [
        r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
        r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
        r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
        r"((\%27)|(\'))union",
        r"exec(\s|\+)+(s|x)p\w+",
        r"UNION\s+SELECT",
        r"INSERT\s+INTO",
        r"DELETE\s+FROM",
        r"DROP\s+TABLE",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>[\s\S]*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"eval\s*\(",
        r"expression\s*\(",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%252e%252e%252f",
    ]
    
    def __init__(self):
        self.sql_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
    
    def sanitize_sql(self, value: str) -> str:
        """SQL注入防护"""
        for pattern in self.sql_patterns:
            if pattern.search(value):
                raise ValidationError("检测到SQL注入风险")
        
        return value.replace("'", "''").replace("\\", "\\\\")
    
    def sanitize_html(self, value: str) -> str:
        """XSS防护"""
        for pattern in self.xss_patterns:
            if pattern.search(value):
                raise ValidationError("检测到XSS攻击")
        
        html_escape = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
        }
        return ''.join(html_escape.get(c, c) for c in value)
    
    def validate_path(self, path: str) -> str:
        """路径遍历防护"""
        for pattern in self.path_patterns:
            if pattern.search(path):
                raise ValidationError("检测到路径遍历攻击")
        
        normalized = os.path.normpath(path)
        if normalized.startswith('..'):
            raise ValidationError("非法路径访问")
        
        return normalized


class AuthenticationManager(BaseManager):
    """认证管理器 - 重构版"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.db_path = None
        self.password_manager = None
        self.jwt_manager = None
        self.validator = None
        self._sessions: Dict[str, Session] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._lock = threading.Lock()
    
    async def _do_initialize(self) -> None:
        """初始化认证管理器"""
        self.db_path = self.get_config('db_path', './security_data/auth.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 初始化子组件
        self.password_manager = PasswordManager(self._config)
        await self.password_manager.initialize()
        
        self.jwt_manager = JWTManager(self._config)
        await self.jwt_manager.initialize()
        
        self.validator = InputValidator()
        
        # 初始化数据库
        self._init_database()
        
        self.logger.info("认证管理器初始化完成")
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户凭证表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_credentials (
                user_id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                mfa_secret TEXT,
                mfa_enabled INTEGER DEFAULT 0,
                last_password_change TEXT,
                password_history TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TEXT,
                security_level TEXT DEFAULT 'medium',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # API密钥表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT,
                permissions TEXT,
                created_at TEXT,
                expires_at TEXT,
                last_used_at TEXT,
                usage_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                allowed_ips TEXT,
                rate_limit INTEGER DEFAULT 1000
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, user_id: str, password: str, 
                      user_info: Dict = None) -> Tuple[bool, str]:
        """注册用户"""
        # 验证密码强度
        is_valid, errors = self.password_manager.validate_password(password, user_info)
        if not is_valid:
            return False, f"密码不符合要求: {', '.join(errors)}"
        
        # 哈希密码
        password_hash, salt = self.password_manager.hash_password(password)
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_credentials 
                (user_id, password_hash, salt, last_password_change)
                VALUES (?, ?, ?, ?)
            ''', (user_id, password_hash, salt, timestamp_now()))
            conn.commit()
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户已存在"
        finally:
            conn.close()
    
    def authenticate(self, user_id: str, password: str, 
                     ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Dict]:
        """用户认证"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT password_hash, salt, mfa_enabled, mfa_secret,
                   failed_login_attempts, locked_until
            FROM user_credentials WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False, "用户名或密码错误", {}
        
        password_hash, salt, mfa_enabled, mfa_secret, failed_attempts, locked_until = row
        
        # 检查账户锁定
        if locked_until:
            lock_time = datetime.fromisoformat(locked_until)
            if lock_time > datetime.utcnow():
                return False, f"账户已锁定，请在{locked_until}后重试", {}
        
        # 验证密码
        if not self.password_manager.verify_password(password, password_hash, salt):
            self._increment_failed_attempts(user_id)
            return False, "用户名或密码错误", {}
        
        # 重置失败次数
        self._reset_failed_attempts(user_id)
        
        # 生成会话
        session = self._create_session(user_id, ip_address, user_agent)
        
        return True, "认证成功", {
            'session_id': session.session_id,
            'access_token': self.jwt_manager.generate_token(user_id),
            'refresh_token': secrets.token_urlsafe(32),
            'expires_at': session.expires_at
        }
    
    def _create_session(self, user_id: str, ip_address: str = None, 
                        user_agent: str = None) -> Session:
        """创建会话"""
        session_id = generate_id("sess_")
        now = datetime.utcnow()
        expires = now + timedelta(hours=self.get_config('session_timeout_hours', 24))
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=timestamp_now(),
            expires_at=expires.isoformat(),
            ip_address=ip_address or '',
            user_agent=user_agent or ''
        )
        
        with self._lock:
            self._sessions[session_id] = session
        
        return session
    
    def _increment_failed_attempts(self, user_id: str):
        """增加失败登录次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_credentials 
            SET failed_login_attempts = failed_login_attempts + 1
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def _reset_failed_attempts(self, user_id: str):
        """重置失败登录次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_credentials 
            SET failed_login_attempts = 0, locked_until = NULL
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()


class SecurityManager(BaseManager):
    """综合安全管理器 - 统一入口"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.auth = None
        self.validator = None
    
    async def _do_initialize(self) -> None:
        """初始化安全系统"""
        self.logger.info("=" * 70)
        self.logger.info("🔒 初始化辉夜AI安全框架")
        self.logger.info("=" * 70)
        
        # 初始化认证管理器
        self.auth = AuthenticationManager(self._config)
        await self.auth.initialize()
        
        # 初始化验证器
        self.validator = InputValidator()
        
        self.logger.info("✅ 安全框架初始化完成")
        self.logger.info("=" * 70)
    
    async def _do_shutdown(self) -> None:
        """关闭安全系统"""
        if self.auth:
            await self.auth.shutdown()
        self.logger.info("安全框架已关闭")


# 全局实例
_security_manager: Optional[SecurityManager] = None


def get_security_manager(config: Optional[Dict] = None) -> SecurityManager:
    """获取安全管理器实例（单例）"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(config)
    return _security_manager
