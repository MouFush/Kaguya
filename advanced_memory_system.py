#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级长期记忆系统
参考: MemGPT, LangChain Memory, AutoGPT Memory
特性: 分层存储、知识蒸馏、混合检索、记忆整合
"""

import os
import json
import sqlite3
import numpy as np
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import threading
from functools import lru_cache

# 记忆存储目录
MEMORY_DIR = os.path.join(os.path.dirname(__file__), 'memory_store')
os.makedirs(MEMORY_DIR, exist_ok=True)

class MemoryTier(Enum):
    """记忆层级"""
    WORKING = "working"      # 工作记忆: 当前对话上下文
    SHORT_TERM = "short_term" # 短期记忆: 近期对话历史
    LONG_TERM = "long_term"  # 长期记忆: 重要信息持久化
    EPISODIC = "episodic"    # 情景记忆: 具体事件和经历
    SEMANTIC = "semantic"    # 语义记忆: 知识和概念
    PROCEDURAL = "procedural" # 程序记忆: 技能和流程

class MemoryType(Enum):
    """记忆类型"""
    CONVERSATION = "conversation"  # 对话记录
    FACT = "fact"                  # 事实信息
    PREFERENCE = "preference"      # 用户偏好
    EVENT = "event"                # 事件记录
    SKILL = "skill"                # 技能/流程
    ENTITY = "entity"              # 实体信息
    SUMMARY = "summary"            # 摘要总结
    REFLECTION = "reflection"      # 反思洞察

@dataclass
class Memory:
    """记忆单元"""
    id: str
    content: str
    memory_type: MemoryType
    tier: MemoryTier
    importance: float  # 0-1
    created_at: float
    last_accessed: float
    access_count: int
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)
    relations: List[str] = field(default_factory=list)  # 关联的记忆ID
    source: Optional[str] = None  # 来源对话ID
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type.value,
            'tier': self.tier.value,
            'importance': self.importance,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
            'embedding': self.embedding,
            'metadata': self.metadata,
            'relations': self.relations,
            'source': self.source
        }
    
    @property
    def age_days(self) -> float:
        """记忆年龄（天）"""
        return (time.time() - self.created_at) / 86400
    
    @property
    def recency_score(self) -> float:
        """新鲜度分数"""
        days_since_access = (time.time() - self.last_accessed) / 86400
        return np.exp(-days_since_access / 7)  # 7天衰减
    
    @property
    def relevance_score(self) -> float:
        """相关性分数（综合重要性、访问频率、新鲜度）"""
        importance_weight = 0.4
        recency_weight = 0.3
        frequency_weight = 0.3
        
        # 访问频率归一化（假设最大访问100次）
        frequency_score = min(self.access_count / 100, 1.0)
        
        return (
            self.importance * importance_weight +
            self.recency_score * recency_weight +
            frequency_score * frequency_weight
        )

class MemoryDistiller:
    """记忆蒸馏器 - 压缩和提取关键信息"""
    
    def __init__(self, llm_func=None):
        self.llm = llm_func
        
    def distill_conversation(self, messages: List[Dict], 
                            strategy: str = "summary") -> List[Memory]:
        """
        蒸馏对话内容
        
        Args:
            messages: 对话消息列表
            strategy: 蒸馏策略 (summary/extract/merge)
        
        Returns:
            蒸馏后的记忆列表
        """
        if not self.llm:
            # 降级方案：使用简单提取
            return self._simple_distill(messages)
        
        # 构建提示词
        conversation_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        prompt = f"""请分析以下对话，提取关键信息：

对话内容：
{conversation_text}

请提取：
1. 重要事实（用户提到的具体信息）
2. 用户偏好（喜好、习惯、要求）
3. 关键决策或结论
4. 待办事项或承诺

