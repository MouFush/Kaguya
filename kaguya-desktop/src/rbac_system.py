#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBAC权限控制系统 (Role-Based Access Control)
参考: Kubernetes RBAC, AWS IAM
"""

import json
import uuid
from enum import Enum, auto
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from functools import wraps

class Permission(Enum):
    """权限定义"""
    # 对话权限
    CHAT_CREATE = "chat:create"
    CHAT_READ = "chat:read"
    CHAT_UPDATE = "chat:update"
    CHAT_DELETE = "chat:delete"
    
    # 模型权限
    MODEL_USE = "model:use"
    MODEL_SWITCH = "model:switch"
    MODEL_FINE_TUNE = "model:fine_tune"
    
    # 知识库权限
    KB_READ = "kb:read"
    KB_WRITE = "kb:write"
    KB_DELETE = "kb:delete"
    
    # 工具权限
    TOOL_USE = "tool:use"
    TOOL_CONFIGURE = "tool:configure"
    
    # 系统权限
    USER_MANAGE = "user:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    AUDIT_VIEW = "audit:view"
    BILLING_VIEW = "billing:view"
    
    # API权限
    API_KEY_MANAGE = "api_key:manage"
    WEBHOOK_MANAGE = "webhook:manage"

class Role(Enum):
    """角色定义"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"
    API = "api"

@dataclass
class RoleDefinition:
    """角色定义"""
    name: str
    description: str
    permissions: Set[Permission]
    inherits: Optional[Role] = None

# 预定义角色权限
ROLE_PERMISSIONS = {
    Role.SUPER_ADMIN: RoleDefinition(
        name="超级管理员",
        description="拥有所有权限",
        permissions=set(Permission),  # 所有权限
    ),
    
    Role.ADMIN: RoleDefinition(
        name="管理员",
        description="可以管理用户和系统设置",
        permissions={
            Permission.CHAT_CREATE, Permission.CHAT_READ, 
            Permission.CHAT_UPDATE, Permission.CHAT_DELETE,
            Permission.MODEL_USE, Permission.MODEL_SWITCH, Permission.MODEL_FINE_TUNE,
            Permission.KB_READ, Permission.KB_WRITE, Permission.KB_DELETE,
            Permission.TOOL_USE, Permission.TOOL_CONFIGURE,
            Permission.USER_MANAGE,
            Permission.SETTINGS_READ, Permission.SETTINGS_WRITE,
            Permission.AUDIT_VIEW, Permission.BILLING_VIEW,
            Permission.API_KEY_MANAGE, Permission.WEBHOOK_MANAGE,
        }
    ),
    
    Role.MANAGER: RoleDefinition(
        name="经理",
        description="可以管理团队和查看报表",
        permissions={
            Permission.CHAT_CREATE, Permission.CHAT_READ, Permission.CHAT_UPDATE,
            Permission.MODEL_USE, Permission.MODEL_SWITCH,
            Permission.KB_READ, Permission.KB_WRITE,
            Permission.TOOL_USE,
            Permission.USER_MANAGE,
            Permission.SETTINGS_READ,
            Permission.AUDIT_VIEW, Permission.BILLING_VIEW,
        }
    ),
    
    Role.USER: RoleDefinition(
        name="普通用户",
        description="标准用户权限",
        permissions={
            Permission.CHAT_CREATE, Permission.CHAT_READ, Permission.CHAT_UPDATE,
            Permission.MODEL_USE,
            Permission.KB_READ,
            Permission.TOOL_USE,
            Permission.SETTINGS_READ,
        }
    ),
    
    Role.GUEST: RoleDefinition(
        name="访客",
        description="受限访问权限",
        permissions={
            Permission.CHAT_CREATE, Permission.CHAT_READ,
            Permission.MODEL_USE,
        }
    ),
    
    Role.API: RoleDefinition(
        name="API用户",
        description="仅API访问权限",
        permissions={
            Permission.CHAT_CREATE, Permission.CHAT_READ,
            Permission.MODEL_USE,
            Permission.KB_READ,
        }
    ),
}

