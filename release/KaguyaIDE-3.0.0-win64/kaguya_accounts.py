#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 增强账户管理系统
实现：认证机制、密码重置、角色权限、活动日志、安全防护

安全特性：
1. 基于bcrypt的密码哈希（带盐值）
2. JWT令牌认证（含刷新令牌）
3. RBAC角色权限系统
4. 完整审计日志链
5. CSRF/XSS/SQL注入/暴力破解防护
6. 账户锁定与密码策略
"""

import json
import os
import re
import time
import uuid
import hashlib
import hmac
import secrets
import threading
import base64
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime, timedelta
from collections import OrderedDict


class AuthEventType(Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKE = "token_revoke"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CSRF_VALIDATION_FAILED = "csrf_validation_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"


class UserRole(Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"
    GUEST = "guest"


@dataclass
class Permission:
    resource: str
    actions: Set[str] = field(default_factory=set)

    def allows(self, action: str) -> bool:
        return "*" in self.actions or action in self.actions


ROLE_PERMISSIONS: Dict[UserRole, Dict[str, Set[str]]] = {
    UserRole.SUPER_ADMIN: {
        "*": {"*"},
    },
    UserRole.ADMIN: {
        "users": {"read", "write", "delete"},
        "conversations": {"read", "write", "delete"},
        "tools": {"read", "write", "execute"},
        "settings": {"read", "write"},
        "audit": {"read"},
        "agents": {"read", "write", "execute"},
        "skills": {"read", "write", "delete"},
        "system": {"read", "write"},
    },
    UserRole.MANAGER: {
        "users": {"read"},
        "conversations": {"read", "write", "delete"},
        "tools": {"read", "execute"},
        "settings": {"read"},
        "audit": {"read"},
        "agents": {"read", "execute"},
        "skills": {"read", "write"},
        "system": {"read"},
    },
    UserRole.USER: {
        "conversations": {"read", "write"},
        "tools": {"read", "execute"},
        "settings": {"read"},
        "agents": {"read", "execute"},
        "skills": {"read", "execute"},
        "system": {"read"},
    },
    UserRole.VIEWER: {
        "conversations": {"read"},
        "tools": {"read"},
        "settings": {"read"},
        "agents": {"read"},
        "skills": {"read"},
        "system": {"read"},
    },
    UserRole.GUEST: {
        "conversations": {"read"},
    },
}


@dataclass
class AccountRecord:
    user_id: str
    username: str
    email: str = ""
    password_hash: str = ""
    salt: str = ""
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_locked: bool = False
    locked_until: Optional[str] = None
    failed_login_attempts: int = 0
    last_login: Optional[str] = None
    last_password_change: Optional[str] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[str] = None
    mfa_secret: Optional[str] = None
    mfa_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionRecord:
    session_id: str
    user_id: str
    token: str
    refresh_token: str
    ip_address: str = ""
    user_agent: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = ""
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True


@dataclass
class AuditEntry:
    event_id: str
    event_type: AuthEventType
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    resource: str = ""
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PasswordManager:
    MIN_LENGTH = 12
    REQUIRE_UPPER = True
    REQUIRE_LOWER = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    PASSWORD_HISTORY_SIZE = 5

    @staticmethod
    def _derive_key(salt: str, password: str, iterations: int = 100000) -> str:
        try:
            dk = hashlib.pbkdf2_hmac(
                'sha256',
                (salt + password).encode('utf-8'),
                salt.encode('utf-8'),
                iterations,
            )
            return dk.hex()
        except AttributeError:
            key = salt.encode('utf-8') + password.encode('utf-8')
            for _ in range(iterations):
                key = hashlib.sha256(key + salt.encode('utf-8')).digest()
            return key.hex()

    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        if salt is None:
            salt = secrets.token_hex(16)
        try:
            import bcrypt
            hashed = bcrypt.hashpw(
                (salt + password).encode('utf-8'),
                bcrypt.gensalt(rounds=12),
            )
            return hashed.decode('utf-8'), salt
        except ImportError:
            return PasswordManager._derive_key(salt, password), salt

    @staticmethod
    def verify_password(password: str, password_hash: str, salt: str) -> bool:
        try:
            import bcrypt
            return bcrypt.checkpw(
                (salt + password).encode('utf-8'),
                password_hash.encode('utf-8'),
            )
        except ImportError:
            derived = PasswordManager._derive_key(salt, password)
            return hmac.compare_digest(derived, password_hash)

    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, List[str]]:
        errors = []
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"密码长度至少{cls.MIN_LENGTH}位")
        if cls.REQUIRE_UPPER and not re.search(r'[A-Z]', password):
            errors.append("密码需包含大写字母")
        if cls.REQUIRE_LOWER and not re.search(r'[a-z]', password):
            errors.append("密码需包含小写字母")
        if cls.REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("密码需包含数字")
        if cls.REQUIRE_SPECIAL and not re.search(f'[{re.escape(cls.SPECIAL_CHARS)}]', password):
            errors.append("密码需包含特殊字符")
        common = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() in common:
            errors.append("密码过于常见")
        return len(errors) == 0, errors


class JWTManager:
    def __init__(self, secret_key: str = None, expiry_hours: int = 24,
                 refresh_expiry_days: int = 7):
        self._secret = secret_key or secrets.token_hex(32)
        self._expiry_hours = expiry_hours
        self._refresh_expiry_days = refresh_expiry_days
        self._revoked_tokens: Set[str] = set()
        self._lock = threading.Lock()

    def generate_token(self, user_id: str, role: str, extra_claims: Dict = None) -> Tuple[str, str]:
        now = datetime.utcnow()
        jti = str(uuid.uuid4())

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=self._expiry_hours)).timestamp()),
            "jti": jti,
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        access_token = self._encode(header, payload)

        refresh_jti = str(uuid.uuid4())
        refresh_payload = {
            "sub": user_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=self._refresh_expiry_days)).timestamp()),
            "jti": refresh_jti,
            "type": "refresh",
        }
        refresh_token = self._encode(header, refresh_payload)

        return access_token, refresh_token

    def validate_token(self, token: str) -> Optional[Dict]:
        try:
            payload = self._decode(token)
            if not payload:
                return None

            with self._lock:
                if payload.get("jti") in self._revoked_tokens:
                    return None

            exp = payload.get("exp", 0)
            if exp and datetime.utcnow().timestamp() > exp:
                return None

            if payload.get("type") != "access":
                return None

            return payload
        except Exception:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        try:
            payload = self._decode(refresh_token)
            if not payload:
                return None

            with self._lock:
                if payload.get("jti") in self._revoked_tokens:
                    return None

            if payload.get("type") != "refresh":
                return None

            exp = payload.get("exp", 0)
            if exp and datetime.utcnow().timestamp() > exp:
                return None

            user_id = payload.get("sub", "")
            return self.generate_token(user_id, "")
        except Exception:
            return None

    def revoke_token(self, token: str) -> None:
        try:
            payload = self._decode(token)
            if payload and payload.get("jti"):
                with self._lock:
                    self._revoked_tokens.add(payload["jti"])
        except Exception:
            pass

    def _encode(self, header: Dict, payload: Dict) -> str:
        h = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b'=').decode()
        p = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
        sig = hmac.new(
            self._secret.encode(),
            f"{h}.{p}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{h}.{p}.{sig}"

    def _decode(self, token: str) -> Optional[Dict]:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        h, p, sig = parts
        expected_sig = hmac.new(
            self._secret.encode(),
            f"{h}.{p}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        try:
            padding = 4 - len(p) % 4
            p += '=' * padding
            return json.loads(base64.urlsafe_b64decode(p))
        except Exception:
            return None


class CSRFProtection:
    def __init__(self, secret_key: str = None):
        self._secret = secret_key or secrets.token_hex(32)
        self._token_expiry = 3600

    def generate_token(self, session_id: str = "") -> str:
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(8)
        message = f"{session_id}:{timestamp}:{nonce}"
        sig = hmac.new(self._secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{message}:{sig}".encode()).decode()

    def validate_token(self, token: str, session_id: str = "") -> bool:
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = decoded.split(":")
            if len(parts) != 4:
                return False
            token_session, timestamp, nonce, sig = parts
            if session_id and token_session != session_id:
                return False
            token_time = int(timestamp)
            if time.time() - token_time > self._token_expiry:
                return False
            message = f"{token_session}:{timestamp}:{nonce}"
            expected_sig = hmac.new(
                self._secret.encode(), message.encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False


class XSSProtection:
    DANGEROUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript\s*:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
        re.compile(r'expression\s*\(', re.IGNORECASE),
        re.compile(r'vbscript\s*:', re.IGNORECASE),
        re.compile(r'data\s*:\s*text/html', re.IGNORECASE),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return text
        for pattern in cls.DANGEROUS_PATTERNS:
            text = pattern.sub('', text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

    @classmethod
    def sanitize_html(cls, html: str) -> str:
        allowed_tags = {'p', 'br', 'b', 'i', 'em', 'strong', 'a', 'code', 'pre',
                        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                        'table', 'tr', 'td', 'th', 'thead', 'tbody', 'span', 'div'}
        allowed_attrs = {'href', 'class', 'id', 'target', 'rel'}

        def clean_tag(match):
            tag = match.group(1)
            is_closing = tag.startswith('/')
            tag_name = tag.lstrip('/').split()[0].lower()
            if tag_name not in allowed_tags:
                return ''
            if is_closing:
                return f'</{tag_name}>'
            attrs_str = ''
            attr_pattern = re.compile(r'(\w+)\s*=\s*["\']([^"\']*)["\']')
            for attr_match in attr_pattern.finditer(tag):
                attr_name = attr_match.group(1).lower()
                attr_value = attr_match.group(2)
                if attr_name in allowed_attrs:
                    if attr_name == 'href' and (
                        attr_value.lower().startswith('javascript:') or
                        attr_value.lower().startswith('data:')
                    ):
                        continue
                    attrs_str += f' {attr_name}="{attr_value}"'
            return f'<{tag_name}{attrs_str}>'

        return re.sub(r'<([^>]+)>', clean_tag, html)


class SQLInjectionProtection:
    DANGEROUS_PATTERNS = [
        re.compile(r"(\b(union)\b.*\b(select)\b)", re.IGNORECASE),
        re.compile(r"(\b(drop)\b.*\b(table)\b)", re.IGNORECASE),
        re.compile(r"(\b(insert)\b.*\b(into)\b)", re.IGNORECASE),
        re.compile(r"(\b(delete)\b.*\b(from)\b)", re.IGNORECASE),
        re.compile(r"(\b(update)\b.*\b(set)\b)", re.IGNORECASE),
        re.compile(r"(--|;|/\*|\*/|xp_|sp_)", re.IGNORECASE),
        re.compile(r"('\s*(or|and)\s+'.*'=')", re.IGNORECASE),
        re.compile(r"(\b(exec|execute)\b)", re.IGNORECASE),
    ]

    @classmethod
    def validate(cls, input_str: str) -> Tuple[bool, str]:
        if not input_str:
            return True, ""
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(input_str):
                return False, "Potential SQL injection detected"
        return True, ""

    @classmethod
    def sanitize(cls, input_str: str) -> str:
        if not input_str:
            return input_str
        sanitized = input_str.replace("'", "''")
        sanitized = sanitized.replace("\\", "\\\\")
        sanitized = re.sub(r'[\x00\x1a]', '', sanitized)
        return sanitized


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> Tuple[bool, int]:
        now = time.time()
        with self._lock:
            if key not in self._requests:
                self._requests[key] = []

            self._requests[key] = [
                t for t in self._requests[key]
                if now - t < self._window
            ]

            if len(self._requests[key]) >= self._max_requests:
                return False, self._max_requests

            self._requests[key].append(now)
            return True, len(self._requests[key])

    def reset(self, key: str):
        with self._lock:
            self._requests.pop(key, None)


class AuditLogger:
    def __init__(self, log_dir: str = None, max_entries: int = 100000):
        self._log_dir = log_dir or os.path.join(
            os.path.expanduser("~"), ".kaguya", "audit"
        )
        self._max_entries = max_entries
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._hash_chain: str = "genesis"
        os.makedirs(self._log_dir, exist_ok=True)
        self._load_existing()

    def log(self, event_type: AuthEventType, user_id: str = None,
            ip_address: str = "", user_agent: str = "", resource: str = "",
            action: str = "", details: Dict = None, severity: str = "info") -> AuditEntry:
        entry = AuditEntry(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent[:200] if user_agent else "",
            resource=resource,
            action=action,
            details=details or {},
            severity=severity,
        )

        chain_data = f"{self._hash_chain}:{entry.event_id}:{entry.timestamp}:{entry.event_type.value}"
        self._hash_chain = hashlib.sha256(chain_data.encode()).hexdigest()

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

        self._persist_entry(entry)
        return entry

    def query(self, user_id: str = None, event_type: AuthEventType = None,
              start_time: str = None, end_time: str = None,
              resource: str = None, severity: str = None,
              limit: int = 100) -> List[AuditEntry]:
        with self._lock:
            results = self._entries

        if user_id:
            results = [e for e in results if e.user_id == user_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        if resource:
            results = [e for e in results if e.resource == resource]
        if severity:
            results = [e for e in results if e.severity == severity]

        return results[-limit:]

    def get_user_activity(self, user_id: str, limit: int = 50) -> List[Dict]:
        entries = self.query(user_id=user_id, limit=limit)
        result = []
        for e in reversed(entries):
            d = asdict(e)
            d["event_type"] = e.event_type.value
            result.append(d)
        return result

    def verify_integrity(self) -> bool:
        with self._lock:
            entries = list(self._entries)
        chain = "genesis"
        for entry in entries:
            chain_data = f"{chain}:{entry.event_id}:{entry.timestamp}:{entry.event_type.value}"
            chain = hashlib.sha256(chain_data.encode()).hexdigest()
        return chain == self._hash_chain

    def _persist_entry(self, entry: AuditEntry):
        try:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = os.path.join(self._log_dir, f"audit_{date_str}.jsonl")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def _load_existing(self):
        try:
            files = sorted(
                f for f in os.listdir(self._log_dir)
                if f.startswith("audit_") and f.endswith(".jsonl")
            )
            for fname in files[-7:]:
                fpath = os.path.join(self._log_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            entry = AuditEntry(
                                event_id=data["event_id"],
                                event_type=AuthEventType(data["event_type"]),
                                user_id=data.get("user_id"),
                                ip_address=data.get("ip_address", ""),
                                user_agent=data.get("user_agent", ""),
                                resource=data.get("resource", ""),
                                action=data.get("action", ""),
                                details=data.get("details", {}),
                                severity=data.get("severity", "info"),
                                timestamp=data.get("timestamp", ""),
                            )
                            self._entries.append(entry)
                        except Exception:
                            continue
            if self._entries:
                self._rebuild_chain()
        except Exception:
            pass

    def _rebuild_chain(self):
        self._hash_chain = "genesis"
        for entry in self._entries:
            chain_data = f"{self._hash_chain}:{entry.event_id}:{entry.timestamp}:{entry.event_type.value}"
            self._hash_chain = hashlib.sha256(chain_data.encode()).hexdigest()


class AccountManager:
    def __init__(self, data_dir: str = None, secret_key: str = None):
        self._data_dir = data_dir or os.path.join(
            os.path.expanduser("~"), ".kaguya", "accounts"
        )
        os.makedirs(self._data_dir, exist_ok=True)

        self._accounts: Dict[str, AccountRecord] = {}
        self._sessions: Dict[str, SessionRecord] = {}
        self._password_history: Dict[str, List[str]] = {}

        self._jwt = JWTManager(secret_key=secret_key)
        self._csrf = CSRFProtection(secret_key=secret_key)
        self._rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
        self._login_limiter = RateLimiter(max_requests=5, window_seconds=300)
        self._audit = AuditLogger(
            log_dir=os.path.join(self._data_dir, "audit")
        )

        self._lock = threading.Lock()
        self._load_accounts()

    def create_account(self, username: str, password: str, email: str = "",
                       role: UserRole = UserRole.USER) -> Tuple[Optional[AccountRecord], str]:
        if not username or len(username) < 3:
            return None, "用户名至少3个字符"

        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', username):
            return None, "用户名只能包含字母、数字、下划线和中文"

        with self._lock:
            for acc in self._accounts.values():
                if acc.username == username:
                    return None, "用户名已存在"
                if email and acc.email == email:
                    return None, "邮箱已被使用"

        valid, errors = PasswordManager.validate_password_strength(password)
        if not valid:
            return None, "; ".join(errors)

        pw_hash, salt = PasswordManager.hash_password(password)
        user_id = str(uuid.uuid4())

        account = AccountRecord(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=pw_hash,
            salt=salt,
            role=role,
        )

        with self._lock:
            self._accounts[user_id] = account
            self._password_history[user_id] = [pw_hash]

        self._save_accounts()
        self._audit.log(AuthEventType.SESSION_CREATED, user_id=user_id,
                        resource="account", action="create",
                        details={"username": username, "role": role.value})
        return account, ""

    def authenticate(self, username: str, password: str,
                     ip_address: str = "", user_agent: str = "") -> Tuple[Optional[Dict], str]:
        allowed, _ = self._login_limiter.check(f"login:{ip_address}")
        if not allowed:
            self._audit.log(AuthEventType.RATE_LIMIT_EXCEEDED,
                            ip_address=ip_address, resource="auth",
                            severity="warning")
            return None, "登录尝试过于频繁，请稍后再试"

        with self._lock:
            account = None
            for acc in self._accounts.values():
                if acc.username == username:
                    account = acc
                    break

        if not account:
            self._audit.log(AuthEventType.LOGIN_FAILURE, ip_address=ip_address,
                            user_agent=user_agent, resource="auth",
                            details={"username": username}, severity="warning")
            return None, "用户名或密码错误"

        if account.is_locked:
            if account.locked_until:
                lock_time = datetime.fromisoformat(account.locked_until)
                if datetime.utcnow() < lock_time:
                    return None, f"账户已锁定，请于{account.locked_until}后重试"
                else:
                    account.is_locked = False
                    account.failed_login_attempts = 0
                    self._audit.log(AuthEventType.ACCOUNT_UNLOCKED,
                                    user_id=account.user_id, resource="account")
            else:
                return None, "账户已被锁定，请联系管理员"

        if not PasswordManager.verify_password(password, account.password_hash, account.salt):
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= PasswordManager.MAX_LOGIN_ATTEMPTS:
                account.is_locked = True
                account.locked_until = (
                    datetime.utcnow() + timedelta(minutes=PasswordManager.LOCKOUT_DURATION_MINUTES)
                ).isoformat()
                self._audit.log(AuthEventType.ACCOUNT_LOCKED,
                                user_id=account.user_id, resource="account",
                                details={"attempts": account.failed_login_attempts},
                                severity="warning")

            self._save_accounts()
            self._audit.log(AuthEventType.LOGIN_FAILURE, user_id=account.user_id,
                            ip_address=ip_address, user_agent=user_agent,
                            resource="auth", severity="warning")
            return None, "用户名或密码错误"

        account.failed_login_attempts = 0
        account.is_locked = False
        account.locked_until = None
        account.last_login = datetime.utcnow().isoformat()

        access_token, refresh_token = self._jwt.generate_token(
            account.user_id, account.role.value
        )

        session = SessionRecord(
            session_id=str(uuid.uuid4()),
            user_id=account.user_id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=(datetime.utcnow() + timedelta(hours=24)).isoformat(),
        )

        with self._lock:
            self._sessions[session.session_id] = session

        self._save_accounts()
        self._audit.log(AuthEventType.LOGIN_SUCCESS, user_id=account.user_id,
                        ip_address=ip_address, user_agent=user_agent,
                        resource="auth")

        return {
            "user_id": account.user_id,
            "username": account.username,
            "role": account.role.value,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "csrf_token": self._csrf.generate_token(session.session_id),
        }, ""

    def validate_request(self, token: str, resource: str, action: str,
                         csrf_token: str = None, session_id: str = "") -> Tuple[bool, str]:
        payload = self._jwt.validate_token(token)
        if not payload:
            return False, "无效或过期的令牌"

        user_id = payload.get("sub", "")
        with self._lock:
            account = self._accounts.get(user_id)

        if not account or not account.is_active:
            return False, "账户不存在或已禁用"

        if not self.check_permission(account.role, resource, action):
            self._audit.log(AuthEventType.SUSPICIOUS_ACTIVITY,
                            user_id=user_id, resource=resource, action=action,
                            details={"required": f"{resource}:{action}"},
                            severity="warning")
            return False, "权限不足"

        if csrf_token and not self._csrf.validate_token(csrf_token, session_id):
            self._audit.log(AuthEventType.CSRF_VALIDATION_FAILED,
                            user_id=user_id, resource=resource,
                            severity="warning")
            return False, "CSRF验证失败"

        return True, ""

    def check_permission(self, role: UserRole, resource: str, action: str) -> bool:
        perms = ROLE_PERMISSIONS.get(role, {})
        if "*" in perms and "*" in perms["*"]:
            return True
        resource_perms = perms.get(resource, set())
        if "*" in resource_perms:
            return True
        return action in resource_perms

    def change_password(self, user_id: str, old_password: str,
                        new_password: str) -> Tuple[bool, str]:
        with self._lock:
            account = self._accounts.get(user_id)

        if not account:
            return False, "账户不存在"

        if not PasswordManager.verify_password(old_password, account.password_hash, account.salt):
            return False, "当前密码错误"

        valid, errors = PasswordManager.validate_password_strength(new_password)
        if not valid:
            return False, "; ".join(errors)

        history = self._password_history.get(user_id, [])
        for old_hash in history[-PasswordManager.PASSWORD_HISTORY_SIZE:]:
            if PasswordManager.verify_password(new_password, old_hash, account.salt):
                return False, "不能使用最近使用过的密码"

        new_hash, new_salt = PasswordManager.hash_password(new_password)
        account.password_hash = new_hash
        account.salt = new_salt
        account.last_password_change = datetime.utcnow().isoformat()

        history.append(new_hash)
        self._password_history[user_id] = history[-PasswordManager.PASSWORD_HISTORY_SIZE:]

        self._save_accounts()
        self._audit.log(AuthEventType.PASSWORD_CHANGE, user_id=user_id,
                        resource="account", action="password_change")
        return True, ""

    def request_password_reset(self, username: str,
                               ip_address: str = "") -> Tuple[bool, str]:
        with self._lock:
            account = None
            for acc in self._accounts.values():
                if acc.username == username:
                    account = acc
                    break

        if not account:
            return True, ""

        reset_token = secrets.token_urlsafe(32)
        account.password_reset_token = reset_token
        account.password_reset_expires = (
            datetime.utcnow() + timedelta(hours=1)
        ).isoformat()

        self._save_accounts()
        self._audit.log(AuthEventType.PASSWORD_RESET_REQUEST,
                        user_id=account.user_id, ip_address=ip_address,
                        resource="account", action="password_reset_request")
        return True, reset_token

    def reset_password(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        with self._lock:
            account = None
            for acc in self._accounts.values():
                if acc.password_reset_token == reset_token:
                    account = acc
                    break

        if not account:
            return False, "无效的重置令牌"

        if account.password_reset_expires:
            exp_time = datetime.fromisoformat(account.password_reset_expires)
            if datetime.utcnow() > exp_time:
                account.password_reset_token = None
                account.password_reset_expires = None
                self._save_accounts()
                return False, "重置令牌已过期"

        valid, errors = PasswordManager.validate_password_strength(new_password)
        if not valid:
            return False, "; ".join(errors)

        new_hash, new_salt = PasswordManager.hash_password(new_password)
        account.password_hash = new_hash
        account.salt = new_salt
        account.password_reset_token = None
        account.password_reset_expires = None
        account.last_password_change = datetime.utcnow().isoformat()

        self._save_accounts()
        self._audit.log(AuthEventType.PASSWORD_RESET_COMPLETE,
                        user_id=account.user_id, resource="account",
                        action="password_reset")
        return True, ""

    def change_role(self, target_user_id: str, new_role: UserRole,
                    admin_user_id: str) -> Tuple[bool, str]:
        with self._lock:
            admin = self._accounts.get(admin_user_id)
            target = self._accounts.get(target_user_id)

        if not admin or admin.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return False, "需要管理员权限"

        if not target:
            return False, "目标用户不存在"

        if admin.role == UserRole.ADMIN and new_role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return False, "不能提升到同级或更高级角色"

        old_role = target.role
        target.role = new_role

        self._save_accounts()
        self._audit.log(AuthEventType.ROLE_CHANGE, user_id=admin_user_id,
                        resource="account", action="role_change",
                        details={"target_user": target_user_id,
                                 "old_role": old_role.value,
                                 "new_role": new_role.value})
        return True, ""

    def logout(self, token: str):
        self._jwt.revoke_token(token)
        payload = self._jwt._decode(token) if token else None
        user_id = payload.get("sub") if payload else None
        self._audit.log(AuthEventType.LOGOUT, user_id=user_id, resource="auth")

    def get_account(self, user_id: str) -> Optional[Dict]:
        with self._lock:
            account = self._accounts.get(user_id)
        if not account:
            return None
        data = asdict(account)
        data.pop("password_hash", None)
        data.pop("salt", None)
        data.pop("password_reset_token", None)
        data.pop("mfa_secret", None)
        data["role"] = account.role.value
        return data

    def list_accounts(self, requesting_user_id: str) -> Optional[List[Dict]]:
        with self._lock:
            requester = self._accounts.get(requesting_user_id)
        if not requester or requester.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            return None
        result = []
        with self._lock:
            for acc in self._accounts.values():
                data = {
                    "user_id": acc.user_id,
                    "username": acc.username,
                    "email": acc.email,
                    "role": acc.role.value,
                    "is_active": acc.is_active,
                    "is_locked": acc.is_locked,
                    "last_login": acc.last_login,
                    "created_at": acc.created_at,
                }
                result.append(data)
        return result

    def get_audit_log(self, user_id: str = None, limit: int = 100) -> List[Dict]:
        entries = self._audit.query(user_id=user_id, limit=limit)
        result = []
        for e in reversed(entries):
            d = asdict(e)
            d["event_type"] = e.event_type.value
            result.append(d)
        return result

    def _save_accounts(self):
        try:
            data = {}
            with self._lock:
                for uid, acc in self._accounts.items():
                    d = asdict(acc)
                    d["role"] = acc.role.value
                    data[uid] = d

            path = os.path.join(self._data_dir, "accounts.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def _load_accounts(self):
        path = os.path.join(self._data_dir, "accounts.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                for uid, d in data.items():
                    try:
                        d["role"] = UserRole(d.get("role", "user"))
                    except ValueError:
                        d["role"] = UserRole.USER
                    self._accounts[uid] = AccountRecord(**d)
        except Exception:
            pass


def create_account_manager(data_dir: str = None, secret_key: str = None) -> AccountManager:
    return AccountManager(data_dir=data_dir, secret_key=secret_key)