以JSON格式返回：
{{
    "facts": ["事实1", "事实2"],
    "preferences": ["偏好1", "偏好2"],
    "conclusions": ["结论1"],
    "action_items": ["待办1"]
}}"""
        
        try:
            response = self.llm(prompt)
            # 解析JSON响应
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                memories = []
                
                # 转换为记忆对象
                for fact in data.get('facts', []):
                    memories.append(self._create_memory(
                        fact, MemoryType.FACT, 0.8
                    ))
                
                for pref in data.get('preferences', []):
                    memories.append(self._create_memory(
                        pref, MemoryType.PREFERENCE, 0.9
                    ))
                
                for conclusion in data.get('conclusions', []):
                    memories.append(self._create_memory(
                        conclusion, MemoryType.SUMMARY, 0.85
                    ))
                
                for action in data.get('action_items', []):
                    memories.append(self._create_memory(
                        action, MemoryType.EVENT, 0.75
                    ))
                
                return memories
        except Exception as e:
            print(f"蒸馏失败: {e}")
        
        return self._simple_distill(messages)
    
    def _simple_distill(self, messages: List[Dict]) -> List[Memory]:
        """简单蒸馏（降级方案）"""
        memories = []
        
        # 提取关键句子（包含特定关键词）
        key_patterns = [
            r'我喜欢(.+)', r'我讨厌(.+)', r'我希望(.+)',
            r'请记住(.+)', r'重要的是(.+)', r'我的(.+)是(.+)',
            r'我是(.+)', r'我有(.+)',
        ]
        
        for msg in messages:
            content = msg.get('content', '')
            role = msg.get('role', '')
            
            if role == 'user':
                for pattern in key_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if isinstance(match, tuple):
                            match = ' '.join(match)
                        memories.append(self._create_memory(
                            match.strip(), MemoryType.FACT, 0.7
                        ))
        
        return memories
    
    def _create_memory(self, content: str, mem_type: MemoryType, 
                      importance: float) -> Memory:
        """创建记忆对象"""
        return Memory(
            id=f"mem_{hashlib.md5(content.encode()).hexdigest()[:12]}",
            content=content,
            memory_type=mem_type,
            tier=MemoryTier.LONG_TERM,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0
        )
    
    def compress_memories(self, memories: List[Memory], 
                         target_count: int = 10) -> List[Memory]:
        """
        压缩记忆列表，合并相似内容
        
        Args:
            memories: 记忆列表
            target_count: 目标记忆数量
        
        Returns:
            压缩后的记忆列表
        """
        if len(memories) <= target_count:
            return memories
        
        # 按重要性排序
        memories = sorted(memories, key=lambda m: m.relevance_score, reverse=True)
        
        # 去重：合并相似内容
        compressed = []
        for mem in memories:
            is_duplicate = False
            for existing in compressed:
                if self._is_similar(mem.content, existing.content):
                    # 合并到现有记忆
                    existing.importance = max(existing.importance, mem.importance)
                    existing.access_count += mem.access_count
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                compressed.append(mem)
            
            if len(compressed) >= target_count:
                break
        
        return compressed
    
    def _is_similar(self, text1: str, text2: str, threshold: float = 0.8) -> bool:
        """判断两段文本是否相似"""
        # 简单的Jaccard相似度
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 or not set2:
            return False
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return (intersection / union) > threshold

class HybridRetriever:
    """混合检索器 - 结合多种检索策略"""
    
    def __init__(self):
        self.keyword_index = defaultdict(set)  # 关键词索引
        self.time_index = defaultdict(set)     # 时间索引
        self.embedding_cache = {}              # 嵌入缓存
    
    def index_memory(self, memory: Memory):
        """为记忆建立索引"""
        # 关键词索引
        words = self._extract_keywords(memory.content)
        for word in words:
            self.keyword_index[word].add(memory.id)
        
        # 时间索引（按天）
        day_key = datetime.fromtimestamp(memory.created_at).strftime('%Y-%m-%d')
        self.time_index[day_key].add(memory.id)
    
    def retrieve(self, query: str, memories: List[Memory], 
                top_k: int = 5,
                use_semantic: bool = True,
                use_keyword: bool = True,
                use_temporal: bool = True) -> List[Tuple[Memory, float]]:
        """
        混合检索
        
        Args:
            query: 查询文本
            memories: 记忆库
            top_k: 返回数量
            use_semantic: 使用语义检索
            use_keyword: 使用关键词检索
            use_temporal: 使用时间衰减
        
        Returns:
            (记忆, 分数) 列表
        """
        scores = defaultdict(float)
        
        # 1. 语义相似度
        if use_semantic:
            semantic_scores = self._semantic_search(query, memories)
            for mem_id, score in semantic_scores.items():
                scores[mem_id] += score * 0.5  # 权重50%
        
        # 2. 关键词匹配
        if use_keyword:
            keyword_scores = self._keyword_search(query, memories)
            for mem_id, score in keyword_scores.items():
                scores[mem_id] += score * 0.3  # 权重30%
        
        # 3. 时间衰减（新鲜度）
        if use_temporal:
            for mem in memories:
                scores[mem.id] += mem.recency_score * 0.2  # 权重20%
        
        # 排序并返回top_k
        memory_map = {m.id: m for m in memories}
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [(memory_map[mid], score) for mid, score in sorted_results 
                if mid in memory_map]
    
    def _semantic_search(self, query: str, 
                        memories: List[Memory]) -> Dict[str, float]:
        """语义检索（使用嵌入向量）"""
        scores = {}
        
        # 获取查询的嵌入向量（简化版，实际应该调用嵌入模型）
        query_embedding = self._get_embedding(query)
        
        for memory in memories:
            if memory.embedding:
                # 计算余弦相似度
                similarity = self._cosine_similarity(
                    query_embedding, memory.embedding
                )
                scores[memory.id] = max(0, similarity)
        
        return scores
    
    def _keyword_search(self, query: str, 
                       memories: List[Memory]) -> Dict[str, float]:
        """关键词检索"""
        scores = {}
        query_words = set(self._extract_keywords(query))
        
        memory_map = {m.id: m for m in memories}
        
        for word in query_words:
            for mem_id in self.keyword_index.get(word, set()):
                if mem_id in memory_map:
                    scores[mem_id] = scores.get(mem_id, 0) + 1
        
        # 归一化
        for mem_id in scores:
            mem_content = memory_map[mem_id].content
            mem_words = set(self._extract_keywords(mem_content))
            if mem_words:
                scores[mem_id] /= len(mem_words)
        
        return scores
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（去除停用词）
        stop_words = {'的', '了', '是', '我', '你', '在', '和', '就', '都', '要', 
                     '会', '能', '很', '也', '这', '那', '有', '个', '之', '与'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入（简化版）"""
        # 实际应该调用嵌入模型
        # 这里使用简单的词袋模型作为降级方案
        embedding = [0.0] * 128
        for char in text.lower():
            idx = ord(char) % 128
            embedding[idx] += 1.0
        
        # 归一化
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)