class RBACManager:
    """RBAC管理器"""
    
    def __init__(self):
        self._custom_roles: Dict[str, RoleDefinition] = {}
        self._user_roles: Dict[str, Set[Role]] = {}  # user_id -> roles
        self._user_permissions: Dict[str, Set[Permission]] = {}  # user_id -> permissions
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """获取角色的所有权限（包括继承的）"""
        role_def = ROLE_PERMISSIONS.get(role)
        if not role_def:
            return set()
        
        permissions = set(role_def.permissions)
        
        # 处理继承
        if role_def.inherits:
            parent_permissions = self.get_role_permissions(role_def.inherits)
            permissions.update(parent_permissions)
        
        return permissions
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查用户是否有特定权限"""
        # 获取用户的所有权限
        user_perms = self.get_user_permissions(user_id)
        return permission in user_perms
    
    def check_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查用户是否有任一权限"""
        user_perms = self.get_user_permissions(user_id)
        return any(p in user_perms for p in permissions)
    
    def check_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查用户是否有所有权限"""
        user_perms = self.get_user_permissions(user_id)
        return all(p in user_perms for p in permissions)
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户的所有权限"""
        # 检查缓存
        if user_id in self._user_permissions:
            return self._user_permissions[user_id]
        
        # 从用户角色计算
        permissions = set()
        roles = self._user_roles.get(user_id, set())
        
        for role in roles:
            perms = self.get_role_permissions(role)
            permissions.update(perms)
        
        # 缓存
        self._user_permissions[user_id] = permissions
        return permissions
    
    def assign_role(self, user_id: str, role: Role):
        """为用户分配角色"""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role)
        
        # 清除权限缓存
        if user_id in self._user_permissions:
            del self._user_permissions[user_id]
    
    def remove_role(self, user_id: str, role: Role):
        """移除用户角色"""
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role)
            
            # 清除权限缓存
            if user_id in self._user_permissions:
                del self._user_permissions[user_id]
    
    def get_user_roles(self, user_id: str) -> Set[Role]:
        """获取用户的所有角色"""
        return self._user_roles.get(user_id, set())
    
    def create_custom_role(self, role_name: str, permissions: Set[Permission], 
                          description: str = "", inherits: Optional[Role] = None) -> str:
        """创建自定义角色"""
        role_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        self._custom_roles[role_id] = RoleDefinition(
            name=role_name,
            description=description,
            permissions=permissions,
            inherits=inherits
        )
        
        return role_id
    
    def list_roles(self) -> Dict[str, Dict]:
        """列出所有可用角色"""
        roles = {}
        
        # 系统角色
        for role, definition in ROLE_PERMISSIONS.items():
            roles[role.value] = {
                'name': definition.name,
                'description': definition.description,
                'permissions': [p.value for p in definition.permissions],
                'type': 'system'
            }
        
        # 自定义角色
        for role_id, definition in self._custom_roles.items():
            roles[role_id] = {
                'name': definition.name,
                'description': definition.description,
                'permissions': [p.value for p in definition.permissions],
                'type': 'custom'
            }
        
        return roles

# 权限检查装饰器
def require_permission(permission: Permission):
    """要求特定权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 这里需要从请求中获取user_id
            # 简化实现，实际应该从session或token中获取
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id:
                return {'error': 'Unauthorized'}, 401
            
            rbac = RBACManager()
            if not rbac.check_permission(user_id, permission):
                return {'error': 'Forbidden'}, 403
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(permissions: List[Permission]):
    """要求任一权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id:
                return {'error': 'Unauthorized'}, 401
            
            rbac = RBACManager()
            if not rbac.check_any_permission(user_id, permissions):
                return {'error': 'Forbidden'}, 403
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# 全局实例
rbac_manager = RBACManager()

if __name__ == '__main__':
    # 测试
    rbac = RBACManager()
    
    # 创建用户并分配角色
    user_id = "user_123"
    rbac.assign_role(user_id, Role.USER)
    
    # 检查权限
    print(f"用户 {user_id} 权限检查:")
    print(f"  CHAT_CREATE: {rbac.check_permission(user_id, Permission.CHAT_CREATE)}")
    print(f"  USER_MANAGE: {rbac.check_permission(user_id, Permission.USER_MANAGE)}")
    print(f"  MODEL_USE: {rbac.check_permission(user_id, Permission.MODEL_USE)}")
    
    # 获取所有权限
    perms = rbac.get_user_permissions(user_id)
    print(f"\n所有权限 ({len(perms)} 个):")
    for p in perms:
        print(f"  - {p.value}")
    
    # 列出角色
    print("\n可用角色:")
    roles = rbac.list_roles()
    for role_id, info in roles.items():
        print(f"  {role_id}: {info['name']} ({len(info['permissions'])} 个权限)")
