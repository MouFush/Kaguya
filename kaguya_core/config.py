#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理系统
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = "sqlite:///kaguya.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class CacheConfig:
    """缓存配置"""
    backend: str = "memory"  # memory, redis, memcached
    url: Optional[str] = None
    ttl: int = 3600
    max_size: int = 10000


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = field(default_factory=lambda: os.urandom(32).hex())
    jwt_expiry_hours: int = 24
    password_min_length: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    enable_mfa: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class KaguyaConfig:
    """
    辉夜AI平台统一配置
    
    集中管理所有模块的配置
    """
    # 基础配置
    app_name: str = "辉夜AI平台"
    app_version: str = "3.0.0"
    debug: bool = False
    env: str = "production"  # development, testing, production
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 5000
    workers: int = 4
    
    # 模块配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 功能开关
    enable_security: bool = True
    enable_optimization: bool = True
    enable_monitoring: bool = True
    enable_audit: bool = True
    
    # 路径配置
    data_dir: str = "./data"
    log_dir: str = "./logs"
    temp_dir: str = "./temp"
    
    # 扩展配置（用于模块特定配置）
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保目录存在
        for dir_path in [self.data_dir, self.log_dir, self.temp_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KaguyaConfig':
        """从字典创建配置"""
        # 处理嵌套配置
        if 'database' in data:
            data['database'] = DatabaseConfig(**data['database'])
        if 'cache' in data:
            data['cache'] = CacheConfig(**data['cache'])
        if 'security' in data:
            data['security'] = SecurityConfig(**data['security'])
        if 'logging' in data:
            data['logging'] = LoggingConfig(**data['logging'])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, path: str) -> 'KaguyaConfig':
        """从JSON文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'KaguyaConfig':
        """从YAML文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'KaguyaConfig':
        """从环境变量加载配置"""
        config = cls()
        
        # 基础配置
        if os.getenv('KAGUYA_DEBUG'):
            config.debug = os.getenv('KAGUYA_DEBUG').lower() == 'true'
        if os.getenv('KAGUYA_ENV'):
            config.env = os.getenv('KAGUYA_ENV')
        if os.getenv('KAGUYA_PORT'):
            config.port = int(os.getenv('KAGUYA_PORT'))
        
        # 数据库配置
        if os.getenv('KAGUYA_DATABASE_URL'):
            config.database.url = os.getenv('KAGUYA_DATABASE_URL')
        
        # 安全配置
        if os.getenv('KAGUYA_SECRET_KEY'):
            config.security.secret_key = os.getenv('KAGUYA_SECRET_KEY')
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self, path: str) -> None:
        """保存为JSON文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号路径）"""
        keys = key.split('.')
        value = self.to_dict()
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项（支持点号路径）"""
        keys = key.split('.')
        target = self
        
        for k in keys[:-1]:
            if hasattr(target, k):
                target = getattr(target, k)
            else:
                return
        
        setattr(target, keys[-1], value)


# 全局配置实例
_config: Optional[KaguyaConfig] = None


def get_config() -> KaguyaConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        # 尝试从配置文件加载
        config_paths = [
            './config.yaml',
            './config.json',
            './config.yml',
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                if path.endswith('.yaml') or path.endswith('.yml'):
                    _config = KaguyaConfig.from_yaml(path)
                else:
                    _config = KaguyaConfig.from_json(path)
                break
        else:
            # 从环境变量加载
            _config = KaguyaConfig.from_env()
    
    return _config


def set_config(config: KaguyaConfig) -> None:
    """设置全局配置实例"""
    global _config
    _config = config
