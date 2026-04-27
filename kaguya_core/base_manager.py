#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础管理器类 - 提供统一的管理器模式实现
"""

import asyncio
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Dict, Any
from datetime import datetime
import logging

T = TypeVar('T')


class SingletonMixin:
    """单例模式混入类"""
    _instances: Dict[type, Any] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls: type[T], *args, **kwargs) -> T:
        """异步获取单例实例"""
        if cls not in cls._instances:
            async with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]
    
    @classmethod
    def get_instance_sync(cls: type[T], *args, **kwargs) -> T:
        """同步获取单例实例（用于非异步上下文）"""
        if cls not in cls._instances:
            cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]


class BaseManager(ABC):
    """
    基础管理器类
    
    所有管理器的基类，提供统一的初始化、配置和生命周期管理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._initialized = False
        self._config = config or {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._start_time: Optional[datetime] = None
        
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    @property
    def logger(self):
        """获取日志记录器"""
        return self._logger
    
    async def initialize(self) -> None:
        """
        初始化管理器
        
        子类应该重写 _do_initialize 方法而不是此方法
        """
        if self._initialized:
            self.logger.debug(f"{self.__class__.__name__} 已经初始化")
            return
        
        self.logger.info(f"🚀 初始化 {self.__class__.__name__}...")
        self._start_time = datetime.now()
        
        try:
            await self._do_initialize()
            self._initialized = True
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self.logger.info(f"✅ {self.__class__.__name__} 初始化完成 ({elapsed:.2f}s)")
        except Exception as e:
            self.logger.error(f"❌ {self.__class__.__name__} 初始化失败: {e}")
            raise
    
    @abstractmethod
    async def _do_initialize(self) -> None:
        """
        实际的初始化逻辑
        
        子类必须实现此方法
        """
        pass
    
    async def shutdown(self) -> None:
        """
        关闭管理器
        
        子类可以重写 _do_shutdown 方法添加自定义清理逻辑
        """
        if not self._initialized:
            return
        
        self.logger.info(f"🛑 关闭 {self.__class__.__name__}...")
        
        try:
            await self._do_shutdown()
            self._initialized = False
            self.logger.info(f"✅ {self.__class__.__name__} 已关闭")
        except Exception as e:
            self.logger.error(f"❌ {self.__class__.__name__} 关闭失败: {e}")
            raise
    
    async def _do_shutdown(self) -> None:
        """实际的关闭逻辑，子类可以重写"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """设置配置项"""
        self._config[key] = value
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        返回管理器的健康状态
        """
        return {
            'status': 'healthy' if self._initialized else 'not_initialized',
            'initialized': self._initialized,
            'uptime': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            'class': self.__class__.__name__,
        }


class ManagerRegistry:
    """管理器注册表 - 统一管理所有管理器实例"""
    
    _managers: Dict[str, BaseManager] = {}
    
    @classmethod
    def register(cls, name: str, manager: BaseManager) -> None:
        """注册管理器"""
        cls._managers[name] = manager
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseManager]:
        """获取管理器"""
        return cls._managers.get(name)
    
    @classmethod
    async def initialize_all(cls) -> None:
        """初始化所有管理器"""
        for name, manager in cls._managers.items():
            if not manager.is_initialized:
                await manager.initialize()
    
    @classmethod
    async def shutdown_all(cls) -> None:
        """关闭所有管理器"""
        for name, manager in reversed(list(cls._managers.items())):
            if manager.is_initialized:
                await manager.shutdown()
    
    @classmethod
    def health_check_all(cls) -> Dict[str, Dict[str, Any]]:
        """检查所有管理器健康状态"""
        return {
            name: manager.health_check()
            for name, manager in cls._managers.items()
        }
