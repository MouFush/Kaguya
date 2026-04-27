#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能缓存系统 - 多层次缓存管理
功能: 内存缓存、磁盘缓存、智能过期策略、缓存预热
"""

import json
import hashlib
import pickle
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import os
import functools


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0


class LRUCache:
    """LRU内存缓存"""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: float = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.current_memory = 0
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.stats['total_requests'] += 1
            
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # 检查是否过期
            if time.time() > entry.expires_at:
                self._remove_entry(key)
                self.stats['misses'] += 1
                return None
            
            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.cache.move_to_end(key)
            
            self.stats['hits'] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: float = 300) -> bool:
        """设置缓存值"""
        with self.lock:
            # 计算值大小
            try:
                size = len(pickle.dumps(value))
            except:
                size = 1024  # 默认估计大小
            
            # 检查是否超过单个条目大小限制
            if size > self.max_memory_bytes * 0.1:  # 单个条目不超过10%
                return False
            
            # 如果key已存在，先移除旧值
            if key in self.cache:
                self._remove_entry(key)
            
            # 检查是否需要清理空间
            while (len(self.cache) >= self.max_size or 
                   self.current_memory + size > self.max_memory_bytes):
                if not self.cache:
                    break
                self._evict_oldest()
            
            # 创建新条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=time.time() + ttl_seconds,
                size_bytes=size
            )
            
            self.cache[key] = entry
            self.current_memory += size
            self.cache.move_to_end(key)
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0
    
    def _remove_entry(self, key: str):
        """移除条目（内部方法）"""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_memory -= entry.size_bytes
    
    def _evict_oldest(self):
        """淘汰最旧的条目"""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.current_memory -= entry.size_bytes
            self.stats['evictions'] += 1
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with self.lock:
            total = self.stats['total_requests']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage_mb': self.current_memory / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'hit_rate': round(hit_rate, 2),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'evictions': self.stats['evictions']
            }
    
    def cleanup_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time > entry.expires_at
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
            
            return len(expired_keys)


class DiskCache:
    """磁盘缓存"""
    
    def __init__(self, cache_dir: str = './cache', max_size_mb: float = 500):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        
        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)
        
        # 启动清理线程
        self._start_cleanup_thread()
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 使用hash作为文件名
        filename = hashlib.md5(key.encode()).hexdigest() + '.cache'
        return os.path.join(self.cache_dir, filename)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            self.stats['total_requests'] += 1
            
            cache_path = self._get_cache_path(key)
            
            if not os.path.exists(cache_path):
                self.stats['misses'] += 1
                return None
            
            try:
                with open(cache_path, 'rb') as f:
                    entry = pickle.load(f)
                
                # 检查是否过期
                if time.time() > entry['expires_at']:
                    os.remove(cache_path)
                    self.stats['misses'] += 1
                    return None
                
                self.stats['hits'] += 1
                return entry['value']
            except Exception:
                self.stats['misses'] += 1
                return None
    
    def set(self, key: str, value: Any, ttl_seconds: float = 3600) -> bool:
        """设置缓存值"""
        try:
            cache_path = self._get_cache_path(key)
            
            entry = {
                'key': key,
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl_seconds
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(entry, f)
            
            # 检查总大小，必要时清理
            self._cleanup_if_needed()
            
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            return True
        return False
    
    def _cleanup_if_needed(self):
        """如果需要则清理缓存"""
        total_size = self._get_total_size()
        
        if total_size > self.max_size_bytes:
            # 获取所有缓存文件按修改时间排序
            files = []
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if filename.endswith('.cache'):
                    files.append((filepath, os.path.getmtime(filepath)))
            
            # 删除最旧的文件直到满足大小限制
            files.sort(key=lambda x: x[1])
            
            for filepath, _ in files:
                if total_size <= self.max_size_bytes * 0.8:  # 清理到80%
                    break
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    total_size -= size
                except:
                    pass
    
    def _get_total_size(self) -> int:
        """获取缓存总大小"""
        total = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.cache'):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    total += os.path.getsize(filepath)
                except:
                    pass
        return total
    
    def _start_cleanup_thread(self):
        """启动定期清理线程"""
        def cleanup_task():
            while True:
                time.sleep(3600)  # 每小时清理一次
                self.cleanup_expired()
        
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        current_time = time.time()
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.cache'):
                continue
            
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'rb') as f:
                    entry = pickle.load(f)
                
                if current_time > entry['expires_at']:
                    os.remove(filepath)
                    count += 1
            except:
                pass
        
        return count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            total = self.stats['total_requests']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            
            return {
                'size_mb': self._get_total_size() / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024),
                'hit_rate': round(hit_rate, 2),
                'hits': self.stats['hits'],
                'misses': self.stats['misses']
            }


class IntelligentCache:
    """智能缓存管理器 - 多级缓存"""
    
    def __init__(self):
        self.l1_cache = LRUCache(max_size=1000, max_memory_mb=50)  # L1: 内存
        self.l2_cache = DiskCache(cache_dir='./cache/l2', max_size_mb=200)  # L2: 磁盘
        self.lock = threading.RLock()
        
        # 缓存策略配置
        self.strategies = {
            'api_response': {'l1_ttl': 60, 'l2_ttl': 300},      # API响应
            'user_session': {'l1_ttl': 1800, 'l2_ttl': 7200},   # 用户会话
            'analytics_result': {'l1_ttl': 300, 'l2_ttl': 3600}, # 分析结果
            'document_processed': {'l1_ttl': 600, 'l2_ttl': 7200}, # 文档处理
            'static_data': {'l1_ttl': 3600, 'l2_ttl': 86400},    # 静态数据
        }
    
    def get(self, key: str, cache_type: str = 'default') -> Optional[Any]:
        """
        获取缓存值，多级缓存策略
        
        Args:
            key: 缓存键
            cache_type: 缓存类型，影响TTL策略
        
        Returns:
            缓存值或None
        """
        # 先查L1
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # 再查L2
        value = self.l2_cache.get(key)
        if value is not None:
            # 回填L1
            strategy = self.strategies.get(cache_type, self.strategies['static_data'])
            self.l1_cache.set(key, value, strategy['l1_ttl'])
            return value
        
        return None
    
    def set(self, key: str, value: Any, cache_type: str = 'default') -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            cache_type: 缓存类型
        """
        strategy = self.strategies.get(cache_type, self.strategies['static_data'])
        
        # 写入L1
        self.l1_cache.set(key, value, strategy['l1_ttl'])
        
        # 写入L2
        self.l2_cache.set(key, value, strategy['l2_ttl'])
        
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        self.l1_cache.delete(key)
        self.l2_cache.delete(key)
        return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式批量删除缓存"""
        # 这里简化实现，实际可以使用更复杂的模式匹配
        count = 0
        # L1清理
        keys_to_delete = [k for k in self.l1_cache.cache.keys() if pattern in k]
        for key in keys_to_delete:
            self.l1_cache.delete(key)
            count += 1
        
        return count
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            'l1_memory': self.l1_cache.get_stats(),
            'l2_disk': self.l2_cache.get_stats()
        }
    
    def clear_all(self):
        """清空所有缓存"""
        self.l1_cache.clear()
        # L2不清空，保留持久化数据


def cached(cache_type: str = 'default', key_prefix: str = ''):
    """
    缓存装饰器
    
    Args:
        cache_type: 缓存类型
        key_prefix: 键前缀
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # 尝试从缓存获取
            cache = intelligent_cache
            result = cache.get(cache_key, cache_type)
            
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache.set(cache_key, result, cache_type)
            
            return result
        
        return wrapper
    return decorator


