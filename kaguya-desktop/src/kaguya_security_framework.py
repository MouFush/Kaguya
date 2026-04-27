#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 企业级综合安全框架
Kaguya AI Security Framework - Enterprise Grade

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
from urllib.parse import urlparse
import logging

# 尝试导入加密库
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("警告: cryptography库未安装，将使用简化加密")

# 安全配置
SECURITY_CONFIG = {
    'password_min_length': 12,
    'password_require_uppercase': True,
    'password_require_lowercase': True,
    'password_require_digit': True,
    'password_require_special': True,
    'max_login_attempts': 5,
    'lockout_duration_minutes': 30,
    'session_timeout_hours': 24,
    'jwt_expiry_hours': 24,
    'refresh_token_expiry_days': 7,
    'max_api_keys_per_user': 10,
    'rate_limit_requests': 100,
    'rate_limit_window_minutes': 1,
    'csrf_token_expiry_hours': 24,
    'mfa_code_length': 6,
    'mfa_code_validity_minutes': 5,
}

# ==================== 数据模型 ====================

class SecurityLevel(Enum):
    """安全等级"""
    LOW = "low"           # 基础安全
    MEDIUM = "medium"     # 标准安全
    HIGH = "high"         # 高级安全
    CRITICAL = "critical" # 关键系统

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
    applies_to: List[str]  # user_ids or roles
    priority: int = 0
    is_active: bool = True

# ==================== 核心安全服务 ====================

class PasswordManager:
    """密码管理器 - 符合NIST SP 800-63B标准"""
    
    def __init__(self):
        self.config = SECURITY_CONFIG
        self._common_passwords = self._load_common_passwords()
    
    def _load_common_passwords(self) -> Set[str]:
        """加载常见弱密码列表"""
        common = {
            'password', '123456', '12345678', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey',
            'dragon', 'master', 'sunshine', 'princess', 'football',
            'baseball', 'iloveyou', 'trustno1', 'admin123', 'welcome123'
        }
        return common
    
    def validate_password(self, password: str, user_info: Dict = None) -> Tuple[bool, List[str]]:
        """验证密码强度"""
        errors = []
        
        # 长度检查
        if len(password) < self.config['password_min_length']:
            errors.append(f"密码长度至少{self.config['password_min_length']}位")
        
        # 复杂度检查
        if self.config['password_require_uppercase'] and not re.search(r'[A-Z]', password):
            errors.append("密码必须包含大写字母")
        
        if self.config['password_require_lowercase'] and not re.search(r'[a-z]', password):
            errors.append("密码必须包含小写字母")
        
        if self.config['password_require_digit'] and not re.search(r'\d', password):
            errors.append("密码必须包含数字")
        
        if self.config['password_require_special'] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("密码必须包含特殊字符")
        
        # 常见密码检查
        if password.lower() in self._common_passwords:
            errors.append("密码过于常见，请选择更强的密码")
        
        # 用户信息检查（避免使用用户名、邮箱等）
        if user_info:
            username = user_info.get('username', '').lower()
            email = user_info.get('email', '').lower().split('@')[0]
            if username and username in password.lower():
                errors.append("密码不能包含用户名")
            if email and email in password.lower():
                errors.append("密码不能包含邮箱")
        
        # 重复字符检查
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
            100000  # 迭代次数
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
    
    def check_password_history(self, password: str, history: List[str]) -> bool:
        """检查密码是否在历史记录中"""
        for old_hash, old_salt in [h.split(':') for h in history]:
            if self.verify_password(password, old_hash, old_salt):
                return True
        return False

