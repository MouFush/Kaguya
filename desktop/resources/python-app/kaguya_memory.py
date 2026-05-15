#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 增强记忆系统
参考 Claude Code 的 memdir + memoryTypes + paths 架构
实现：类型化记忆、自动提取、上下文注入、信任验证、分层存储
"""

import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from datetime import datetime

try:
    import sqlite3
    HAS_SQLITE3 = True
except ImportError:
    HAS_SQLITE3 = False


class MemoryType(Enum):
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class MemoryTier(Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


MEMORY_TYPE_DESCRIPTIONS = {
    MemoryType.USER: "User's role, goals, responsibilities, knowledge. Tailors behavior to the individual.",
    MemoryType.FEEDBACK: "Guidance on approach - corrections AND confirmations. Prevents repeating mistakes.",
    MemoryType.PROJECT: "Ongoing work, goals, initiatives, bugs, incidents not derivable from code/git.",
    MemoryType.REFERENCE: "Pointers to external systems (URLs, project IDs, dashboard links).",
}

DERIVABILITY_EXCLUSIONS = [
    "Code patterns and architecture (derivable from codebase)",
    "Git history and commit messages (derivable from git)",
    "File structure and directory layout (derivable from filesystem)",
    "API signatures and type definitions (derivable from source code)",
    "Standard library documentation (universally available)",
]


@dataclass
class MemoryEntry:
    id: str
    content: str
    memory_type: MemoryType
    tier: MemoryTier
    importance: float = 0.5
    created_at: str = ""
    last_accessed: str = ""
    access_count: int = 0
    source: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at


@dataclass
class MemoryRetrievalResult:
    entries: List[MemoryEntry]
    total_count: int
    query: str
    token_count: int


class JsonMemoryStore:
    def __init__(self, db_path: str = None):
        self._db_path = db_path or os.path.join(
            os.path.expanduser("~"), ".kaguya", "memory", "memory.json"
        )
        self._lock = threading.Lock()
        self._data: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._db_path):
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        with open(self._db_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def store(self, entry: MemoryEntry) -> bool:
        with self._lock:
            self._data[entry.id] = {
                "id": entry.id,
                "content": entry.content,
                "memory_type": entry.memory_type.value,
                "tier": entry.tier.value,
                "importance": entry.importance,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "source": entry.source,
                "tags": entry.tags,
                "metadata": entry.metadata,
            }
            self._save()
            return True

    def retrieve(self, query="", memory_type=None, tier=None, min_importance=0.0, limit=10):
        results = []
        for entry_data in self._data.values():
            if query and query.lower() not in entry_data["content"].lower():
                continue
            if memory_type and entry_data["memory_type"] != memory_type.value:
                continue
            if tier and entry_data["tier"] != tier.value:
                continue
            if entry_data["importance"] < min_importance:
                continue
            results.append(self._data_to_entry(entry_data))

        results.sort(key=lambda e: (e.importance, e.last_accessed), reverse=True)
        return results[:limit]

    def retrieve_by_keywords(self, keywords, limit=10):
        results = []
        for entry_data in self._data.values():
            content_lower = entry_data["content"].lower()
            if any(kw.lower() in content_lower for kw in keywords):
                results.append(self._data_to_entry(entry_data))
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            if memory_id in self._data:
                del self._data[memory_id]
                self._save()
                return True
            return False

    def _update_access(self, memory_id: str):
        if memory_id in self._data:
            self._data[memory_id]["last_accessed"] = datetime.now().isoformat()
            self._data[memory_id]["access_count"] = self._data[memory_id].get("access_count", 0) + 1
            self._save()

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        by_tier = {}
        for d in self._data.values():
            by_type[d["memory_type"]] = by_type.get(d["memory_type"], 0) + 1
            by_tier[d["tier"]] = by_tier.get(d["tier"], 0) + 1
        return {"total": len(self._data), "by_type": by_type, "by_tier": by_tier}

    def _data_to_entry(self, d: Dict) -> MemoryEntry:
        return MemoryEntry(
            id=d["id"],
            content=d["content"],
            memory_type=MemoryType(d["memory_type"]),
            tier=MemoryTier(d["tier"]),
            importance=d.get("importance", 0.5),
            created_at=d.get("created_at", ""),
            last_accessed=d.get("last_accessed", ""),
            access_count=d.get("access_count", 0),
            source=d.get("source", ""),
            tags=d.get("tags", []),
            metadata=d.get("metadata", {}),
        )


class MemoryStore:
    def __init__(self, db_path: str = None):
        if not HAS_SQLITE3:
            self._json_store = JsonMemoryStore(db_path)
            self._use_sqlite = False
            return

        self._use_sqlite = True
        self._json_store = None
        self._db_path = db_path or os.path.join(
            os.path.expanduser("~"), ".kaguya", "memory", "memory.db"
        )
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tier TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                source TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_accessed ON memories(last_accessed DESC)
        """)
        conn.commit()

    def store(self, entry: MemoryEntry) -> bool:
        if not self._use_sqlite:
            return self._json_store.store(entry)
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO memories
                (id, content, memory_type, tier, importance, created_at, last_accessed, access_count, source, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.content,
                entry.memory_type.value,
                entry.tier.value,
                entry.importance,
                entry.created_at,
                entry.last_accessed,
                entry.access_count,
                entry.source,
                json.dumps(entry.tags, ensure_ascii=False),
                json.dumps(entry.metadata, ensure_ascii=False),
            ))
            conn.commit()
            return True
        except Exception:
            return False

    def retrieve(
        self,
        query: str = "",
        memory_type: MemoryType = None,
        tier: MemoryTier = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        if not self._use_sqlite:
            return self._json_store.retrieve(query, memory_type, tier, min_importance, limit)
        conn = self._get_conn()
        conditions = []
        params = []

        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")

        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)

        if tier:
            conditions.append("tier = ?")
            params.append(tier.value)

        if min_importance > 0:
            conditions.append("importance >= ?")
            params.append(min_importance)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

        entries = []
        for row in rows:
            entries.append(self._row_to_entry(row))
            self._update_access(row["id"])

        return entries

    def retrieve_by_keywords(
        self,
        keywords: List[str],
        limit: int = 10,
    ) -> List[MemoryEntry]:
        if not keywords:
            return []
        if not self._use_sqlite:
            return self._json_store.retrieve_by_keywords(keywords, limit)
        conn = self._get_conn()
        conditions = []
        params = []
        for kw in keywords[:10]:
            conditions.append("content LIKE ?")
            params.append(f"%{kw}%")

        where = " OR ".join(conditions)
        sql = f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY importance DESC, last_accessed DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def delete(self, memory_id: str) -> bool:
        if not self._use_sqlite:
            return self._json_store.delete(memory_id)
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return True
        except Exception:
            return False

    def _update_access(self, memory_id: str):
        if not self._use_sqlite:
            self._json_store._update_access(memory_id)
            return
        conn = self._get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?",
            (now, memory_id),
        )
        conn.commit()

    def _row_to_entry(self, row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            memory_type=MemoryType(row["memory_type"]),
            tier=MemoryTier(row["tier"]),
            importance=row["importance"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            source=row["source"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
        )

    def get_stats(self) -> Dict[str, Any]:
        if not self._use_sqlite:
            return self._json_store.get_stats()
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_type = {}
        for row in conn.execute("SELECT memory_type, COUNT(*) as cnt FROM memories GROUP BY memory_type"):
            by_type[row[0]] = row[1]
        by_tier = {}
        for row in conn.execute("SELECT tier, COUNT(*) as cnt FROM memories GROUP BY tier"):
            by_tier[row[0]] = row[1]
        return {"total": total, "by_type": by_type, "by_tier": by_tier}


class WorkingMemory:
    MAX_ENTRIES = 20
    TTL_SECONDS = 3600

    def __init__(self):
        self._entries: OrderedDict[str, MemoryEntry] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, entry: MemoryEntry):
        with self._lock:
            if entry.id in self._entries:
                del self._entries[entry.id]
            self._entries[entry.id] = entry
            while len(self._entries) > self.MAX_ENTRIES:
                self._entries.popitem(last=False)

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            return self._entries.get(memory_id)

    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        results = []
        query_lower = query.lower()
        with self._lock:
            for entry in self._entries.values():
                if query_lower in entry.content.lower():
                    results.append(entry)
                if len(results) >= limit:
                    break
        return results

    def get_all(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._entries.values())

    def clear(self):
        with self._lock:
            self._entries.clear()


class MemoryExtractor:
    def __init__(self, llm_adapter=None):
        self._llm = llm_adapter

    def extract_from_conversation(
        self,
        messages: List[Dict[str, str]],
    ) -> List[MemoryEntry]:
        if self._llm:
            return self._llm_extract(messages)
        return self._regex_extract(messages)

    def _llm_extract(self, messages: List[Dict[str, str]]) -> List[MemoryEntry]:
        conversation_text = ""
        for msg in messages[-20:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            conversation_text += f"[{role}]: {content}\n\n"

        prompt = (
            "Extract key information from this conversation as structured memories.\n"
            "For each memory, provide:\n"
            "1. type: one of 'user', 'feedback', 'project', 'reference'\n"
            "2. content: the memory content (lead with the rule/fact, then Why:, then How to apply:)\n"
            "3. importance: 0.0-1.0\n\n"
            "IMPORTANT: Do NOT save information derivable from code, git, or file structure.\n"
            "Only save non-obvious, surprising, or preference-based information.\n\n"
            f"Conversation:\n{conversation_text}\n\n"
            "Output as JSON array: [{\"type\": \"...\", \"content\": \"...\", \"importance\": 0.8}]"
        )

        try:
            result = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
            )
            if isinstance(result, str):
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group())
                    entries = []
                    for item in items[:10]:
                        try:
                            mem_type = MemoryType(item.get("type", "project"))
                        except ValueError:
                            mem_type = MemoryType.PROJECT

                        content = item.get("content", "")
                        if not content:
                            continue

                        entries.append(MemoryEntry(
                            id=hashlib.sha256(content.encode()).hexdigest()[:16],
                            content=content,
                            memory_type=mem_type,
                            tier=MemoryTier.LONG_TERM,
                            importance=float(item.get("importance", 0.5)),
                            source="auto_extract",
                        ))
                    return entries
        except Exception:
            pass

        return self._regex_extract(messages)

    def _regex_extract(self, messages: List[Dict[str, str]]) -> List[MemoryEntry]:
        entries = []
        preference_patterns = [
            re.compile(r'(?:我喜欢|我偏好|我习惯|I prefer|I like|I always)(.+)', re.IGNORECASE),
            re.compile(r'(?:不要|避免|千万别|never|avoid|don\'t)(.+)', re.IGNORECASE),
            re.compile(r'(?:记住|记得|别忘了|remember|note that|keep in mind)(.+)', re.IGNORECASE),
        ]

        for msg in messages:
            content = msg.get("content", "")
            if msg.get("role") != "user":
                continue

            for pattern in preference_patterns:
                match = pattern.search(content)
                if match:
                    extracted = match.group(1).strip()[:200]
                    if len(extracted) > 10:
                        entries.append(MemoryEntry(
                            id=hashlib.sha256(extracted.encode()).hexdigest()[:16],
                            content=extracted,
                            memory_type=MemoryType.FEEDBACK,
                            tier=MemoryTier.LONG_TERM,
                            importance=0.7,
                            source="regex_extract",
                        ))

        return entries[:5]


