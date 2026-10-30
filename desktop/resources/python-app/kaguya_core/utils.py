#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数集合

集中管理所有模块共享的工具函数，避免代码重复
"""

import re
import uuid
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import json


def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID
    
    Args:
        prefix: ID前缀
        
    Returns:
        唯一标识符
    """
    unique_id = uuid.uuid4().hex[:16]
    return f"{prefix}{unique_id}" if prefix else unique_id


def generate_secure_token(length: int = 32) -> str:
    """生成安全随机令牌"""
    return secrets.token_urlsafe(length)


def timestamp_now() -> str:
    """获取当前ISO格式时间戳"""
    return datetime.utcnow().isoformat()


def timestamp_to_datetime(ts: str) -> datetime:
    """将ISO时间戳转换为datetime对象"""
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    清理字符串输入
    
    - 去除首尾空白
    - 限制长度
    - 去除控制字符
    """
    if not text:
        return ""
    
    # 去除控制字符
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    
    # 去除首尾空白
    text = text.strip()
    
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_uuid(value: str) -> bool:
    """验证UUID格式"""
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return re.match(pattern, value, re.IGNORECASE) is not None


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """哈希字符串"""
    if algorithm == "sha256":
        return hashlib.sha256(text.encode()).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    elif algorithm == "sha1":
        return hashlib.sha1(text.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典
    
    Args:
        base: 基础字典
        update: 更新字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_bytes(size: int) -> str:
    """格式化字节大小为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def format_duration(seconds: float) -> str:
    """格式化持续时间为人类可读格式"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def safe_json_loads(text: str, default: Any = None) -> Any:
    """安全地解析JSON"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """安全地将数据转为JSON字符串"""
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """将列表分块"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_list(lst: List[Any]) -> List[Any]:
    """列表去重（保持顺序）"""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def mask_sensitive_data(data: str, mask_char: str = "*") -> str:
    """掩码敏感数据"""
    if len(data) <= 4:
        return mask_char * len(data)
    
    visible = max(2, len(data) // 4)
    return data[:visible] + mask_char * (len(data) - visible * 2) + data[-visible:]


def calculate_similarity(str1: str, str2: str) -> float:
    """
    计算两个字符串的相似度（Levenshtein距离）
    
    Returns:
        相似度分数 (0-1)
    """
    if str1 == str2:
        return 1.0
    
    if len(str1) < len(str2):
        str1, str2 = str2, str1
    
    if len(str2) == 0:
        return 0.0
    
    # Levenshtein距离
    previous_row = list(range(len(str2) + 1))
    
    for i, c1 in enumerate(str1):
        current_row = [i + 1]
        
        for j, c2 in enumerate(str2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        
        previous_row = current_row
    
    distance = previous_row[-1]
    max_len = max(len(str1), len(str2))
    
    return 1 - (distance / max_len)


class RateLimiter:
    """简单的内存速率限制器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # 清理旧请求
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
        else:
            self.requests[key] = []
        
        # 检查限制
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        # 记录请求
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        if not self.is_allowed(key):
            return 0
        
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        if key in self.requests:
            recent_requests = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
            return max(0, self.max_requests - len(recent_requests))
        
        return self.max_requests