class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret = secret_key or secrets.token_hex(32)
        self.algorithm = 'HS256'
    
    def _b64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    
    def _b64url_decode(self, s: str) -> bytes:
        padding = 4 - len(s) % 4
        if padding != 4:
            s += '=' * padding
        return base64.urlsafe_b64decode(s)
    
    def generate_token(self, user_id: str, claims: Dict = None, 
                       expiry_hours: int = None) -> str:
        """生成JWT令牌"""
        try:
            import jwt
            payload = {
                'sub': user_id,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(
                    hours=expiry_hours or SECURITY_CONFIG['jwt_expiry_hours']
                ),
                **(claims or {})
            }
            return jwt.encode(payload, self.secret, algorithm=self.algorithm)
        except ImportError:
            header = json.dumps({'alg': 'HS256', 'typ': 'JWT'}, separators=(',', ':'))
            payload = {
                'sub': user_id,
                'iat': datetime.utcnow().isoformat(),
                'exp': (datetime.utcnow() + timedelta(
                    hours=expiry_hours or SECURITY_CONFIG['jwt_expiry_hours']
                )).isoformat(),
                'claims': claims or {}
            }
            payload_json = json.dumps(payload, separators=(',', ':'))
            
            header_b64 = self._b64url_encode(header.encode())
            payload_b64 = self._b64url_encode(payload_json.encode())
            
            signing_input = f"{header_b64}.{payload_b64}".encode()
            signature = hmac.new(
                self.secret.encode(),
                signing_input,
                hashlib.sha256
            ).digest()
            signature_b64 = self._b64url_encode(signature)
            
            return f"{header_b64}.{payload_b64}.{signature_b64}"
    
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
                header_b64, payload_b64, signature_b64 = parts
                
                header_json = self._b64url_decode(header_b64).decode()
                header = json.loads(header_json)
                if header.get('alg', '').lower() not in ('hs256',):
                    return None
                
                signing_input = f"{header_b64}.{payload_b64}".encode()
                expected_sig = hmac.new(
                    self.secret.encode(),
                    signing_input,
                    hashlib.sha256
                ).digest()
                actual_sig = self._b64url_decode(signature_b64)
                
                if not hmac.compare_digest(expected_sig, actual_sig):
                    return None
                
                payload_json = self._b64url_decode(payload_b64).decode()
                payload = json.loads(payload_json)
                
                exp_str = payload.get('exp')
                if exp_str:
                    try:
                        exp = datetime.fromisoformat(exp_str)
                        if exp < datetime.utcnow():
                            return None
                    except (ValueError, TypeError):
                        return None
                
                return payload
            except Exception:
                return None
        except Exception:
            return None