class EnhancedMemoryManager:
    def __init__(
        self,
        db_path: str = None,
        llm_adapter=None,
        max_context_tokens: int = 4000,
    ):
        self._store = MemoryStore(db_path)
        self._working = WorkingMemory()
        self._extractor = MemoryExtractor(llm_adapter)
        self._max_context_tokens = max_context_tokens
        self._consolidation_lock = threading.Lock()

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.PROJECT,
        importance: float = 0.5,
        source: str = "explicit",
        tags: List[str] = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            id=hashlib.sha256(f"{content}:{time.time()}".encode()).hexdigest()[:16],
            content=content,
            memory_type=memory_type,
            tier=MemoryTier.SHORT_TERM if importance < 0.6 else MemoryTier.LONG_TERM,
            importance=importance,
            source=source,
            tags=tags or [],
        )

        self._working.add(entry)
        self._store.store(entry)
        return entry

    def recall(
        self,
        query: str,
        limit: int = 5,
        include_working: bool = True,
    ) -> MemoryRetrievalResult:
        all_entries = []

        if include_working:
            working_results = self._working.search(query, limit=limit)
            all_entries.extend(working_results)

        keywords = self._extract_keywords(query)
        if keywords:
            store_results = self._store.retrieve_by_keywords(keywords, limit=limit)
        else:
            store_results = self._store.retrieve(query=query, limit=limit)

        seen_ids = {e.id for e in all_entries}
        for entry in store_results:
            if entry.id not in seen_ids:
                all_entries.append(entry)
                seen_ids.add(entry.id)

        all_entries.sort(key=lambda e: e.importance, reverse=True)
        all_entries = all_entries[:limit]

        token_count = sum(len(e.content) // 4 for e in all_entries)

        return MemoryRetrievalResult(
            entries=all_entries,
            total_count=len(all_entries),
            query=query,
            token_count=token_count,
        )

    def build_context_for_llm(
        self,
        user_message: str,
        max_tokens: int = None,
    ) -> str:
        budget = max_tokens or self._max_context_tokens
        sections = []
        used_tokens = 0

        user_memories = self._store.retrieve(
            memory_type=MemoryType.USER, limit=3, min_importance=0.6
        )
        if user_memories:
            section = "## User Profile\n"
            for m in user_memories:
                entry_text = f"- {m.content}\n"
                if used_tokens + len(entry_text) // 4 > budget:
                    break
                section += entry_text
                used_tokens += len(entry_text) // 4
            sections.append(section)

        feedback_memories = self._store.retrieve(
            memory_type=MemoryType.FEEDBACK, limit=5, min_importance=0.5
        )
        if feedback_memories:
            section = "## Feedback & Preferences\n"
            for m in feedback_memories:
                entry_text = f"- {m.content}\n"
                if used_tokens + len(entry_text) // 4 > budget:
                    break
                section += entry_text
                used_tokens += len(entry_text) // 4
            sections.append(section)

        relevant = self.recall(user_message, limit=5, include_working=True)
        if relevant.entries:
            section = "## Relevant Memories\n"
            for m in relevant.entries:
                entry_text = f"- [{m.memory_type.value}] {m.content}\n"
                if used_tokens + len(entry_text) // 4 > budget:
                    break
                section += entry_text
                used_tokens += len(entry_text) // 4
            sections.append(section)

        if not sections:
            return ""

        return (
            "## Memory Context\n"
            "The following memories are from previous interactions. "
            "Trust what you observe now over recalled memories if they conflict.\n\n"
            + "\n".join(sections)
        )

    def extract_and_store(self, messages: List[Dict[str, str]]) -> List[MemoryEntry]:
        entries = self._extractor.extract_from_conversation(messages)
        for entry in entries:
            self._store.store(entry)
        return entries

    def consolidate(self):
        with self._consolidation_lock:
            all_entries = self._store.retrieve(limit=1000)
            if len(all_entries) < 20:
                return

            merged = 0
            for i in range(len(all_entries)):
                for j in range(i + 1, len(all_entries)):
                    if all_entries[i].memory_type != all_entries[j].memory_type:
                        continue

                    similarity = self._jaccard_similarity(
                        all_entries[i].content, all_entries[j].content
                    )
                    if similarity > 0.8:
                        merged_content = (
                            f"{all_entries[i].content}\n"
                            f"Also: {all_entries[j].content}"
                        )
                        all_entries[i].content = merged_content
                        all_entries[i].importance = max(
                            all_entries[i].importance, all_entries[j].importance
                        )
                        self._store.delete(all_entries[j].id)
                        merged += 1

            short_term = [e for e in all_entries if e.tier == MemoryTier.SHORT_TERM and e.importance >= 0.6]
            for entry in short_term:
                entry.tier = MemoryTier.LONG_TERM
                self._store.store(entry)

    def _jaccard_similarity(self, a: str, b: str) -> float:
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)

    def _extract_keywords(self, text: str) -> List[str]:
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "the", "a", "an",
            "is", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "could", "should",
            "may", "might", "shall", "can", "need", "dare", "ought", "used",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
            "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
            "she", "her", "it", "its", "they", "them", "their", "what", "which",
            "that", "this", "these", "those", "how", "why", "when", "where",
        }

        words = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        return keywords[:10]

    def get_stats(self) -> Dict[str, Any]:
        store_stats = self._store.get_stats()
        working = self._working.get_all()
        return {
            "store": store_stats,
            "working_memory_count": len(working),
            "max_context_tokens": self._max_context_tokens,
        }
