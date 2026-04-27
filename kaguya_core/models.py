#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据模型定义

集中管理所有模块共享的数据模型，避免重复定义
"""

from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class Status(Enum):
    """通用状态枚举"""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    COMPLETED = "completed"


class Priority(Enum):
    """优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BaseModel:
    """基础数据模型"""
    id: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    status: Status = Status.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举类型
        if isinstance(self.status, Status):
            data['status'] = self.status.value
        return data
    
    def update(self, **kwargs) -> None:
        """更新字段"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow().isoformat()


@dataclass
class User(BaseModel):
    """用户模型"""
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: str = "user"
    permissions: Set[str] = field(default_factory=set)
    last_login: Optional[str] = None
    is_active: bool = True


@dataclass
class Session(BaseModel):
    """会话模型"""
    user_id: str = ""
    token: str = ""
    expires_at: Optional[str] = None
    ip_address: str = ""
    user_agent: str = ""


@dataclass
class APIKey(BaseModel):
    """API密钥模型"""
    user_id: str = ""
    key_hash: str = ""
    name: str = ""
    permissions: Set[str] = field(default_factory=set)
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    usage_count: int = 0


@dataclass
class Message(BaseModel):
    """消息模型"""
    conversation_id: str = ""
    user_id: str = ""
    role: str = ""  # user, assistant, system
    content: str = ""
    tokens: int = 0
    model: str = ""
    latency_ms: float = 0.0


@dataclass
class Conversation(BaseModel):
    """对话模型"""
    user_id: str = ""
    title: str = ""
    message_count: int = 0
    total_tokens: int = 0
    model: str = ""


@dataclass
class AuditLog(BaseModel):
    """审计日志模型"""
    event_type: str = ""
    action: str = ""
    user_id: Optional[str] = None
    ip_address: str = ""
    resource_type: str = ""
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"


@dataclass
class Task(BaseModel):
    """任务模型"""
    name: str = ""
    description: str = ""
    priority: Priority = Priority.MEDIUM
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Metric(BaseModel):
    """指标模型"""
    name: str = ""
    value: float = 0.0
    unit: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CacheEntry:
    """缓存条目模型"""
    key: str
    value: Any
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    access_count: int = 0
    last_accessed: Optional[str] = None


# 模型注册表
MODEL_REGISTRY = {
    'user': User,
    'session': Session,
    'api_key': APIKey,
    'message': Message,
    'conversation': Conversation,
    'audit_log': AuditLog,
    'task': Task,
    'metric': Metric,
}


def get_model(model_name: str) -> Optional[type]:
    """获取模型类"""
    return MODEL_REGISTRY.get(model_name.lower())


def create_model(model_name: str, **kwargs) -> Optional[BaseModel]:
    """创建模型实例"""
    model_class = get_model(model_name)
    if model_class:
        return model_class(**kwargs)
    return None