class AdvancedMemoryManager:
    """高级记忆管理器"""
    
    def __init__(self, llm_func=None):
        self.db_path = os.path.join(MEMORY_DIR, 'memory.db')
        self._init_database()
        
        self.distiller = MemoryDistiller(llm_func)
        self.retriever = HybridRetriever()
        
        # 工作记忆（当前对话上下文）
        self.working_memory: List[Memory] = []
        
        # 缓存
        self._cache = {}
        self._lock = threading.RLock()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tier TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                embedding TEXT,
                metadata TEXT,
                relations TEXT,
                source TEXT
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tier ON memories(tier)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)')
        
        conn.commit()
        conn.close()
    
    def add_to_working_memory(self, content: str, role: str = "user"):
        """添加到工作记忆"""
        mem = Memory(
            id=f"wm_{int(time.time() * 1000)}",
            content=f"{role}: {content}",
            memory_type=MemoryType.CONVERSATION,
            tier=MemoryTier.WORKING,
            importance=0.5,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=1
        )
        
        self.working_memory.append(mem)
        
        # 限制工作记忆大小（最近20条）
        if len(self.working_memory) > 20:
            # 将旧的蒸馏到长期记忆
            old_memories = self.working_memory[:-20]
            self.working_memory = self.working_memory[-20:]
            
            # 异步蒸馏
            threading.Thread(
                target=self._distill_and_store,
                args=(old_memories,),
                daemon=True
            ).start()
    
    def _distill_and_store(self, messages: List[Memory]):
        """蒸馏并存储到长期记忆"""
        # 转换为消息格式
        msg_list = [{'role': 'user', 'content': m.content} for m in messages]
        
        # 蒸馏
        distilled = self.distiller.distill_conversation(msg_list)
        
        # 存储
        for mem in distilled:
            self.store_memory(mem)
    
    def store_memory(self, memory: Memory):
        """存储记忆到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO memories 
            (id, content, memory_type, tier, importance, created_at, 
             last_accessed, access_count, embedding, metadata, relations, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.content,
            memory.memory_type.value,
            memory.tier.value,
            memory.importance,
            memory.created_at,
            memory.last_accessed,
            memory.access_count,
            json.dumps(memory.embedding) if memory.embedding else None,
            json.dumps(memory.metadata),
            json.dumps(memory.relations),
            memory.source
        ))
        
        conn.commit()
        conn.close()
        
        # 建立索引
        self.retriever.index_memory(memory)
    
    def retrieve_relevant(self, query: str, 
                         top_k: int = 5,
                         tiers: List[MemoryTier] = None) -> List[Memory]:
        """检索相关记忆"""
        if tiers is None:
            tiers = [MemoryTier.WORKING, MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM]
        
        # 1. 从工作记忆检索
        working_results = []
        if MemoryTier.WORKING in tiers:
            working_results = [
                (m, self._simple_similarity(query, m.content))
                for m in self.working_memory
            ]
            working_results = [(m, s) for m, s in working_results if s > 0.3]
        
        # 2. 从数据库存储的记忆检索
        stored_memories = self._load_memories_from_db(tiers)
        stored_results = self.retriever.retrieve(
            query, stored_memories, top_k=top_k
        )
        
        # 3. 合并结果
        all_results = working_results + stored_results
        all_results.sort(key=lambda x: x[1], reverse=True)
        
        # 更新访问统计
        for mem, _ in all_results[:top_k]:
            self._update_access_stats(mem)
        
        return [mem for mem, _ in all_results[:top_k]]
    
    def _load_memories_from_db(self, 
                              tiers: List[MemoryTier]) -> List[Memory]:
        """从数据库加载记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tier_values = [t.value for t in tiers if t != MemoryTier.WORKING]
        
        if not tier_values:
            return []
        
        placeholders = ','.join(['?' for _ in tier_values])
        cursor.execute(f'''
            SELECT * FROM memories 
            WHERE tier IN ({placeholders})
            ORDER BY importance DESC, last_accessed DESC
            LIMIT 1000
        ''', tier_values)
        
        rows = cursor.fetchall()
        conn.close()
        
        memories = []
        for row in rows:
            memories.append(Memory(
                id=row[0],
                content=row[1],
                memory_type=MemoryType(row[2]),
                tier=MemoryTier(row[3]),
                importance=row[4],
                created_at=row[5],
                last_accessed=row[6],
                access_count=row[7],
                embedding=json.loads(row[8]) if row[8] else None,
                metadata=json.loads(row[9]) if row[9] else {},
                relations=json.loads(row[10]) if row[10] else [],
                source=row[11]
            ))
        
        return memories
    
    def _update_access_stats(self, memory: Memory):
        """更新访问统计"""
        memory.last_accessed = time.time()
        memory.access_count += 1
        
        # 异步更新数据库
        threading.Thread(
            target=self._update_db_access,
            args=(memory.id, memory.last_accessed, memory.access_count),
            daemon=True
        ).start()
    
    def _update_db_access(self, mem_id: str, last_accessed: float, 
                         access_count: int):
        """更新数据库访问统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE memories 
                SET last_accessed = ?, access_count = ?
                WHERE id = ?
            ''', (last_accessed, access_count, mem_id))
            conn.commit()
            conn.close()
        except:
            pass
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单相似度计算"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def consolidate_memories(self):
        """
        整合记忆：压缩、去重、更新关系
        定期运行以优化记忆库
        """
        # 加载所有长期记忆
        long_term = self._load_memories_from_db([MemoryTier.LONG_TERM])
        
        # 压缩
        compressed = self.distiller.compress_memories(long_term, target_count=500)
        
        # 删除被压缩的记忆，保留压缩后的
        # 这里简化处理，实际应该更谨慎
        
        print(f"记忆整合完成: {len(long_term)} -> {len(compressed)}")
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 各层级数量
        for tier in MemoryTier:
            cursor.execute('SELECT COUNT(*) FROM memories WHERE tier = ?', 
                         (tier.value,))
            stats[f'{tier.value}_count'] = cursor.fetchone()[0]
        
        # 各类型数量
        for mem_type in MemoryType:
            cursor.execute('SELECT COUNT(*) FROM memories WHERE memory_type = ?', 
                         (mem_type.value,))
            stats[f'{mem_type.value}_count'] = cursor.fetchone()[0]
        
        # 总数量
        cursor.execute('SELECT COUNT(*) FROM memories')
        stats['total_count'] = cursor.fetchone()[0]
        
        # 平均重要性
        cursor.execute('SELECT AVG(importance) FROM memories')
        stats['avg_importance'] = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 工作记忆
        stats['working_memory_count'] = len(self.working_memory)
        
        return stats

# 全局实例
memory_manager = AdvancedMemoryManager()

if __name__ == '__main__':
    # 测试
    manager = AdvancedMemoryManager()
    
    # 添加工作记忆
    manager.add_to_working_memory("我喜欢Python编程", "user")
    manager.add_to_working_memory("请帮我写一个排序算法", "user")
    manager.add_to_working_memory("好的，这是快速排序的实现", "assistant")
    
    # 检索
    results = manager.retrieve_relevant("Python编程")
    print("检索结果:")
    for mem in results:
        print(f"  - {mem.content[:50]}... (分数: {mem.relevance_score:.3f})")
    
    # 统计
    stats = manager.get_memory_stats()
    print(f"\n记忆统计: {stats}")
