#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理模块
"""

import json
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class StructuredLogFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class StructuredLogger:
    """
    结构化日志记录器
    
    提供统一的日志记录接口，支持结构化输出
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self._logger = logging.getLogger(name)
        
        # 配置日志级别
        level = self.config.get('level', 'INFO')
        self._logger.setLevel(getattr(logging, level.upper()))
        
        # 配置处理器
        if not self._logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """设置日志处理器"""
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 根据配置选择格式化器
        if self.config.get('structured', False):
            formatter = StructuredLogFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # 文件处理器（如果配置了日志文件）
        log_file = self.config.get('file')
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
    
    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """内部日志方法"""
        extra_data = extra or {}
        
        # 创建日志记录
        log_method = getattr(self._logger, level.lower())
        
        # 如果有额外数据，使用extra参数
        if extra_data:
            record = logging.LogRecord(
                name=self.name,
                level=getattr(logging, level.upper()),
                pathname='',
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            record.extra_data = extra_data
            self._logger.handle(record)
        else:
            log_method(message)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录调试日志"""
        self._log('DEBUG', message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录信息日志"""
        self._log('INFO', message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录警告日志"""
        self._log('WARNING', message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录错误日志"""
        self._log('ERROR', message, extra)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """记录严重错误日志"""
        self._log('CRITICAL', message, extra)
    
    def exception(self, message: str, exc_info: bool = True) -> None:
        """记录异常日志"""
        self._logger.exception(message, exc_info=exc_info)


# 缓存的日志记录器
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    获取结构化日志记录器
    
    Args:
        name: 日志记录器名称
        config: 配置选项
        
    Returns:
        StructuredLogger实例
    """
    cache_key = f"{name}_{hash(str(config))}"
    
    if cache_key not in _loggers:
        _loggers[cache_key] = StructuredLogger(name, config)
    
    return _loggers[cache_key]


def configure_logging(
    level: str = "INFO",
    format: str = "standard",
    file: Optional[str] = None
) -> None:
    """
    配置全局日志
    
    Args:
        level: 日志级别
        format: 格式类型 (standard, structured)
        file: 日志文件路径
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    
    if format == "structured":
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器
    if file:
        Path(file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
