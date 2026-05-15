#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 核心基础框架
Kaguya AI Core Framework

提供统一的基础类、工具函数和配置管理，解决代码重复问题
"""

from .base_manager import BaseManager, SingletonMixin, ManagerRegistry
from .config import KaguyaConfig, get_config
from .exceptions import (
    KaguyaException, 
    ValidationError, 
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError
)
from .utils import (
    generate_id, 
    generate_secure_token,
    timestamp_now, 
    sanitize_string,
    validate_email,
    validate_uuid,
    hash_string,
    deep_merge,
    truncate_text,
    format_bytes,
    format_duration,
    safe_json_loads,
    safe_json_dumps,
    mask_sensitive_data,
    RateLimiter
)
from .logging import get_logger, StructuredLogger
from .models import (
    BaseModel,
    User,
    Session,
    APIKey,
    Message,
    Conversation,
    AuditLog,
    Task,
    Metric,
    Status,
    Priority
)

# 重构后的模块（可选导入）
try:
    from .audit_system_refactored import AuditLogger, AuditEventType, AuditSeverity
    from .security_framework_refactored import (
        SecurityManager,
        AuthenticationManager,
        PasswordManager,
        JWTManager,
        InputValidator,
        get_security_manager
    )
    REFACTORED_MODULES_AVAILABLE = True
except ImportError:
    REFACTORED_MODULES_AVAILABLE = False

__version__ = "3.0.0"
__all__ = [
    # 基础类
    'BaseManager',
    'SingletonMixin',
    'ManagerRegistry',
    
    # 配置
    'KaguyaConfig',
    'get_config',
    
    # 异常
    'KaguyaException',
    'ValidationError',
    'NotFoundError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    
    # 工具函数
    'generate_id',
    'generate_secure_token',
    'timestamp_now',
    'sanitize_string',
    'validate_email',
    'validate_uuid',
    'hash_string',
    'deep_merge',
    'truncate_text',
    'format_bytes',
    'format_duration',
    'safe_json_loads',
    'safe_json_dumps',
    'mask_sensitive_data',
    'RateLimiter',
    
    # 日志
    'get_logger',
    'StructuredLogger',
    
    # 模型
    'BaseModel',
    'User',
    'Session',
    'APIKey',
    'Message',
    'Conversation',
    'AuditLog',
    'Task',
    'Metric',
    'Status',
    'Priority',
]

# 如果重构模块可用，添加到导出
if REFACTORED_MODULES_AVAILABLE:
    __all__.extend([
        'AuditLogger',
        'AuditEventType',
        'AuditSeverity',
        'SecurityManager',
        'AuthenticationManager',
        'PasswordManager',
        'JWTManager',
        'InputValidator',
        'get_security_manager',
    ])
