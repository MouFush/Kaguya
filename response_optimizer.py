#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应优化模块 - 提升API响应速度和用户体验
功能: 缓存、压缩、流式优化、连接池
"""

import functools
import hashlib
import json
import time
import gzip
from typing import Dict, Any, Optional, Callable
from collections import OrderedDict
import threading
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU缓存 - 用于缓存频繁访问的数据"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        """
        Args:
            maxsize: 最大缓存条目数
            ttl: 缓存过期时间（秒）
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                # 检查是否过期
                if time.time() - self.timestamps[key] > self.ttl:
                    self.delete(key)
                    return None
                
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.maxsize:
                    # 移除最旧的条目
                    oldest = next(iter(self.cache))
                    self.delete(oldest)
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def delete(self, key: str):
        """删除缓存条目"""
        with self.lock:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def cached(self, func: Callable) -> Callable:
        """装饰器 - 缓存函数结果"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = self._generate_key(func.__name__, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_value = self.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            self.set(cache_key, result)
            return result
        
        return wrapper


class ResponseCompressor:
    """响应压缩器 - 压缩大响应数据"""
    
    def __init__(self, min_size: int = 1024, level: int = 6):
        """
        Args:
            min_size: 最小压缩大小（字节）
            level: 压缩级别（1-9）
        """
        self.min_size = min_size
        self.level = level
    
    def compress(self, data: bytes) -> tuple[bytes, bool]:
        """
        压缩数据
        
        Returns:
            (压缩后的数据, 是否被压缩)
        """
        if len(data) < self.min_size:
            return data, False
        
        compressed = gzip.compress(data, compresslevel=self.level)
        
        # 只有当压缩有效时才使用压缩数据
        if len(compressed) < len(data):
            return compressed, True
        
        return data, False
    
    def decompress(self, data: bytes) -> bytes:
        """解压数据"""
        try:
            return gzip.decompress(data)
        except Exception:
            return data


class StreamingOptimizer:
    """流式响应优化器"""
    
    def __init__(self, chunk_size: int = 1024, buffer_timeout: float = 0.05):
        """
        Args:
            chunk_size: 块大小（字节）
            buffer_timeout: 缓冲超时（秒）
        """
        self.chunk_size = chunk_size
        self.buffer_timeout = buffer_timeout
    
    def optimize_generator(self, generator):
        """
        优化生成器 - 批量处理小块
        
        Args:
            generator: 原始生成器
        
        Yields:
            优化后的数据块
        """
        buffer = []
        last_yield_time = time.time()
        
        for chunk in generator:
            buffer.append(chunk)
            current_time = time.time()
            
            # 检查是否应该输出缓冲数据
            buffer_size = sum(len(c) for c in buffer)
            time_since_last_yield = current_time - last_yield_time
            
            if buffer_size >= self.chunk_size or time_since_last_yield >= self.buffer_timeout:
                # 合并缓冲数据
                combined = ''.join(buffer) if isinstance(buffer[0], str) else b''.join(buffer)
                yield combined
                buffer = []
                last_yield_time = current_time
        
        # 输出剩余缓冲数据
        if buffer:
            combined = ''.join(buffer) if isinstance(buffer[0], str) else b''.join(buffer)
            yield combined


class ConnectionPool:
    """简单的连接池管理"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.pool = []
        self.in_use = set()
        self.lock = threading.Lock()
    
    def acquire(self):
        """获取连接"""
        with self.lock:
            if self.pool:
                conn = self.pool.pop()
                self.in_use.add(id(conn))
                return conn
            return None
    
    def release(self, conn):
        """释放连接"""
        with self.lock:
            conn_id = id(conn)
            if conn_id in self.in_use:
                self.in_use.remove(conn_id)
                if len(self.pool) < self.max_connections:
                    self.pool.append(conn)


class ResponseOptimizer:
    """响应优化器 - 主类"""
    
    def __init__(self):
        self.cache = LRUCache(maxsize=1000, ttl=300)
        self.compressor = ResponseCompressor(min_size=1024, level=6)
        self.streaming = StreamingOptimizer(chunk_size=1024, buffer_timeout=0.05)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def cached_response(self, ttl: int = 300):
        """
        装饰器 - 缓存API响应
        
        Usage:
            @optimizer.cached_response(ttl=60)
            def my_api():
                return expensive_operation()
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
                
                # 尝试从缓存获取
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit: {func.__name__}")
                    return cached
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 存入缓存
                self.cache.set(cache_key, result)
                return result
            
            return wrapper
        return decorator
    
    def compress_response(self, data: bytes, content_type: str = 'application/json') -> tuple[bytes, Dict[str, str]]:
        """
        压缩响应数据
        
        Returns:
            (压缩后的数据, 响应头)
        """
        headers = {}
        
        compressed, was_compressed = self.compressor.compress(data)
        
        if was_compressed:
            headers['Content-Encoding'] = 'gzip'
            headers['Vary'] = 'Accept-Encoding'
        
        headers['Content-Length'] = str(len(compressed))
        
        return compressed, headers
    
    def optimize_stream(self, generator):
        """优化流式响应"""
        return self.streaming.optimize_generator(generator)
    
    def prefetch(self, func: Callable, *args, **kwargs):
        """预取数据到缓存"""
        def task():
            try:
                result = func(*args, **kwargs)
                cache_key = f"{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
                self.cache.set(cache_key, result)
            except Exception as e:
                logger.error(f"Prefetch failed: {e}")
        
        self.executor.submit(task)


# 全局优化器实例
response_optimizer = ResponseOptimizer()


# 便捷函数
def cached(ttl: int = 300):
    """缓存装饰器"""
    return response_optimizer.cached_response(ttl)


def compress(data: bytes) -> tuple[bytes, Dict[str, str]]:
    """压缩数据"""
    return response_optimizer.compress_response(data)


def optimize_stream(generator):
    """优化流式响应"""
    return response_optimizer.optimize_stream(generator)


# 测试代码
if __name__ == '__main__':
    # 测试缓存
    cache = LRUCache(maxsize=100, ttl=5)
    
    @cache.cached
    def expensive_function(x):
        time.sleep(1)
        return x * x
    
    # 第一次调用 - 慢
    start = time.time()
    result1 = expensive_function(5)
    print(f"First call: {time.time() - start:.2f}s, result: {result1}")
    
    # 第二次调用 - 快（从缓存）
    start = time.time()
    result2 = expensive_function(5)
    print(f"Second call: {time.time() - start:.2f}s, result: {result2}")
    
    # 测试压缩
    compressor = ResponseCompressor()
    test_data = b"Hello World! " * 1000
    compressed, was_compressed = compressor.compress(test_data)
    print(f"\nOriginal size: {len(test_data)} bytes")
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(compressed) / len(test_data):.2%}")
