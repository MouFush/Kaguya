#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API限流和配额管理系统
参考: Redis Rate Limiting, Token Bucket Algorithm
"""

import time
import json
import sqlite3
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import os

class RateLimitStrategy(Enum):
    """限流策略"""
    TOKEN_BUCKET = "token_bucket"  # 令牌桶
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    FIXED_WINDOW = "fixed_window"  # 固定窗口

@dataclass
class RateLimitConfig:
    """限流配置"""
    requests_per_second: float = 10.0
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 20  # 突发流量容量
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET

class TokenBucket:
    """令牌桶限流器"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # 每秒生成令牌数
        self.capacity = capacity  # 桶容量
        self.tokens = capacity  # 当前令牌数
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """消费令牌，返回(是否成功, 等待时间)"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # 生成新令牌
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # 计算需要等待的时间
                wait_time = (tokens - self.tokens) / self.rate
                return False, wait_time
    
    def get_status(self) -> Dict:
        """获取令牌桶状态"""
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            current_tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            
            return {
                'tokens': current_tokens,
                'capacity': self.capacity,
                'rate': self.rate,
                'utilization': 1 - (current_tokens / self.capacity)
            }

class SlidingWindow:
    """滑动窗口限流器"""
    
    def __init__(self, window_size: int, max_requests: int):
        self.window_size = window_size  # 窗口大小（秒）
        self.max_requests = max_requests  # 窗口内最大请求数
        self.requests = []  # 请求时间戳列表
        self._lock = threading.Lock()
    
    def allow_request(self) -> Tuple[bool, float]:
        """检查是否允许请求"""
        with self._lock:
            now = time.time()
            window_start = now - self.window_size
            
            # 清理过期请求
            self.requests = [t for t in self.requests if t > window_start]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, 0.0
            else:
                # 计算需要等待的时间
                wait_time = self.requests[0] - window_start
                return False, wait_time
    
    def get_status(self) -> Dict:
        """获取窗口状态"""
        with self._lock:
            now = time.time()
            window_start = now - self.window_size
            self.requests = [t for t in self.requests if t > window_start]
            
            return {
                'current_requests': len(self.requests),
                'max_requests': self.max_requests,
                'window_size': self.window_size,
                'utilization': len(self.requests) / self.max_requests
            }

class RateLimiter:
    """API限流管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'rate_limits.db')
        self._init_database()
        
        # 内存中的限流器缓存
        self._buckets: Dict[str, TokenBucket] = {}
        self._windows: Dict[str, SlidingWindow] = {}
        self._lock = threading.Lock()
        
        # 默认配置
        self.default_config = RateLimitConfig()
        
        # 清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 限流记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_limit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                timestamp REAL NOT NULL,
                endpoint TEXT,
                allowed INTEGER NOT NULL
            )
        ''')
        
        # 配额记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quota_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_bucket(self, key: str, config: RateLimitConfig) -> TokenBucket:
        """获取或创建令牌桶"""
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    rate=config.requests_per_second,
                    capacity=config.burst_size
                )
            return self._buckets[key]
    
    def _get_window(self, key: str, window_size: int, max_requests: int) -> SlidingWindow:
        """获取或创建滑动窗口"""
        with self._lock:
            window_key = f"{key}_{window_size}"
            if window_key not in self._windows:
                self._windows[window_key] = SlidingWindow(window_size, max_requests)
            return self._windows[window_key]
    
    def check_rate_limit(self, key: str, 
                        endpoint: Optional[str] = None,
                        config: Optional[RateLimitConfig] = None) -> Dict:
        """检查限流状态"""
        config = config or self.default_config
        
        # 检查令牌桶
        bucket = self._get_bucket(key, config)
        allowed, wait_time = bucket.consume()
        
        # 记录到数据库
        self._record_limit_check(key, endpoint, allowed)
        
        if not allowed:
            return {
                'allowed': False,
                'wait_time': wait_time,
                'retry_after': int(wait_time) + 1,
                'limit': config.requests_per_second,
                'remaining': 0
            }
        
        # 检查滑动窗口（分钟级）
        window = self._get_window(key, 60, config.requests_per_minute)
        window_allowed, window_wait = window.allow_request()
        
        if not window_allowed:
            return {
                'allowed': False,
                'wait_time': window_wait,
                'retry_after': int(window_wait) + 1,
                'limit': config.requests_per_minute,
                'remaining': 0
            }
        
        # 获取状态
        bucket_status = bucket.get_status()
        window_status = window.get_status()
        
        return {
            'allowed': True,
            'wait_time': 0,
            'limit': config.requests_per_minute,
            'remaining': config.requests_per_minute - window_status['current_requests'],
            'reset_time': int(time.time()) + 60,
            'bucket_utilization': bucket_status['utilization'],
            'window_utilization': window_status['utilization']
        }
    
    def _record_limit_check(self, key: str, endpoint: Optional[str], allowed: bool):
        """记录限流检查"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rate_limit_records (key, timestamp, endpoint, allowed)
                VALUES (?, ?, ?, ?)
            ''', (key, time.time(), endpoint, 1 if allowed else 0))
            conn.commit()
            conn.close()
        except:
            pass  # 忽略记录错误
    
    def check_quota(self, key: str, resource_type: str, 
                   amount: int = 1, limit: int = 1000) -> Dict:
        """检查配额"""
        # 获取当前使用量
        current_usage = self._get_quota_usage(key, resource_type, 'daily')
        
        if current_usage + amount > limit:
            return {
                'allowed': False,
                'current': current_usage,
                'limit': limit,
                'remaining': max(0, limit - current_usage),
                'requested': amount
            }
        
        # 记录使用
        self._record_quota_usage(key, resource_type, amount)
        
        return {
            'allowed': True,
            'current': current_usage + amount,
            'limit': limit,
            'remaining': limit - current_usage - amount,
            'requested': amount
        }
    
    def _get_quota_usage(self, key: str, resource_type: str, 
                        period: str = 'daily') -> int:
        """获取配额使用量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if period == 'daily':
                start_time = time.time() - 86400
            elif period == 'hourly':
                start_time = time.time() - 3600
            else:
                start_time = 0
            
            cursor.execute('''
                SELECT SUM(amount) FROM quota_records
                WHERE key = ? AND resource_type = ? AND timestamp > ?
            ''', (key, resource_type, start_time))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] or 0
        except:
            return 0
    
    def _record_quota_usage(self, key: str, resource_type: str, amount: int):
        """记录配额使用"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quota_records (key, resource_type, amount, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (key, resource_type, amount, time.time()))
            conn.commit()
            conn.close()
        except:
            pass
    
    def get_rate_limit_headers(self, key: str, 
                               endpoint: Optional[str] = None) -> Dict[str, str]:
        """获取限流相关的HTTP头"""
        result = self.check_rate_limit(key, endpoint)
        
        headers = {
            'X-RateLimit-Limit': str(result.get('limit', 0)),
            'X-RateLimit-Remaining': str(result.get('remaining', 0)),
            'X-RateLimit-Reset': str(result.get('reset_time', 0)),
        }
        
        if not result['allowed']:
            headers['Retry-After'] = str(result.get('retry_after', 60))
        
        return headers
    
    def get_statistics(self, key: Optional[str] = None, 
                      hours: int = 24) -> Dict:
        """获取限流统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_time = time.time() - (hours * 3600)
            
            # 基础统计
            if key:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN allowed = 1 THEN 1 ELSE 0 END) as allowed,
                        SUM(CASE WHEN allowed = 0 THEN 1 ELSE 0 END) as blocked
                    FROM rate_limit_records
                    WHERE key = ? AND timestamp > ?
                ''', (key, start_time))
            else:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN allowed = 1 THEN 1 ELSE 0 END) as allowed,
                        SUM(CASE WHEN allowed = 0 THEN 1 ELSE 0 END) as blocked
                    FROM rate_limit_records
                    WHERE timestamp > ?
                ''', (start_time,))
            
            row = cursor.fetchone()
            conn.close()
            
            return {
                'total_requests': row[0] or 0,
                'allowed': row[1] or 0,
                'blocked': row[2] or 0,
                'block_rate': (row[2] / row[0] * 100) if row[0] > 0 else 0,
                'period_hours': hours
            }
        except:
            return {'error': 'Failed to get statistics'}
    
    def _cleanup_loop(self):
        """清理过期数据的循环"""
        while True:
            time.sleep(3600)  # 每小时清理一次
            self._cleanup_old_data()
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 清理7天前的限流记录
            cutoff_time = time.time() - (7 * 86400)
            cursor.execute('''
                DELETE FROM rate_limit_records WHERE timestamp < ?
            ''', (cutoff_time,))
            
            # 清理30天前的配额记录
            cutoff_time = time.time() - (30 * 86400)
            cursor.execute('''
                DELETE FROM quota_records WHERE timestamp < ?
            ''', (cutoff_time,))
            
            conn.commit()
            conn.close()
        except:
            pass

# 全局实例
rate_limiter = RateLimiter()

# 装饰器：自动限流
def rate_limit(requests_per_minute: int = 100, 
               requests_per_hour: int = 1000,
               key_func=None):
    """限流装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # 获取限流key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # 默认使用IP或用户ID
                key = kwargs.get('user_id') or kwargs.get('ip_address') or 'anonymous'
            
            # 检查限流
            config = RateLimitConfig(
                requests_per_minute=requests_per_minute,
                requests_per_hour=requests_per_hour
            )
            result = rate_limiter.check_rate_limit(key, config=config)
            
            if not result['allowed']:
                return {
                    'error': 'Rate limit exceeded',
                    'retry_after': result.get('retry_after', 60),
                    'limit': result.get('limit', 0),
                    'remaining': 0
                }, 429
            
            # 执行函数
            return f(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == '__main__':
    # 测试
    limiter = RateLimiter()
    
    # 测试限流
    key = "test_user_123"
    
    print("测试限流:")
    for i in range(15):
        result = limiter.check_rate_limit(key)
        status = "✓" if result['allowed'] else "✗"
        print(f"  请求 {i+1}: {status} 剩余: {result.get('remaining', 0)}")
        time.sleep(0.05)
    
    # 测试配额
    print("\n测试配额:")
    for i in range(5):
        result = limiter.check_quota(key, "api_calls", amount=10, limit=50)
        status = "✓" if result['allowed'] else "✗"
        print(f"  配额检查 {i+1}: {status} 当前: {result['current']}/{result['limit']}")
    
    # 统计
    print("\n统计:")
    stats = limiter.get_statistics(key)
    print(f"  {stats}")
