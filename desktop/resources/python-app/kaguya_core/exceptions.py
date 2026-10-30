#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一异常处理模块
"""

from typing import Optional, Dict, Any
from datetime import datetime


class KaguyaException(Exception):
    """
    辉夜AI平台基础异常类
    
    所有自定义异常的基类
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error': {
                'code': self.code,
                'message': self.message,
                'details': self.details,
                'timestamp': self.timestamp,
            }
        }
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class ValidationError(KaguyaException):
    """数据验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        super().__init__(
            message=message,
            code='VALIDATION_ERROR',
            details=details,
            status_code=400
        )


class NotFoundError(KaguyaException):
    """资源不存在错误"""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} '{identifier}' not found"
        
        super().__init__(
            message=message,
            code='NOT_FOUND',
            details={'resource': resource, 'identifier': identifier},
            status_code=404
        )


class AuthenticationError(KaguyaException):
    """认证错误"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code='AUTHENTICATION_ERROR',
            status_code=401
        )


class AuthorizationError(KaguyaException):
    """授权错误"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            code='AUTHORIZATION_ERROR',
            status_code=403
        )


class RateLimitError(KaguyaException):
    """速率限制错误"""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            code='RATE_LIMIT_EXCEEDED',
            details={'retry_after': retry_after},
            status_code=429
        )


class ServiceUnavailableError(KaguyaException):
    """服务不可用错误"""
    
    def __init__(self, service: str):
        super().__init__(
            message=f"Service '{service}' is unavailable",
            code='SERVICE_UNAVAILABLE',
            details={'service': service},
            status_code=503
        )


class DatabaseError(KaguyaException):
    """数据库错误"""
    
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            code='DATABASE_ERROR',
            details={'operation': operation},
            status_code=500
        )


class ExternalServiceError(KaguyaException):
    """外部服务错误"""
    
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service '{service}' error: {message}",
            code='EXTERNAL_SERVICE_ERROR',
            details={'service': service},
            status_code=502
        )


# 错误码映射
ERROR_CODES = {
    'VALIDATION_ERROR': 400,
    'AUTHENTICATION_ERROR': 401,
    'AUTHORIZATION_ERROR': 403,
    'NOT_FOUND': 404,
    'RATE_LIMIT_EXCEEDED': 429,
    'INTERNAL_ERROR': 500,
    'EXTERNAL_SERVICE_ERROR': 502,
    'SERVICE_UNAVAILABLE': 503,
}
