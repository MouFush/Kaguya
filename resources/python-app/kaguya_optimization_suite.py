#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI平台 - 综合优化套件
包含前端优化、性能提升、测试框架、运维工具
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
import hashlib
import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== 1. 性能监控与优化 ====================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    function_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    max_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    error_count: int = 0
    last_called: Optional[datetime] = None


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.slow_threshold_ms: float = 1000.0
        
    def monitor(self, func_name: str = None):
        """监控装饰器"""
        def decorator(func):
            name = func_name or func.__name__
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    self._record_success(name, start_time)
                    return result
                except Exception as e:
                    self._record_error(name, start_time)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    self._record_success(name, start_time)
                    return result
                except Exception as e:
                    self._record_error(name, start_time)
                    raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def _record_success(self, name: str, start_time: float):
        """记录成功调用"""
        elapsed_ms = (time.time() - start_time) * 1000
        
        if name not in self.metrics:
            self.metrics[name] = PerformanceMetrics(function_name=name)
        
        metric = self.metrics[name]
        metric.call_count += 1
        metric.total_time_ms += elapsed_ms
        metric.avg_time_ms = metric.total_time_ms / metric.call_count
        metric.max_time_ms = max(metric.max_time_ms, elapsed_ms)
        metric.min_time_ms = min(metric.min_time_ms, elapsed_ms)
        metric.last_called = datetime.now()
        
        # 慢查询警告
        if elapsed_ms > self.slow_threshold_ms:
            logger.warning(f"慢查询警告: {name} 耗时 {elapsed_ms:.2f}ms")
    
    def _record_error(self, name: str, start_time: float):
        """记录错误"""
        if name not in self.metrics:
            self.metrics[name] = PerformanceMetrics(function_name=name)
        self.metrics[name].error_count += 1
    
    def get_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "total_functions": len(self.metrics),
            "functions": [
                {
                    "name": m.function_name,
                    "calls": m.call_count,
                    "avg_ms": round(m.avg_time_ms, 2),
                    "max_ms": round(m.max_time_ms, 2),
                    "min_ms": round(m.min_time_ms, 2) if m.min_time_ms != float('inf') else 0,
                    "errors": m.error_count,
                    "error_rate": round(m.error_count / m.call_count * 100, 2) if m.call_count > 0 else 0
                }
                for m in sorted(self.metrics.values(), key=lambda x: x.avg_time_ms, reverse=True)
            ]
        }


# ==================== 2. 缓存系统 ====================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self.cache:
            item = self.cache[key]
            if item["expires"] > time.time():
                self.hit_count += 1
                return item["value"]
            else:
                del self.cache[key]
        
        self.miss_count += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires": time.time() + ttl,
            "created": datetime.now()
        }
    
    def delete(self, key: str):
        """删除缓存"""
        self.cache.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total = self.hit_count + self.miss_count
        return {
            "size": len(self.cache),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": round(self.hit_count / total * 100, 2) if total > 0 else 0
        }


# ==================== 3. 连接池管理 ====================

class ConnectionPool:
    """连接池管理器"""
    
    def __init__(self, max_size: int = 10, timeout: float = 30.0):
        self.max_size = max_size
        self.timeout = timeout
        self.pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.active_connections: int = 0
        self.total_created: int = 0
        
    async def acquire(self) -> Any:
        """获取连接"""
        try:
            return await asyncio.wait_for(self.pool.get(), timeout=self.timeout)
        except asyncio.TimeoutError:
            if self.active_connections < self.max_size:
                # 创建新连接
                self.active_connections += 1
                self.total_created += 1
                return await self._create_connection()
            raise
    
    async def release(self, connection: Any):
        """释放连接"""
        await self.pool.put(connection)
    
    async def _create_connection(self) -> Any:
        """创建连接（子类实现）"""
        raise NotImplementedError
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "pool_size": self.pool.qsize(),
            "active": self.active_connections,
            "max_size": self.max_size,
            "total_created": self.total_created
        }


# ==================== 4. 错误处理与重试 ====================

class RetryPolicy:
    """重试策略"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    logger.warning(f"重试 {attempt + 1}/{self.max_retries}, 等待 {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
        
        raise last_exception


# ==================== 5. 配置管理 ====================

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.configs: Dict[str, Any] = {}
        self.watchers: List[Callable] = []
        self._loaded = False
    
    def load(self, config_dict: Dict[str, Any]):
        """加载配置"""
        self.configs.update(config_dict)
        self._loaded = True
        self._notify_watchers()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        keys = key.split('.')
        value = self.configs
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置"""
        keys = key.split('.')
        config = self.configs
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._notify_watchers()
    
    def watch(self, callback: Callable):
        """监听配置变化"""
        self.watchers.append(callback)
    
    def _notify_watchers(self):
        """通知监听者"""
        for watcher in self.watchers:
            try:
                watcher(self.configs)
            except Exception as e:
                logger.error(f"配置监听者错误: {e}")