# 全局缓存实例
intelligent_cache = IntelligentCache()


# 便捷函数
def cache_get(key: str, cache_type: str = 'default') -> Optional[Any]:
    """获取缓存"""
    return intelligent_cache.get(key, cache_type)


def cache_set(key: str, value: Any, cache_type: str = 'default') -> bool:
    """设置缓存"""
    return intelligent_cache.set(key, value, cache_type)


def cache_delete(key: str) -> bool:
    """删除缓存"""
    return intelligent_cache.delete(key)


def cache_stats() -> Dict:
    """获取缓存统计"""
    return intelligent_cache.get_stats()


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("智能缓存系统测试")
    print("=" * 60)
    
    cache = IntelligentCache()
    
    # 测试基本操作
    print("\n1. 基本缓存操作测试")
    cache.set('user:1', {'name': '张三', 'age': 25}, 'user_session')
    cache.set('user:2', {'name': '李四', 'age': 30}, 'user_session')
    
    user1 = cache.get('user:1', 'user_session')
    print(f"获取用户1: {user1}")
    
    user2 = cache.get('user:2', 'user_session')
    print(f"获取用户2: {user2}")
    
    # 测试缓存统计
    print("\n2. 缓存统计")
    stats = cache.get_stats()
    print(f"L1缓存: {stats['l1_memory']}")
    print(f"L2缓存: {stats['l2_disk']}")
    
    # 测试装饰器
    print("\n3. 缓存装饰器测试")
    
    @cached(cache_type='api_response', key_prefix='test')
    def expensive_computation(n: int) -> int:
        """模拟耗时计算"""
        time.sleep(0.1)
        return n * n
    
    start = time.time()
    result1 = expensive_computation(10)
    time1 = time.time() - start
    
    start = time.time()
    result2 = expensive_computation(10)  # 应该从缓存读取
    time2 = time.time() - start
    
    print(f"第一次计算: {result1}, 耗时: {time1:.3f}s")
    print(f"第二次计算(缓存): {result2}, 耗时: {time2:.3f}s")
    print(f"缓存加速: {time1/time2:.1f}x")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
