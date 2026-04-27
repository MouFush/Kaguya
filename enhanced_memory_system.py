#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 增强版记忆系统
支持公网访问设备的本地缓存、记忆模式开关、记忆管理
"""

import os
import json
import uuid
import hashlib
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeviceMemoryConfig:
    """设备记忆配置"""
    device_id: str
    memory_mode_enabled: bool = False
    local_cache_enabled: bool = True
    auto_distill: bool = True
    max_local_memories: int = 1000
    retention_days: int = 30
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LocalMemoryEntry:
    """本地记忆条目"""
    id: str
    device_id: str
    content: str
    memory_type: str  # 'fact', 'preference', 'conversation', 'distilled'
    source_conversation_id: Optional[str] = None
    confidence: float = 1.0
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistilledMemory:
    """蒸馏后的记忆"""
    id: str
    device_id: str
    original_content: str
    distilled_content: str
    key_facts: List[str] = field(default_factory=list)
    user_preferences: List[str] = field(default_factory=list)
    conclusions: List[str] = field(default_factory=list)
    source_memories: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    importance_score: float = 0.5


class DeviceMemoryManager:
    """
    设备记忆管理器
    管理每个公网设备的本地记忆缓存
    """
    
    def __init__(self, base_dir: str = "./device_memories"):
        self.base_dir = base_dir
        self.configs: Dict[str, DeviceMemoryConfig] = {}
        self.memories: Dict[str, List[LocalMemoryEntry]] = defaultdict(list)
        self.distilled_memories: Dict[str, List[DistilledMemory]] = defaultdict(list)
        self.lock = threading.RLock()
        
        # 确保目录存在
        os.makedirs(base_dir, exist_ok=True)
        
        # 加载现有配置
        self._load_all_configs()
        
        logger.info(f"设备记忆管理器初始化完成，基础目录: {base_dir}")
    
    def _get_device_dir(self, device_id: str) -> str:
        """获取设备专属目录"""
        # 使用设备ID的哈希作为目录名，避免特殊字符
        device_hash = hashlib.md5(device_id.encode()).hexdigest()[:12]
        return os.path.join(self.base_dir, device_hash)
    
    def _load_all_configs(self):
        """加载所有设备配置"""
        try:
            for device_dir in os.listdir(self.base_dir):
                config_path = os.path.join(self.base_dir, device_dir, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = DeviceMemoryConfig(**data)
                        self.configs[config.device_id] = config
                        
                        # 加载该设备的记忆
                        self._load_device_memories(config.device_id)
        except Exception as e:
            logger.error(f"加载设备配置失败: {e}")
    
    def _load_device_memories(self, device_id: str):
        """加载指定设备的记忆"""
        device_dir = self._get_device_dir(device_id)
        
        # 加载普通记忆
        memories_path = os.path.join(device_dir, "memories.json")
        if os.path.exists(memories_path):
            try:
                with open(memories_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories[device_id] = [LocalMemoryEntry(**item) for item in data]
            except Exception as e:
                logger.error(f"加载设备 {device_id} 的记忆失败: {e}")
        
        # 加载蒸馏记忆
        distilled_path = os.path.join(device_dir, "distilled_memories.json")
        if os.path.exists(distilled_path):
            try:
                with open(distilled_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.distilled_memories[device_id] = [DistilledMemory(**item) for item in data]
            except Exception as e:
                logger.error(f"加载设备 {device_id} 的蒸馏记忆失败: {e}")
    
    def _save_device_config(self, device_id: str):
        """保存设备配置"""
        device_dir = self._get_device_dir(device_id)
        os.makedirs(device_dir, exist_ok=True)
        
        config_path = os.path.join(device_dir, "config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.configs[device_id]), f, ensure_ascii=False, default=str)
    
    def _save_device_memories(self, device_id: str):
        """保存设备记忆"""
        device_dir = self._get_device_dir(device_id)
        os.makedirs(device_dir, exist_ok=True)
        
        # 保存普通记忆
        memories_path = os.path.join(device_dir, "memories.json")
        with open(memories_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(m) for m in self.memories[device_id]], f, ensure_ascii=False, default=str)
        
        # 保存蒸馏记忆
        distilled_path = os.path.join(device_dir, "distilled_memories.json")
        with open(distilled_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(m) for m in self.distilled_memories[device_id]], f, ensure_ascii=False, default=str)
    
    def register_device(self, device_id: str, enable_memory: bool = False) -> DeviceMemoryConfig:
        """
        注册新设备
        
        Args:
            device_id: 设备唯一标识（可以是IP+UserAgent的哈希，或自定义ID）
            enable_memory: 是否默认开启记忆模式
        
        Returns:
            设备记忆配置
        """
        with self.lock:
            if device_id in self.configs:
                # 更新最后访问时间
                self.configs[device_id].last_accessed = datetime.now()
                return self.configs[device_id]
            
            # 创建新配置
            config = DeviceMemoryConfig(
                device_id=device_id,
                memory_mode_enabled=enable_memory
            )
            self.configs[device_id] = config
            self._save_device_config(device_id)
            
            logger.info(f"新设备注册: {device_id}, 记忆模式: {enable_memory}")
            return config
    
    def toggle_memory_mode(self, device_id: str, enabled: bool) -> bool:
        """
        切换记忆模式
        
        Args:
            device_id: 设备ID
            enabled: 是否开启
        
        Returns:
            是否成功
        """
        with self.lock:
            if device_id not in self.configs:
                self.register_device(device_id, enabled)
                return True
            
            self.configs[device_id].memory_mode_enabled = enabled
            self.configs[device_id].last_accessed = datetime.now()
            self._save_device_config(device_id)
            
            logger.info(f"设备 {device_id} 记忆模式已{'开启' if enabled else '关闭'}")
            return True
    
    def is_memory_mode_enabled(self, device_id: str) -> bool:
        """检查设备是否开启记忆模式"""
        with self.lock:
            if device_id not in self.configs:
                return False
            return self.configs[device_id].memory_mode_enabled
    
    def add_memory(self, device_id: str, content: str, memory_type: str = "fact",
                   source_conversation_id: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> Optional[LocalMemoryEntry]:
        """
        添加记忆
        
        Args:
            device_id: 设备ID
            content: 记忆内容
            memory_type: 记忆类型
            source_conversation_id: 来源对话ID
            metadata: 元数据
        
        Returns:
            添加的记忆条目，如果记忆模式未开启则返回None
        """
        with self.lock:
            if not self.is_memory_mode_enabled(device_id):
                return None
            
            # 检查记忆数量限制
            config = self.configs[device_id]
            if len(self.memories[device_id]) >= config.max_local_memories:
                # 删除最旧的记忆
                self.memories[device_id].sort(key=lambda x: x.last_accessed)
                removed = self.memories[device_id].pop(0)
                logger.info(f"设备 {device_id} 记忆数量超限，删除最旧记忆: {removed.id}")
            
            # 创建新记忆
            memory = LocalMemoryEntry(
                id=str(uuid.uuid4()),
                device_id=device_id,
                content=content,
                memory_type=memory_type,
                source_conversation_id=source_conversation_id,
                metadata=metadata or {}
            )
            
            # 设置过期时间
            if config.retention_days > 0:
                memory.expires_at = datetime.now() + timedelta(days=config.retention_days)
            
            self.memories[device_id].append(memory)
            self._save_device_memories(device_id)
            
            logger.info(f"设备 {device_id} 添加记忆: {content[:50]}...")
            return memory
    
    def get_memories(self, device_id: str, memory_type: Optional[str] = None,
                     limit: int = 100) -> List[LocalMemoryEntry]:
        """
        获取设备记忆
        
        Args:
            device_id: 设备ID
            memory_type: 记忆类型筛选
            limit: 返回数量限制
        
        Returns:
            记忆列表
        """
        with self.lock:
            if device_id not in self.memories:
                return []
            
            memories = self.memories[device_id]
            
            # 过滤过期记忆
            now = datetime.now()
            memories = [m for m in memories if m.expires_at is None or m.expires_at > now]
            
            # 类型筛选
            if memory_type:
                memories = [m for m in memories if m.memory_type == memory_type]
            
            # 按最后访问时间排序
            memories.sort(key=lambda x: x.last_accessed, reverse=True)
            
            return memories[:limit]
    
    def add_distilled_memory(self, device_id: str, original_content: str,
                            distilled_content: str, key_facts: List[str],
                            user_preferences: List[str], conclusions: List[str],
                            source_memories: List[str]) -> Optional[DistilledMemory]:
        """
        添加蒸馏记忆
        
        Args:
            device_id: 设备ID
            original_content: 原始内容
            distilled_content: 蒸馏后内容
            key_facts: 关键事实
            user_preferences: 用户偏好
            conclusions: 结论
            source_memories: 来源记忆ID列表
        
        Returns:
            蒸馏记忆对象
        """
        with self.lock:
            if not self.is_memory_mode_enabled(device_id):
                return None
            
            distilled = DistilledMemory(
                id=str(uuid.uuid4()),
                device_id=device_id,
                original_content=original_content,
                distilled_content=distilled_content,
                key_facts=key_facts,
                user_preferences=user_preferences,
                conclusions=conclusions,
                source_memories=source_memories
            )
            
            self.distilled_memories[device_id].append(distilled)
            self._save_device_memories(device_id)
            
            logger.info(f"设备 {device_id} 添加蒸馏记忆: {distilled_content[:50]}...")
            return distilled
    
    def get_distilled_memories(self, device_id: str, limit: int = 50) -> List[DistilledMemory]:
        """获取设备的蒸馏记忆"""
        with self.lock:
            if device_id not in self.distilled_memories:
                return []
            
            memories = self.distilled_memories[device_id]
            memories.sort(key=lambda x: x.importance_score, reverse=True)
            return memories[:limit]
    
    def delete_memory(self, device_id: str, memory_id: str) -> bool:
        """
        删除单条记忆
        
        Args:
            device_id: 设备ID
            memory_id: 记忆ID
        
        Returns:
            是否成功
        """
        with self.lock:
            if device_id not in self.memories:
                return False
            
            original_count = len(self.memories[device_id])
            self.memories[device_id] = [m for m in self.memories[device_id] if m.id != memory_id]
            
            if len(self.memories[device_id]) < original_count:
                self._save_device_memories(device_id)
                logger.info(f"设备 {device_id} 删除记忆: {memory_id}")
                return True
            
            # 也检查蒸馏记忆
            if device_id in self.distilled_memories:
                original_count = len(self.distilled_memories[device_id])
                self.distilled_memories[device_id] = [m for m in self.distilled_memories[device_id] if m.id != memory_id]
                if len(self.distilled_memories[device_id]) < original_count:
                    self._save_device_memories(device_id)
                    logger.info(f"设备 {device_id} 删除蒸馏记忆: {memory_id}")
                    return True
            
            return False
    
    def clear_all_memories(self, device_id: str, include_distilled: bool = True) -> int:
        """
        清空设备所有记忆
        
        Args:
            device_id: 设备ID
            include_distilled: 是否包括蒸馏记忆
        
        Returns:
            删除的记忆数量
        """
        with self.lock:
            count = 0
            
            # 删除普通记忆
            if device_id in self.memories:
                count += len(self.memories[device_id])
                self.memories[device_id] = []
            
            # 删除蒸馏记忆
            if include_distilled and device_id in self.distilled_memories:
                count += len(self.distilled_memories[device_id])
                self.distilled_memories[device_id] = []
            
            self._save_device_memories(device_id)
            
            logger.info(f"设备 {device_id} 清空记忆，共删除 {count} 条")
            return count
    
    def delete_device_cache(self, device_id: str) -> bool:
        """
        完全删除设备缓存（包括配置和所有记忆）
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否成功
        """
        with self.lock:
            device_dir = self._get_device_dir(device_id)
            
            if os.path.exists(device_dir):
                try:
                    shutil.rmtree(device_dir)
                    logger.info(f"设备 {device_id} 缓存目录已删除")
                except Exception as e:
                    logger.error(f"删除设备 {device_id} 缓存失败: {e}")
                    return False
            
            # 从内存中移除
            if device_id in self.configs:
                del self.configs[device_id]
            if device_id in self.memories:
                del self.memories[device_id]
            if device_id in self.distilled_memories:
                del self.distilled_memories[device_id]
            
            logger.info(f"设备 {device_id} 所有数据已删除")
            return True
    
    def get_memory_stats(self, device_id: str) -> Dict[str, Any]:
        """
        获取设备记忆统计
        
        Args:
            device_id: 设备ID
        
        Returns:
            统计信息
        """
        with self.lock:
            stats = {
                "device_id": device_id,
                "memory_mode_enabled": False,
                "local_cache_enabled": False,
                "total_memories": 0,
                "distilled_memories": 0,
                "memory_types": {},
                "cache_size_mb": 0
            }
            
            if device_id in self.configs:
                config = self.configs[device_id]
                stats["memory_mode_enabled"] = config.memory_mode_enabled
                stats["local_cache_enabled"] = config.local_cache_enabled
                stats["auto_distill"] = config.auto_distill
                stats["max_local_memories"] = config.max_local_memories
                stats["retention_days"] = config.retention_days
                stats["created_at"] = config.created_at.isoformat()
                stats["last_accessed"] = config.last_accessed.isoformat()
            
            if device_id in self.memories:
                memories = self.memories[device_id]
                stats["total_memories"] = len(memories)
                
                # 统计类型
                type_counts = defaultdict(int)
                for m in memories:
                    type_counts[m.memory_type] += 1
                stats["memory_types"] = dict(type_counts)
            
            if device_id in self.distilled_memories:
                stats["distilled_memories"] = len(self.distilled_memories[device_id])
            
            # 计算缓存大小
            device_dir = self._get_device_dir(device_id)
            if os.path.exists(device_dir):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(device_dir):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                stats["cache_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            return stats
    
    def list_all_devices(self) -> List[Dict[str, Any]]:
        """列出所有注册的设备"""
        with self.lock:
            devices = []
            for device_id in self.configs:
                devices.append(self.get_memory_stats(device_id))
            return devices
    
    def cleanup_expired_memories(self) -> int:
        """
        清理所有过期记忆
        
        Returns:
            清理的记忆数量
        """
        with self.lock:
            total_cleaned = 0
            now = datetime.now()
            
            for device_id in list(self.memories.keys()):
                original_count = len(self.memories[device_id])
                self.memories[device_id] = [
                    m for m in self.memories[device_id]
                    if m.expires_at is None or m.expires_at > now
                ]
                cleaned = original_count - len(self.memories[device_id])
                if cleaned > 0:
                    total_cleaned += cleaned
                    self._save_device_memories(device_id)
                    logger.info(f"设备 {device_id} 清理 {cleaned} 条过期记忆")
            
            return total_cleaned


# ==================== 记忆蒸馏器 ====================

class MemoryDistiller:
    """
    记忆蒸馏器
    将对话内容蒸馏为结构化记忆
    """
    
    def __init__(self):
        self.distillation_prompt = """请从以下对话内容中提取关键信息，以JSON格式返回：