class MFAManager:
    """多因素认证管理器"""
    
    def __init__(self):
        self._codes: Dict[str, Tuple[str, datetime]] = {}  # user_id -> (code, expiry)
    
    def generate_secret(self) -> str:
        """生成MFA密钥"""
        return base64.b32encode(secrets.token_bytes(20)).decode()
    
    def generate_totp_uri(self, user_id: str, secret: str, 
                          issuer: str = "KaguyaAI") -> str:
        """生成TOTP URI（用于二维码）"""
        return f"otpauth://totp/{issuer}:{user_id}?secret={secret}&issuer={issuer}"
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """生成备用验证码"""
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    def verify_totp(self, secret: str, code: str, window: int = 1) -> bool:
        """验证TOTP码"""
        try:
            import pyotp
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except ImportError:
            if not code or len(code) != SECURITY_CONFIG['mfa_code_length']:
                return False
            for offset in range(-window, window + 1):
                expected = self._generate_simple_totp(secret, offset)
                if hmac.compare_digest(code.upper(), expected):
                    return True
            return False
    
    def _generate_simple_totp(self, secret: str, time_offset: int = 0) -> str:
        """简化TOTP生成 - HOTP-based实现"""
        import struct
        import time
        counter = int(time.time()) // 30 + time_offset
        try:
            key = base64.b32decode(secret, casefold=True)
        except Exception:
            key = secret.encode()
        msg = struct.pack('>Q', counter)
        hmac_hash = hmac.new(key, msg, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        binary = struct.unpack('>I', hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
        code_len = SECURITY_CONFIG['mfa_code_length']
        otp = binary % (10 ** code_len)
        return str(otp).zfill(code_len).upper()
    
    def send_sms_code(self, phone: str) -> str:
        """发送短信验证码（简化实现）"""
        code = ''.join(secrets.choice('0123456789') 
                      for _ in range(SECURITY_CONFIG['mfa_code_length']))
        # 实际应调用短信服务
        print(f"[SMS] 验证码 {code} 已发送至 {phone}")
        return code

class InputValidator:
    """输入验证器 - 防止注入攻击"""
    
    # SQL注入模式
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
    
    # XSS模式
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
    
    # 路径遍历模式
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
        # 检查危险模式
        for pattern in self.sql_patterns:
            if pattern.search(value):
                raise SecurityException("检测到SQL注入攻击", SecurityEventType.SQL_INJECTION_ATTEMPT)
        
        # 转义特殊字符
        sanitized = value.replace("'", "''").replace("\\", "\\\\")
        return sanitized
    
    def sanitize_html(self, value: str) -> str:
        """XSS防护"""
        # 检查危险模式
        for pattern in self.xss_patterns:
            if pattern.search(value):
                raise SecurityException("检测到XSS攻击", SecurityEventType.XSS_ATTEMPT)
        
        # HTML实体编码
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
                raise SecurityException("检测到路径遍历攻击", SecurityEventType.SUSPICIOUS_ACTIVITY)
        
        # 规范化路径
        normalized = os.path.normpath(path)
        if normalized.startswith('..'):
            raise SecurityException("非法路径访问", SecurityEventType.SUSPICIOUS_ACTIVITY)
        
        return normalized
    
    def validate_email(self, email: str) -> bool:
        """邮箱格式验证"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_uuid(self, value: str) -> bool:
        """UUID格式验证"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return re.match(pattern, value, re.IGNORECASE) is not None
    
    def validate_ip(self, ip: str) -> bool:
        """IP地址验证"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

class CSRFProtection:
    """CSRF防护"""
    
    def __init__(self):
        self._tokens: Dict[str, Tuple[str, datetime]] = {}
        self._lock = threading.Lock()
    
    def generate_token(self, session_id: str) -> str:
        """生成CSRF令牌"""
        token = secrets.token_urlsafe(32)
        expiry = datetime.utcnow() + timedelta(
            hours=SECURITY_CONFIG['csrf_token_expiry_hours']
        )
        
        with self._lock:
            self._tokens[session_id] = (token, expiry)
        
        return token
    
    def validate_token(self, session_id: str, token: str) -> bool:
        """验证CSRF令牌"""
        with self._lock:
            stored = self._tokens.get(session_id)
            if not stored:
                return False
            
            stored_token, expiry = stored
            if expiry < datetime.utcnow():
                del self._tokens[session_id]
                return False
            
            return hmac.compare_digest(stored_token, token)
    
    def cleanup_expired(self):
        """清理过期令牌"""
        now = datetime.utcnow()
        with self._lock:
            expired = [sid for sid, (_, exp) in self._tokens.items() if exp < now]
            for sid in expired:
                del self._tokens[sid]

class SecurityException(Exception):
    """安全异常"""
    def __init__(self, message: str, event_type: SecurityEventType = None, 
                 details: Dict = None):
        super().__init__(message)
        self.event_type = event_type
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()

# ==================== 认证与授权管理器 ====================

class AuthenticationManager:
    """认证管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), 'security_data', 'auth.db'
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager()
        self.mfa_manager = MFAManager()
        self.validator = InputValidator()
        
        self._sessions: Dict[str, Session] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._lock = threading.Lock()
        
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
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
            
            # 安全事件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    severity TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON user_credentials(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_key_user ON api_keys(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_time ON security_events(timestamp)')
            
            conn.commit()
    
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO user_credentials 
                    (user_id, password_hash, salt, last_password_change)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, password_hash, salt, datetime.utcnow().isoformat()))
                conn.commit()
                return True, "注册成功"
            except sqlite3.IntegrityError:
                return False, "用户已存在"
    
    def authenticate(self, user_id: str, password: str, 
                     ip_address: str = None, user_agent: str = None) -> Tuple[bool, str, Dict]:
        """用户认证"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT password_hash, salt, mfa_enabled, mfa_secret,
                       failed_login_attempts, locked_until
                FROM user_credentials WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
        
        if not row:
            self._log_security_event(SecurityEventType.AUTH_FAILURE, user_id, ip_address)
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
            self._log_security_event(SecurityEventType.AUTH_FAILURE, user_id, ip_address)
            
            # 检查是否需要锁定
            if failed_attempts + 1 >= SECURITY_CONFIG['max_login_attempts']:
                self._lock_account(user_id)
                return False, "登录失败次数过多，账户已锁定", {}
            
            return False, "用户名或密码错误", {}
        
        # 重置失败次数
        self._reset_failed_attempts(user_id)
        
        # 检查是否需要MFA
        if mfa_enabled:
            return True, "需要二次验证", {
                'require_mfa': True,
                'user_id': user_id,
                'temp_token': self.jwt_manager.generate_token(
                    user_id, {'mfa_pending': True}, expiry_hours=1
                )
            }
        
        # 生成会话
        session = self._create_session(user_id, ip_address, user_agent)
        
        self._log_security_event(SecurityEventType.AUTH_SUCCESS, user_id, ip_address)
        
        return True, "认证成功", {
            'session_id': session.session_id,
            'access_token': self.jwt_manager.generate_token(user_id),
            'refresh_token': secrets.token_urlsafe(32),
            'expires_at': session.expires_at
        }
    
    def verify_mfa(self, user_id: str, code: str, temp_token: str) -> Tuple[bool, str, Dict]:
        """验证MFA码"""
        # 验证临时令牌
        payload = self.jwt_manager.verify_token(temp_token)
        if not payload or not payload.get('claims', {}).get('mfa_pending'):
            return False, "无效的验证请求", {}
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT mfa_secret FROM user_credentials WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
        
        if not row or not row[0]:
            return False, "MFA未配置", {}
        
        mfa_secret = row[0]
        
        if not self.mfa_manager.verify_totp(mfa_secret, code):
            return False, "验证码错误", {}
        
        # 生成完整会话
        session = self._create_session(user_id)
        
        return True, "验证成功", {
            'session_id': session.session_id,
            'access_token': self.jwt_manager.generate_token(user_id),
            'refresh_token': secrets.token_urlsafe(32)
        }
    
    def _create_session(self, user_id: str, ip_address: str = None, 
                        user_agent: str = None) -> Session:
        """创建会话"""
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires = now + timedelta(hours=SECURITY_CONFIG['session_timeout_hours'])
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            ip_address=ip_address or '',
            user_agent=user_agent or ''
        )
        
        with self._lock:
            self._sessions[session_id] = session
        
        return session
    
    def validate_session(self, session_id: str) -> Optional[Session]:
        """验证会话"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            
            if not session.is_active:
                return None
            
            expires = datetime.fromisoformat(session.expires_at)
            if expires < datetime.utcnow():
                session.is_active = False
                return None
            
            return session
    
    def logout(self, session_id: str):
        """注销会话"""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].is_active = False
    
    def create_api_key(self, user_id: str, name: str, 
                       permissions: List[str] = None,
                       expires_days: int = None) -> Tuple[str, str]:
        """创建API密钥"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM api_keys 
                WHERE user_id = ? AND is_active = 1
            ''', (user_id,))
            count = cursor.fetchone()[0]
            
            if count >= SECURITY_CONFIG['max_api_keys_per_user']:
                raise SecurityException(f"每个用户最多{SECURITY_CONFIG['max_api_keys_per_user']}个API密钥")
            
            key_id = f"kag_{secrets.token_urlsafe(16)}"
            api_secret = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_secret.encode()).hexdigest()
            
            now = datetime.utcnow()
            expires = None
            if expires_days:
                expires = (now + timedelta(days=expires_days)).isoformat()
            
            cursor.execute('''
                INSERT INTO api_keys 
                (key_id, user_id, key_hash, name, permissions, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                key_id, user_id, key_hash, name,
                json.dumps(permissions or []),
                now.isoformat(), expires
            ))
            conn.commit()
        
        return key_id, f"{key_id}.{api_secret}"
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """验证API密钥"""
        try:
            key_id, secret = api_key.split('.', 1)
        except ValueError:
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT key_id, user_id, key_hash, name, permissions, 
                       created_at, expires_at, last_used_at, usage_count, 
                       is_active, allowed_ips, rate_limit
                FROM api_keys WHERE key_id = ? AND is_active = 1
            ''', (key_id,))
            row = cursor.fetchone()
        
        if not row:
            return None
        
        key_hash = hashlib.sha256(secret.encode()).hexdigest()
        if not hmac.compare_digest(key_hash, row[2]):
            return None
        
        if row[6]:
            if datetime.fromisoformat(row[6]) < datetime.utcnow():
                return None
        
        api_key_obj = APIKey(
            key_id=row[0],
            user_id=row[1],
            key_hash=row[2],
            name=row[3],
            permissions=set(json.loads(row[4])),
            created_at=row[5],
            expires_at=row[6],
            last_used_at=row[7],
            usage_count=row[8],
            is_active=bool(row[9]),
            allowed_ips=json.loads(row[10]) if row[10] else None,
            rate_limit=row[11]
        )
        
        self._update_api_key_usage(key_id)
        
        return api_key_obj
    
    def _update_api_key_usage(self, key_id: str):
        """更新API密钥使用记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE api_keys 
                SET last_used_at = ?, usage_count = usage_count + 1
                WHERE key_id = ?
            ''', (datetime.utcnow().isoformat(), key_id))
            conn.commit()
    
    def _increment_failed_attempts(self, user_id: str):
        """增加失败登录次数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_credentials 
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    
    def _reset_failed_attempts(self, user_id: str):
        """重置失败登录次数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_credentials 
                SET failed_login_attempts = 0, locked_until = NULL
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    
    def _lock_account(self, user_id: str):
        """锁定账户"""
        lock_until = (datetime.utcnow() + timedelta(
            minutes=SECURITY_CONFIG['lockout_duration_minutes']
        )).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_credentials SET locked_until = ? WHERE user_id = ?
            ''', (lock_until, user_id))
            conn.commit()
        
        self._log_security_event(SecurityEventType.ACCOUNT_LOCKOUT, user_id)
    
    def _log_security_event(self, event_type: SecurityEventType, 
                           user_id: str = None, ip_address: str = None,
                           details: Dict = None):
        """记录安全事件"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO security_events 
                (event_id, event_type, user_id, ip_address, details, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                secrets.token_hex(16),
                event_type.value,
                user_id,
                ip_address,
                json.dumps(details or {}),
                'warning' if event_type in [SecurityEventType.AUTH_FAILURE] else 'info'
            ))
            conn.commit()

# ==================== 安全监控与防护 ====================

class SecurityMonitor:
    """安全监控器"""
    
    def __init__(self):
        self._suspicious_ips: Set[str] = set()
        self._blocked_ips: Set[str] = set()
        self._request_counts: Dict[str, List[datetime]] = {}  # ip -> [timestamps]
        self._lock = threading.Lock()
        self._alert_handlers: List[Callable] = []
    
    def add_alert_handler(self, handler: Callable):
        """添加告警处理器"""
        self._alert_handlers.append(handler)
    
    def check_request(self, ip_address: str, user_agent: str = None,
                      path: str = None) -> Tuple[bool, str]:
        """检查请求是否安全"""
        # 检查IP是否被封锁
        if ip_address in self._blocked_ips:
            return False, "IP已被封锁"
        
        now = datetime.utcnow()
        
        with self._lock:
            # 更新请求计数
            if ip_address not in self._request_counts:
                self._request_counts[ip_address] = []
            
            # 清理过期记录（1分钟前）
            cutoff = now - timedelta(minutes=1)
            self._request_counts[ip_address] = [
                t for t in self._request_counts[ip_address] if t > cutoff
            ]
            
            self._request_counts[ip_address].append(now)
            
            # 检查速率限制
            if len(self._request_counts[ip_address]) > SECURITY_CONFIG['rate_limit_requests']:
                self._suspicious_ips.add(ip_address)
                self._trigger_alert(SecurityEventType.RATE_LIMIT_EXCEEDED, ip_address)
                return False, "请求过于频繁"
        
        # 检查可疑User-Agent
        if user_agent and self._is_suspicious_ua(user_agent):
            return False, "可疑的请求来源"
        
        return True, "通过"
    
    def _is_suspicious_ua(self, user_agent: str) -> bool:
        """检查是否为可疑User-Agent"""
        suspicious_patterns = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zgrab',
            'gobuster', 'dirbuster', 'burp', 'metasploit'
        ]
        ua_lower = user_agent.lower()
        return any(pattern in ua_lower for pattern in suspicious_patterns)
    
    def block_ip(self, ip_address: str, duration_minutes: int = 60):
        """封锁IP地址"""
        self._blocked_ips.add(ip_address)
        
        # 定时解封
        def unblock():
            self._blocked_ips.discard(ip_address)
        
        threading.Timer(duration_minutes * 60, unblock).start()
    
    def _trigger_alert(self, event_type: SecurityEventType, 
                      ip_address: str = None, details: Dict = None):
        """触发安全告警"""
        alert = {
            'event_type': event_type.value,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': ip_address,
            'details': details or {}
        }
        
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"告警处理器错误: {e}")

class WAF:
    """Web应用防火墙"""
    
    def __init__(self):
        self.validator = InputValidator()
        self.monitor = SecurityMonitor()
        self._rules: List[Dict] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        self._rules = [
            {
                'id': 'waf-001',
                'name': 'SQL注入防护',
                'type': 'sql_injection',
                'severity': 'high',
                'enabled': True
            },
            {
                'id': 'waf-002',
                'name': 'XSS攻击防护',
                'type': 'xss',
                'severity': 'high',
                'enabled': True
            },
            {
                'id': 'waf-003',
                'name': '路径遍历防护',
                'type': 'path_traversal',
                'severity': 'medium',
                'enabled': True
            },
            {
                'id': 'waf-004',
                'name': '敏感文件访问',
                'type': 'sensitive_file',
                'severity': 'medium',
                'enabled': True
            }
        ]
    
    def inspect_request(self, request_data: Dict) -> Tuple[bool, List[Dict]]:
        """检查请求"""
        violations = []
        
        # 检查IP
        ip = request_data.get('ip_address')
        ua = request_data.get('user_agent')
        path = request_data.get('path')
        
        is_safe, reason = self.monitor.check_request(ip, ua, path)
        if not is_safe:
            violations.append({
                'rule_id': 'rate-limit',
                'type': 'rate_limit',
                'message': reason
            })
            return False, violations
        
        # 检查路径
        if path:
            try:
                self.validator.validate_path(path)
            except SecurityException as e:
                violations.append({
                    'rule_id': 'waf-003',
                    'type': 'path_traversal',
                    'message': str(e)
                })
        
        # 检查参数
        params = request_data.get('params', {})
        for key, value in params.items():
            if isinstance(value, str):
                # SQL注入检查
                for pattern in self.validator.sql_patterns:
                    if pattern.search(value):
                        violations.append({
                            'rule_id': 'waf-001',
                            'type': 'sql_injection',
                            'message': f'参数 {key} 包含SQL注入风险',
                            'param': key
                        })
                        break
                
                # XSS检查
                for pattern in self.validator.xss_patterns:
                    if pattern.search(value):
                        violations.append({
                            'rule_id': 'waf-002',
                            'type': 'xss',
                            'message': f'参数 {key} 包含XSS风险',
                            'param': key
                        })
                        break
        
        # 检查敏感文件访问
        sensitive_paths = ['/.env', '/config.php', '/.git/', '/.htaccess',
                          '/wp-config.php', '/admin/', '/phpmyadmin/']
        if any(path and sp in path for sp in sensitive_paths):
            violations.append({
                'rule_id': 'waf-004',
                'type': 'sensitive_file',
                'message': '尝试访问敏感路径'
            })
        
        return len(violations) == 0, violations

# ==================== 综合安全管理器 ====================

class SecurityManager:
    """综合安全管理器 - 统一入口"""
    
    def __init__(self, db_path: str = None):
        self.auth = AuthenticationManager(db_path)
        self.validator = InputValidator()
        self.csrf = CSRFProtection()
        self.waf = WAF()
        self.monitor = SecurityMonitor()
        
        # 从已有模块导入
        try:
            from rbac_system import rbac_manager, Permission, Role
            self.rbac = rbac_manager
            self.Permission = Permission
            self.Role = Role
        except ImportError:
            self.rbac = None
            print("警告: RBAC系统未加载")
        
        try:
            from encryption_system import encryption_service, privacy_protector
            self.encryption = encryption_service
            self.privacy = privacy_protector
        except ImportError:
            self.encryption = None
            self.privacy = None
            print("警告: 加密服务未加载")
        
        try:
            from audit_system import audit_logger, AuditEventType
            self.audit = audit_logger
            self.AuditEventType = AuditEventType
        except ImportError:
            self.audit = None
            print("警告: 审计系统未加载")
        
        self._initialized = False
    
    async def initialize(self):
        """初始化安全系统"""
        if self._initialized:
            return
        
        print("=" * 70)
        print("🔒 初始化辉夜AI安全框架")
        print("=" * 70)
        
        # 配置安全监控告警
        self.monitor.add_alert_handler(self._default_alert_handler)
        
        print("✅ 认证管理器初始化完成")
        print("✅ WAF规则加载完成")
        print("✅ 输入验证器初始化完成")
        print("✅ CSRF防护初始化完成")
        
        if self.rbac:
            print("✅ RBAC权限系统已连接")
        if self.encryption:
            print("✅ 加密服务已连接")
        if self.audit:
            print("✅ 审计系统已连接")
        
        self._initialized = True
        print("=" * 70)
        print("🔒 安全框架初始化完成")
        print("=" * 70)
    
    def _default_alert_handler(self, alert: Dict):
        """默认告警处理器"""
        print(f"🚨 安全告警: {alert['event_type']} - IP: {alert.get('ip_address')}")
        
        # 记录到审计系统
        if self.audit:
            try:
                event_type = getattr(self.AuditEventType, 'SUSPICIOUS_ACTIVITY', None)
                if event_type:
                    self.audit.log(
                        event_type=event_type,
                        action='security_alert',
                        details=alert
                    )
            except:
                pass
    
    # ========== 便捷方法 ==========
    
    def secure_route(self, require_auth: bool = True, 
                     permissions: List = None,
                     require_csrf: bool = True):
        """路由安全装饰器工厂"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # 这里简化实现，实际应从请求上下文获取
                request_data = kwargs.get('request', {})
                
                # WAF检查
                is_safe, violations = self.waf.inspect_request(request_data)
                if not is_safe:
                    return {'error': 'Security violation', 'violations': violations}, 403
                
                # 认证检查
                if require_auth:
                    auth_header = request_data.get('headers', {}).get('Authorization', '')
                    if not auth_header:
                        return {'error': 'Unauthorized'}, 401
                    
                    # 验证令牌
                    token = auth_header.replace('Bearer ', '')
                    payload = self.auth.jwt_manager.verify_token(token)
                    if not payload:
                        return {'error': 'Invalid token'}, 401
                    
                    kwargs['current_user'] = payload.get('sub')
                
                # 权限检查
                if permissions and self.rbac:
                    user_id = kwargs.get('current_user')
                    for perm in permissions:
                        if not self.rbac.check_permission(user_id, perm):
                            return {'error': 'Forbidden'}, 403
                
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def encrypt_sensitive_data(self, data: str, context: str = None) -> str:
        """加密敏感数据"""
        if self.encryption:
            return self.encryption.encrypt_field(data, context or 'default')
        # 简化实现
        return base64.b64encode(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted: str, context: str = None) -> str:
        """解密敏感数据"""
        if self.encryption:
            return self.encryption.decrypt_field(encrypted, context or 'default')
        # 简化实现
        return base64.b64decode(encrypted.encode()).decode()
    
    def mask_pii(self, text: str) -> str:
        """掩码PII信息"""
        if self.privacy:
            return self.privacy.mask_pii(text)
        # 简化实现
        import re
        text = re.sub(r'\d{3}\d{4}\d{4}', r'\1****\2', text)
        return text

