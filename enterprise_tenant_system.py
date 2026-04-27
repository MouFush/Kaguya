#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业级多租户系统
参考: SaaS多租户架构最佳实践
"""

import os
import json
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import sqlite3

# 租户数据目录
TENANTS_DIR = os.path.join(os.path.dirname(__file__), 'tenants')
os.makedirs(TENANTS_DIR, exist_ok=True)

class TenantTier(Enum):
    """租户等级"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class ResourceType(Enum):
    """资源类型"""
    API_CALLS = "api_calls"
    TOKENS = "tokens"
    STORAGE = "storage"
    CONCURRENT_USERS = "concurrent_users"
    MODELS = "models"

@dataclass
class Tenant:
    """租户定义"""
    id: str
    name: str
    tier: TenantTier
    api_key: str
    created_at: str
    expires_at: Optional[str]
    is_active: bool
    metadata: Dict
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tier': self.tier.value,
            'api_key': self.api_key,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'is_active': self.is_active,
            'metadata': self.metadata
        }

@dataclass
class UsageQuota:
    """使用配额"""
    resource_type: ResourceType
    limit: int
    used: int
    reset_period: str  # daily, monthly, yearly
    
    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)
    
    @property
    def percentage(self) -> float:
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

class TenantManager:
    """租户管理器"""
    
    # 各等级的默认配额
    DEFAULT_QUOTAS = {
        TenantTier.FREE: {
            ResourceType.API_CALLS: 1000,
            ResourceType.TOKENS: 100000,
            ResourceType.STORAGE: 100 * 1024 * 1024,  # 100MB
            ResourceType.CONCURRENT_USERS: 1,
            ResourceType.MODELS: 2
        },
        TenantTier.BASIC: {
            ResourceType.API_CALLS: 10000,
            ResourceType.TOKENS: 1000000,
            ResourceType.STORAGE: 1024 * 1024 * 1024,  # 1GB
            ResourceType.CONCURRENT_USERS: 5,
            ResourceType.MODELS: 5
        },
        TenantTier.PROFESSIONAL: {
            ResourceType.API_CALLS: 100000,
            ResourceType.TOKENS: 10000000,
            ResourceType.STORAGE: 10 * 1024 * 1024 * 1024,  # 10GB
            ResourceType.CONCURRENT_USERS: 20,
            ResourceType.MODELS: 10
        },
        TenantTier.ENTERPRISE: {
            ResourceType.API_CALLS: -1,  # 无限
            ResourceType.TOKENS: -1,
            ResourceType.STORAGE: -1,
            ResourceType.CONCURRENT_USERS: -1,
            ResourceType.MODELS: -1
        }
    }
    
    def __init__(self):
        self.db_path = os.path.join(TENANTS_DIR, 'tenants.db')
        self._init_database()
        self._cache = {}
        self._lock = threading.RLock()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 租户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                metadata TEXT
            )
        ''')
        
        # 使用记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT,
                password_hash TEXT,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_tenant(self, name: str, tier: TenantTier = TenantTier.FREE, 
                     expires_days: Optional[int] = None) -> Tenant:
        """创建新租户"""
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        api_key = f"sk-kaguya-{secrets.token_hex(24)}"
        
        created_at = datetime.now().isoformat()
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        tenant = Tenant(
            id=tenant_id,
            name=name,
            tier=tier,
            api_key=api_key,
            created_at=created_at,
            expires_at=expires_at,
            is_active=True,
            metadata={}
        )
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tenants (id, name, tier, api_key, created_at, expires_at, is_active, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tenant.id, tenant.name, tenant.tier.value, tenant.api_key,
            tenant.created_at, tenant.expires_at, 1, json.dumps(tenant.metadata)
        ))
        conn.commit()
        conn.close()
        
        # 创建租户数据目录
        tenant_dir = os.path.join(TENANTS_DIR, tenant_id)
        os.makedirs(tenant_dir, exist_ok=True)
        
        print(f"✓ 租户创建成功: {name} ({tenant_id})")
        return tenant
    
    def get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """通过API密钥获取租户"""
        # 检查缓存
        if api_key in self._cache:
            return self._cache[api_key]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenants WHERE api_key = ?', (api_key,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        tenant = Tenant(
            id=row[0],
            name=row[1],
            tier=TenantTier(row[2]),
            api_key=row[3],
            created_at=row[4],
            expires_at=row[5],
            is_active=bool(row[6]),
            metadata=json.loads(row[7]) if row[7] else {}
        )
        
        # 检查是否过期
        if tenant.expires_at and datetime.now() > datetime.fromisoformat(tenant.expires_at):
            tenant.is_active = False
        
        # 缓存
        with self._lock:
            self._cache[api_key] = tenant
        
        return tenant
    
    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """通过ID获取租户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenants WHERE id = ?', (tenant_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return Tenant(
            id=row[0],
            name=row[1],
            tier=TenantTier(row[2]),
            api_key=row[3],
            created_at=row[4],
            expires_at=row[5],
            is_active=bool(row[6]),
            metadata=json.loads(row[7]) if row[7] else {}
        )
    
    def record_usage(self, tenant_id: str, resource_type: ResourceType, amount: int = 1):
        """记录资源使用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usage_records (tenant_id, resource_type, amount, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (tenant_id, resource_type.value, amount, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_usage(self, tenant_id: str, resource_type: ResourceType, 
                  period: str = "daily") -> int:
        """获取资源使用量"""
        if period == "daily":
            start_time = (datetime.now() - timedelta(days=1)).isoformat()
        elif period == "monthly":
            start_time = (datetime.now() - timedelta(days=30)).isoformat()
        else:
            start_time = "1970-01-01"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(amount) FROM usage_records
            WHERE tenant_id = ? AND resource_type = ? AND timestamp > ?
        ''', (tenant_id, resource_type.value, start_time))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] or 0
    
    def check_quota(self, tenant_id: str, resource_type: ResourceType) -> bool:
        """检查配额是否足够"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        quota_limit = self.DEFAULT_QUOTAS[tenant.tier][resource_type]
        
        # -1 表示无限配额
        if quota_limit == -1:
            return True
        
        used = self.get_usage(tenant_id, resource_type, "daily")
        return used < quota_limit
    
    def get_quota_status(self, tenant_id: str) -> Dict[ResourceType, UsageQuota]:
        """获取配额状态"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        quotas = {}
        for resource_type in ResourceType:
            limit = self.DEFAULT_QUOTAS[tenant.tier][resource_type]
            used = self.get_usage(tenant_id, resource_type, "daily")
            
            quotas[resource_type] = UsageQuota(
                resource_type=resource_type,
                limit=limit,
                used=used,
                reset_period="daily"
            )
        
        return quotas
    
    def create_user(self, tenant_id: str, username: str, password: str, 
                   email: Optional[str] = None, role: str = "user") -> Optional[Dict]:
        """为租户创建用户"""
        # 检查租户是否存在
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tenant_users (id, tenant_id, username, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, tenant_id, username, email, password_hash, role, datetime.now().isoformat()))
            conn.commit()
            
            return {
                'id': user_id,
                'tenant_id': tenant_id,
                'username': username,
                'email': email,
                'role': role
            }
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def authenticate_user(self, tenant_id: str, username: str, password: str) -> Optional[Dict]:
        """认证用户"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM tenant_users 
            WHERE tenant_id = ? AND username = ? AND password_hash = ? AND is_active = 1
        ''', (tenant_id, username, password_hash))
        row = cursor.fetchone()
        
        if row:
            # 更新最后登录时间
            cursor.execute('''
                UPDATE tenant_users SET last_login = ? WHERE id = ?
            ''', (datetime.now().isoformat(), row[0]))
            conn.commit()
        
        conn.close()
        
        if not row:
            return None
        
        return {
            'id': row[0],
            'tenant_id': row[1],
            'username': row[2],
            'email': row[3],
            'role': row[5]
        }
    
    def list_tenants(self) -> List[Tenant]:
        """列出所有租户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tenants')
        rows = cursor.fetchall()
        conn.close()
        
        tenants = []
        for row in rows:
            tenants.append(Tenant(
                id=row[0],
                name=row[1],
                tier=TenantTier(row[2]),
                api_key=row[3],
                created_at=row[4],
                expires_at=row[5],
                is_active=bool(row[6]),
                metadata=json.loads(row[7]) if row[7] else {}
            ))
        
        return tenants
    
    def deactivate_tenant(self, tenant_id: str) -> bool:
        """停用租户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE tenants SET is_active = 0 WHERE id = ?', (tenant_id,))
        conn.commit()
        conn.close()
        
        # 清除缓存
        with self._lock:
            self._cache = {k: v for k, v in self._cache.items() if v.id != tenant_id}
        
        return True

# 全局实例
tenant_manager = TenantManager()

if __name__ == '__main__':
    # 测试
    manager = TenantManager()
    
    # 创建测试租户
    tenant = manager.create_tenant("测试公司", TenantTier.PROFESSIONAL, expires_days=30)
    print(f"租户API密钥: {tenant.api_key}")
    
    # 创建用户
    user = manager.create_user(tenant.id, "admin", "password123", "admin@test.com", "admin")
    print(f"用户创建: {user}")
    
    # 认证
    auth_user = manager.authenticate_user(tenant.id, "admin", "password123")
    print(f"认证结果: {auth_user}")
    
    # 记录使用
    manager.record_usage(tenant.id, ResourceType.API_CALLS, 100)
    
    # 检查配额
    print(f"API调用配额: {manager.check_quota(tenant.id, ResourceType.API_CALLS)}")
    
    # 配额状态
    quotas = manager.get_quota_status(tenant.id)
    for rt, q in quotas.items():
        print(f"{rt.value}: {q.used}/{q.limit} ({q.percentage:.1f}%)")