对话内容：
{conversation}

请提取：
1. 关键事实（用户提到的客观信息）
2. 用户偏好（用户的喜好、习惯、倾向）
3. 结论（对话得出的结论或决定）

返回格式：
{{
    "key_facts": ["事实1", "事实2"],
    "user_preferences": ["偏好1", "偏好2"],
    "conclusions": ["结论1", "结论2"],
    "distilled_summary": "简要总结"
}}
"""
    
    async def distill(self, conversation: str, llm_func) -> Dict[str, Any]:
        """
        蒸馏对话内容
        
        Args:
            conversation: 对话内容
            llm_func: LLM调用函数
        
        Returns:
            蒸馏结果
        """
        try:
            prompt = self.distillation_prompt.format(conversation=conversation)
            response = await llm_func(prompt)
            
            # 尝试解析JSON
            import json
            import re
            
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
            return {
                "key_facts": [],
                "user_preferences": [],
                "conclusions": [],
                "distilled_summary": response[:200]
            }
        except Exception as e:
            logger.error(f"记忆蒸馏失败: {e}")
            return {
                "key_facts": [],
                "user_preferences": [],
                "conclusions": [],
                "distilled_summary": conversation[:200]
            }


# ==================== 全局实例 ====================

# 创建设备记忆管理器全局实例
device_memory_manager = DeviceMemoryManager()
memory_distiller = MemoryDistiller()


# ==================== 便捷函数 ====================

def get_or_create_device_id(request) -> str:
    """
    从请求中获取或创建设备ID
    可以使用IP+UserAgent的哈希，或客户端提供的ID
    """
    # 首先检查请求中是否提供了设备ID
    if request.is_json:
        data = request.get_json()
        if 'device_id' in data and data['device_id']:
            return data['device_id']
    
    # 否则使用IP+UserAgent的哈希
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
    user_agent = request.headers.get('User-Agent', '')
    device_str = f"{ip}:{user_agent}"
    return hashlib.md5(device_str.encode()).hexdigest()[:16]


async def process_conversation_for_memory(device_id: str, conversation: str,
                                         conversation_id: str, llm_func) -> bool:
    """
    处理对话并提取记忆
    
    Args:
        device_id: 设备ID
        conversation: 对话内容
        conversation_id: 对话ID
        llm_func: LLM调用函数
    
    Returns:
        是否成功
    """
    # 检查记忆模式是否开启
    if not device_memory_manager.is_memory_mode_enabled(device_id):
        return False
    
    # 添加原始对话记忆
    device_memory_manager.add_memory(
        device_id=device_id,
        content=conversation,
        memory_type="conversation",
        source_conversation_id=conversation_id
    )
    
    # 检查是否自动蒸馏
    config = device_memory_manager.configs.get(device_id)
    if config and config.auto_distill:
        # 蒸馏对话
        distilled = await memory_distiller.distill(conversation, llm_func)
        
        # 添加蒸馏记忆
        device_memory_manager.add_distilled_memory(
            device_id=device_id,
            original_content=conversation,
            distilled_content=distilled.get("distilled_summary", ""),
            key_facts=distilled.get("key_facts", []),
            user_preferences=distilled.get("user_preferences", []),
            conclusions=distilled.get("conclusions", []),
            source_memories=[conversation_id]
        )
    
    return True


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("🧠 辉夜AI - 增强版记忆系统测试")
    print("=" * 60)
    print()
    
    # 创建设备
    device_id = "test_device_001"
    config = device_memory_manager.register_device(device_id, enable_memory=True)
    print(f"✅ 设备注册: {device_id}")
    print(f"   记忆模式: {'开启' if config.memory_mode_enabled else '关闭'}")
    
    # 添加记忆
    memory = device_memory_manager.add_memory(
        device_id=device_id,
        content="用户喜欢Python编程，讨厌Java",
        memory_type="preference"
    )
    print(f"✅ 添加记忆: {memory.id if memory else '失败'}")
    
    # 获取统计
    stats = device_memory_manager.get_memory_stats(device_id)
    print(f"\n📊 设备统计:")
    print(f"   总记忆数: {stats['total_memories']}")
    print(f"   缓存大小: {stats['cache_size_mb']} MB")
    
    # 列出所有设备
    devices = device_memory_manager.list_all_devices()
    print(f"\n📱 注册设备数: {len(devices)}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