# ==================== 全局实例 ====================

_security_manager: Optional[SecurityManager] = None

def get_security_manager(db_path: str = None) -> SecurityManager:
    """获取安全管理器实例（单例）"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(db_path)
    return _security_manager

# ==================== 测试 ====================

if __name__ == '__main__':
    import asyncio
    
    async def test():
        security = get_security_manager()
        await security.initialize()
        
        print("\n" + "=" * 70)
        print("🧪 运行安全测试")
        print("=" * 70)
        
        # 测试用户注册
        print("\n1. 测试用户注册")
        success, msg = security.auth.register_user(
            "test_user",
            "SecureP@ssw0rd123!",
            {"username": "test_user", "email": "test@example.com"}
        )
        print(f"   注册: {msg}")
        
        # 测试弱密码
        success, msg = security.auth.register_user(
            "weak_user",
            "password123"
        )
        print(f"   弱密码测试: {msg}")
        
        # 测试认证
        print("\n2. 测试用户认证")
        success, msg, data = security.auth.authenticate(
            "test_user",
            "SecureP@ssw0rd123!",
            ip_address="192.168.1.1"
        )
        print(f"   认证: {msg}")
        if success:
            print(f"   Token: {data.get('access_token', '')[:50]}...")
        
        # 测试错误密码
        success, msg, _ = security.auth.authenticate(
            "test_user",
            "wrong_password",
            ip_address="192.168.1.1"
        )
        print(f"   错误密码: {msg}")
        
        # 测试WAF
        print("\n3. 测试WAF防护")
        test_requests = [
            {'ip_address': '192.168.1.1', 'path': '/api/test', 'params': {'id': '1'}},
            {'ip_address': '192.168.1.1', 'path': '/api/test', 'params': {'id': "1' OR '1'='1"}},
            {'ip_address': '192.168.1.1', 'path': '/../etc/passwd', 'params': {}},
            {'ip_address': '192.168.1.1', 'path': '/api/test', 'params': {'data': '<script>alert(1)</script>'}},
        ]
        
        for i, req in enumerate(test_requests, 1):
            is_safe, violations = security.waf.inspect_request(req)
            status = "✅ 通过" if is_safe else "❌ 拦截"
            print(f"   请求{i}: {status}")
            if violations:
                for v in violations:
                    print(f"      - {v['type']}: {v['message']}")
        
        # 测试输入验证
        print("\n4. 测试输入验证")
        try:
            security.validator.sanitize_sql("SELECT * FROM users")
            print("   正常SQL: ✅")
        except SecurityException as e:
            print(f"   正常SQL: ❌ {e}")
        
        try:
            security.validator.sanitize_sql("1' OR '1'='1")
            print("   注入SQL: ✅ (未拦截)")
        except SecurityException as e:
            print(f"   注入SQL: ❌ 已拦截 ({e.event_type.value})")
        
        # 测试API密钥
        print("\n5. 测试API密钥")
        key_id, api_key = security.auth.create_api_key(
            "test_user",
            "Test API Key",
            permissions=["chat:read", "chat:write"]
        )
        print(f"   创建API密钥: {key_id}")
        
        validated = security.auth.validate_api_key(api_key)
        if validated:
            print(f"   验证成功: 用户 {validated.user_id}")
            print(f"   权限: {validated.permissions}")
        
        print("\n" + "=" * 70)
        print("✅ 安全测试完成")
        print("=" * 70)
    
    asyncio.run(test())
