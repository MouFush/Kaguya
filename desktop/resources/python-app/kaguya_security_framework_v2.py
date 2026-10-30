#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 企业级综合安全框架 (重构版)
Kaguya AI Security Framework - Enterprise Grade (Refactored)

使用 kaguya_core 框架重构，减少代码重复
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
from urllib.parse import urlparse

# 导入 kaguya_core 框架
from kaguya_core import (
    BaseManager, SingletonMixin, get_config, get_logger,
    generate_id, timestamp_now, validate_email, ValidationError
)
from kaguya_core.models import User, Session, APIKey
from kaguya_core.exceptions import AuthenticationError, AuthorizationError

# 尝试导入加密库
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


# ==================== 枚举定义 ====================

class SecurityLevel(Enum):
    """安全等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """安全事件类型"""
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    ACCESS_DENIED = "access_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_VIOLATION = "csrf_violation"
    ACCOUNT_LOCKOUT = "account_lockout"


# ==================== 核心安全服务 ====================

class PasswordManager:
    """密码管理器 - 符合NIST SP 800-63B标准"""

    def __init__(self):
        self.config = get_config()
        self._common_passwords = self._load_common_passwords()
        self.logger = get_logger('PasswordManager')

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
        min_length = self.config.get('security.password_min_length', 12)

        if len(password) < min_length:
            errors.append(f"密码长度至少{min_length}位")

        if self.config.get('security.password_require_uppercase', True):
            if not re.search(r'[A-Z]', password):
                errors.append("密码必须包含大写字母")

        if self.config.get('security.password_require_lowercase', True):
            if not re.search(r'[a-z]', password):
                errors.append("密码必须包含小写字母")

        if self.config.get('security.password_require_digit', True):
            if not re.search(r'\d', password):
                errors.append("密码必须包含数字")

        if self.config.get('security.password_require_special', True):
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
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


class JWTManager:
    """JWT令牌管理器"""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret = secret_key or secrets.token_hex(32)
        self.algorithm = 'HS256'
        self.config = get_config()

    def generate_token(self, user_id: str, claims: Dict = None,
                       expiry_hours: int = None) -> str:
        """生成JWT令牌"""
        if expiry_hours is None:
            expiry_hours = self.config.get('security.jwt_expiry_hours', 24)

        try:
            import jwt
            payload = {
                'sub': user_id,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
                **(claims or {})
            }
            return jwt.encode(payload, self.secret, algorithm=self.algorithm)
        except ImportError:
            # 简化实现
            header = json.dumps({'alg': 'none', 'typ': 'JWT'})
            payload = {
                'sub': user_id,
                'iat': timestamp_now(),
                'exp': (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat(),
                'claims': claims or {}
            }

            header_b64 = base64.urlsafe_b64encode(header.encode()).decode().rstrip('=')
            payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

            signature = hmac.new(
                self.secret.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).hexdigest()

            return f"{header_b64}.{payload_b64}.{signature}"

    def verify_token(self, token: str) -> Optional[Dict]:
        """验证JWT令牌"""
        try:
            import jwt
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except ImportError:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            try:
                payload_json = base64.urlsafe_b64decode(parts[1] + '==').decode()
                payload = json.loads(payload_json)

                exp = datetime.fromisoformat(payload['exp'])
                if exp < datetime.utcnow():
                    return None

                return payload
            except:
                return None
        except Exception:
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
        self.logger = get_logger('InputValidator')

    def sanitize_sql(self, value: str) -> str:
        """SQL注入防护"""
        for pattern in self.sql_patterns:
            if pattern.search(value):
                self.logger.warning(f"检测到SQL注入尝试: {value[:50]}...")
                raise ValidationError("检测到SQL注入攻击", field="input")

        return value.replace("'", "''").replace("\\", "\\\\")

    def sanitize_html(self, value: str) -> str:
        """XSS防护"""
        for pattern in self.xss_patterns:
            if pattern.search(value):
                self.logger.warning(f"检测到XSS尝试: {value[:50]}...")
                raise ValidationError("检测到XSS攻击", field="input")

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
                raise ValidationError("检测到路径遍历攻击", field="path")

        normalized = os.path.normpath(path)
        if normalized.startswith('..'):
            raise ValidationError("非法路径访问", field="path")

        return normalized


# ==================== 认证与授权管理器 (重构后) ====================

class AuthenticationManager(BaseManager):
    """
    认证管理器 - 使用 BaseManager 重构

    改进点:
    - 继承 BaseManager 获得统一初始化流程
    - 使用 get_logger() 替代手动日志设置
    - 使用 generate_id() 替代 uuid
    - 使用 timestamp_now() 替代 datetime
    """

    def __init__(self, db_path: str = None):
        # 先调用父类初始化
        config = get_config()
        super().__init__(config.to_dict())

        self.db_path = db_path or os.path.join(
            config.get('data_dir', './data'),
            'security.db'
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager()
        self.validator = InputValidator()

        self._sessions: Dict[str, Session] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._lock = threading.Lock()

    async def _do_initialize(self) -> None:
        """初始化逻辑 - 替代原来的 initialize"""
        self.logger.info("🔐 初始化认证管理器...")
        self._init_database()
        self.logger.info("✅ 认证管理器初始化完成")

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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
        is_valid, errors = self.password_manager.validate_password(password, user_info)
        if not is_valid:
            return False, f"密码不符合要求: {', '.join(errors)}"

        password_hash, salt = self.password_manager.hash_password(password)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO user_credentials
                (user_id, password_hash, salt, last_password_change)
                VALUES (?, ?, ?, ?)
            ''', (user_id, password_hash, salt, timestamp_now()))
            conn.commit()
            self.logger.info(f"用户注册成功: {user_id}")
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
            self.logger.warning(f"认证失败: 用户不存在 {user_id}")
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
            self.logger.warning(f"认证失败: 密码错误 {user_id}")

            if failed_attempts + 1 >= self.config.get('security.max_login_attempts', 5):
                self._lock_account(user_id)
                return False, "登录失败次数过多，账户已锁定", {}

            return False, "用户名或密码错误", {}

        # 重置失败次数
        self._reset_failed_attempts(user_id)

        # 生成会话
        session = self._create_session(user_id, ip_address, user_agent)

        self.logger.info(f"认证成功: {user_id}")

        return True, "认证成功", {
            'session_id': session.id,
            'access_token': self.jwt_manager.generate_token(user_id),
            'refresh_token': secrets.token_urlsafe(32),
            'expires_at': session.expires_at
        }

    def _create_session(self, user_id: str, ip_address: str = None,
                        user_agent: str = None) -> Session:
        """创建会话 - 使用统一模型"""
        expires = datetime.utcnow() + timedelta(
            hours=self.config.get('security.session_timeout_hours', 24)
        )

        session = Session(
            id=generate_id("sess_"),
            user_id=user_id,
            created_at=timestamp_now(),
            expires_at=expires.isoformat(),
            ip_address=ip_address or '',
            user_agent=user_agent or ''
        )

        with self._lock:
            self._sessions[session.id] = session

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

    def _lock_account(self, user_id: str):
        """锁定账户"""
        lock_until = (datetime.utcnow() + timedelta(
            minutes=self.config.get('security.lockout_duration_minutes', 30)
        )).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_credentials SET locked_until = ? WHERE user_id = ?
        ''', (lock_until, user_id))
        conn.commit()
        conn.close()

        self.logger.warning(f"账户已锁定: {user_id}")


# ==================== 全局实例 ====================

_security_manager: Optional[AuthenticationManager] = None


def get_authentication_manager() -> AuthenticationManager:
    """获取认证管理器实例（单例）"""
    global _security_manager
    if _security_manager is None:
        _security_manager = AuthenticationManager()
    return _security_manager


# ==================== 测试 ====================

if __name__ == '__main__':
    import asyncio

    async def test():
        print("=" * 70)
        print("🧪 测试重构后的安全框架")
        print("=" * 70)

        auth = get_authentication_manager()
        await auth.initialize()

        # 测试用户注册
        print("\n1. 测试用户注册")
        success, msg = auth.register_user(
            "test_user",
            "SecureP@ssw0rd123!",
            {"username": "test_user", "email": "test@example.com"}
        )
        print(f"   注册: {msg}")

        # 测试认证
        print("\n2. 测试用户认证")
        success, msg, data = auth.authenticate(
            "test_user",
            "SecureP@ssw0rd123!",
            ip_address="192.168.1.1"
        )
        print(f"   认证: {msg}")
        if success:
            print(f"   Token: {data.get('access_token', '')[:50]}...")

        # 测试健康检查
        print("\n3. 健康检查")
        health = auth.health_check()
        print(f"   状态: {health}")

        print("\n" + "=" * 70)
        print("✅ 测试完成！")
        print("=" * 70)

    asyncio.run(test())