# ==================== 6. 健康检查 ====================

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.status: Dict[str, Dict] = {}
    
    def register(self, name: str, check_func: Callable):
        """注册健康检查"""
        self.checks[name] = check_func
    
    async def check_all(self) -> Dict[str, Any]:
        """执行所有检查"""
        results = {}
        overall_status = "healthy"
        
        for name, check_func in self.checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "timestamp": datetime.now().isoformat()
                }
                
                if not result:
                    overall_status = "degraded"
                    
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "checks": results,
            "timestamp": datetime.now().isoformat()
        }


# ==================== 7. 日志管理 ====================

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logs: List[Dict] = []
        
    def log(self, level: str, message: str, **kwargs):
        """记录日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": self.service_name,
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
        
        # 同时输出到标准日志
        logger.log(getattr(logging, level.upper()), message)
        
        return log_entry
    
    def info(self, message: str, **kwargs):
        return self.log("info", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        return self.log("warning", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        return self.log("error", message, **kwargs)
    
    def get_logs(self, level: str = None, limit: int = 100) -> List[Dict]:
        """获取日志"""
        filtered = self.logs
        if level:
            filtered = [l for l in filtered if l["level"] == level]
        return filtered[-limit:]


# ==================== 8. API限流 ====================

class RateLimiter:
    """API限流器"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - 60  # 1分钟窗口
        
        # 清理旧请求
        if key in self.requests:
            self.requests[key] = [t for t in self.requests[key] if t > window_start]
        else:
            self.requests[key] = []
        
        # 检查限流
        if len(self.requests[key]) >= self.requests_per_minute:
            return False
        
        # 记录请求
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余配额"""
        now = time.time()
        window_start = now - 60
        
        if key in self.requests:
            recent = [t for t in self.requests[key] if t > window_start]
            return max(0, self.requests_per_minute - len(recent))
        
        return self.requests_per_minute


# ==================== 9. 数据验证 ====================

class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_required(data: Dict, required_fields: List[str]) -> List[str]:
        """验证必填字段"""
        missing = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing.append(field)
        return missing
    
    @staticmethod
    def validate_type(value: Any, expected_type: type) -> bool:
        """验证类型"""
        return isinstance(value, expected_type)
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: float = None, 
                      max_val: float = None) -> bool:
        """验证范围"""
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


# ==================== 10. 全局优化管理器 ====================

class OptimizationManager:
    """优化管理器 - 统一管理所有优化功能"""
    
    def __init__(self):
        self.performance = PerformanceMonitor()
        self.cache = CacheManager()
        self.config = ConfigManager()
        self.health = HealthChecker()
        self.logger = StructuredLogger("kaguya_ai")
        self.rate_limiter = RateLimiter()
        self.validator = DataValidator()
        
        self.initialized = False
    
    async def initialize(self):
        """初始化优化系统"""
        if self.initialized:
            return
        
        print("=" * 70)
        print("🚀 初始化辉夜AI优化套件")
        print("=" * 70)
        
        # 加载默认配置
        self.config.load({
            "performance": {
                "slow_threshold_ms": 1000,
                "enable_monitoring": True
            },
            "cache": {
                "default_ttl": 300,
                "max_size": 1000
            },
            "rate_limit": {
                "requests_per_minute": 60
            }
        })
        
        # 注册健康检查
        self.health.register("cache", lambda: len(self.cache.cache) < 10000)
        self.health.register("memory", self._check_memory)
        
        self.initialized = True
        print("✅ 优化套件初始化完成")
    
    def _check_memory(self) -> bool:
        """检查内存使用"""
        import psutil
        memory = psutil.virtual_memory()
        return memory.percent < 90
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        return {
            "initialized": self.initialized,
            "performance": self.performance.get_report(),
            "cache": self.cache.get_stats(),
            "health": asyncio.run(self.health.check_all()) if self.initialized else None
        }


# ==================== 全局实例 ====================

_optimization_manager: Optional[OptimizationManager] = None


def get_optimization_manager() -> OptimizationManager:
    """获取优化管理器"""
    global _optimization_manager
    if _optimization_manager is None:
        _optimization_manager = OptimizationManager()
    return _optimization_manager


# ==================== 使用示例 ====================

async def example_usage():
    """使用示例"""
    opt = get_optimization_manager()
    await opt.initialize()
    
    # 使用性能监控
    @opt.performance.monitor("example_function")
    async def example_function():
        await asyncio.sleep(0.1)
        return "done"
    
    await example_function()
    
    # 使用缓存
    opt.cache.set("key", "value", ttl=60)
    value = opt.cache.get("key")
    print(f"缓存值: {value}")
    
    # 获取报告
    report = opt.get_optimization_report()
    print(f"\n优化报告:")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(example_usage())
