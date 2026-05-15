#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 对话压缩系统
参考 Claude Code 的 compact.ts 架构，实现自动上下文窗口管理与对话摘要
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "TokenUsage"):
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens


@dataclass
class CompactBoundary:
    timestamp: str
    tokens_before: int
    tokens_after: int
    messages_compacted: int
    summary: str


@dataclass
class Message:
    role: str
    content: str
    timestamp: str = ""
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationCompactor:
    DEFAULT_MAX_TOKENS = 128000
    DEFAULT_COMPACT_THRESHOLD = 0.8
    DEFAULT_SUMMARY_MAX_TOKENS = 4000

    def __init__(
        self,
        max_context_tokens: int = DEFAULT_MAX_TOKENS,
        compact_threshold: float = DEFAULT_COMPACT_THRESHOLD,
        summary_max_tokens: int = DEFAULT_SUMMARY_MAX_TOKENS,
        llm_adapter=None,
    ):
        self.max_context_tokens = max_context_tokens
        self.compact_threshold = compact_threshold
        self.summary_max_tokens = summary_max_tokens
        self.llm_adapter = llm_adapter
        self._boundaries: List[CompactBoundary] = []
        self._total_tokens_used = TokenUsage()

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def estimate_messages_tokens(self, messages: List[Message]) -> int:
        total = 0
        for msg in messages:
            if msg.token_count > 0:
                total += msg.token_count
            else:
                total += self.estimate_tokens(msg.content)
            total += 4
        return total

    def should_compact(self, messages: List[Message]) -> bool:
        current_tokens = self.estimate_messages_tokens(messages)
        threshold = int(self.max_context_tokens * self.compact_threshold)
        return current_tokens >= threshold

    def get_token_stats(self, messages: List[Message]) -> Dict[str, Any]:
        current = self.estimate_messages_tokens(messages)
        return {
            "current_tokens": current,
            "max_tokens": self.max_context_tokens,
            "threshold": int(self.max_context_tokens * self.compact_threshold),
            "usage_ratio": current / self.max_context_tokens if self.max_context_tokens > 0 else 0,
            "should_compact": self.should_compact(messages),
            "message_count": len(messages),
        }

    def _build_compact_prompt(self, messages: List[Message]) -> str:
        conversation_text = ""
        for msg in messages:
            role = msg.role.upper()
            content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
            conversation_text += f"[{role}]: {content}\n\n"

        return (
            "Please summarize the following conversation concisely, preserving:\n"
            "1. Key decisions and conclusions reached\n"
            "2. Important code changes or file modifications made\n"
            "3. Any unresolved issues or pending tasks\n"
            "4. User preferences and requirements mentioned\n\n"
            f"Conversation to summarize:\n{conversation_text}\n\n"
            "Provide a structured summary in the following format:\n"
            "## Summary\n[Main topics and outcomes]\n\n"
            "## Key Decisions\n[Important decisions made]\n\n"
            "## Changes Made\n[Files modified, code changes]\n\n"
            "## Pending Items\n[Unresolved issues, next steps]"
        )

    def compact(
        self,
        messages: List[Message],
        keep_recent: int = 4,
    ) -> Tuple[List[Message], Optional[CompactBoundary]]:
        if len(messages) <= keep_recent + 1:
            return messages, None

        tokens_before = self.estimate_messages_tokens(messages)

        messages_to_compact = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        system_messages = [m for m in messages_to_compact if m.role == "system"]
        non_system = [m for m in messages_to_compact if m.role != "system"]

        if not non_system:
            return messages, None

        summary_text = self._generate_summary(non_system)

        if not summary_text:
            summary_text = self._fallback_summary(non_system)

        summary_message = Message(
            role="system",
            content=f"[Conversation Summary - Compacted at {datetime.now().isoformat()}]\n\n{summary_text}",
            timestamp=datetime.now().isoformat(),
            token_count=self.estimate_tokens(summary_text),
            metadata={"type": "compact_summary"},
        )

        compacted = system_messages + [summary_message] + recent_messages

        tokens_after = self.estimate_messages_tokens(compacted)

        boundary = CompactBoundary(
            timestamp=datetime.now().isoformat(),
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            messages_compacted=len(non_system),
            summary=summary_text[:500],
        )
        self._boundaries.append(boundary)

        return compacted, boundary

    def _generate_summary(self, messages: List[Message]) -> Optional[str]:
        if self.llm_adapter is None:
            return None

        prompt = self._build_compact_prompt(messages)

        try:
            if hasattr(self.llm_adapter, "chat"):
                result = self.llm_adapter.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=self.summary_max_tokens,
                )
                return result if isinstance(result, str) else str(result)
            return None
        except Exception:
            return None

    def _fallback_summary(self, messages: List[Message]) -> str:
        topics = set()
        files_mentioned = set()
        decisions = []

        for msg in messages:
            content = msg.content.lower()
            for keyword in ["decided", "decision", "conclusion", "resolved", "agreed"]:
                if keyword in content:
                    idx = content.index(keyword)
                    snippet = msg.content[max(0, idx - 50):idx + 100]
                    decisions.append(snippet)

            import re
            file_patterns = re.findall(r'[\w/\\]+\.\w{1,10}', msg.content)
            files_mentioned.update(file_patterns[:5])

        summary_parts = ["## Auto-Generated Summary\n"]
        summary_parts.append(f"Compacted {len(messages)} messages.\n")

        if decisions:
            summary_parts.append("## Key Points\n")
            for d in decisions[:5]:
                summary_parts.append(f"- {d.strip()}\n")

        if files_mentioned:
            summary_parts.append("## Files Mentioned\n")
            for f in sorted(files_mentioned)[:10]:
                summary_parts.append(f"- {f}\n")

        return "".join(summary_parts)

    def auto_compact_if_needed(
        self,
        messages: List[Message],
        keep_recent: int = 4,
    ) -> Tuple[List[Message], Optional[CompactBoundary]]:
        if self.should_compact(messages):
            return self.compact(messages, keep_recent)
        return messages, None

    def get_boundaries(self) -> List[Dict[str, Any]]:
        return [
            {
                "timestamp": b.timestamp,
                "tokens_before": b.tokens_before,
                "tokens_after": b.tokens_after,
                "messages_compacted": b.messages_compacted,
                "summary_preview": b.summary[:200],
            }
            for b in self._boundaries
        ]

    def strip_images_from_messages(self, messages: List[Message]) -> List[Message]:
        cleaned = []
        for msg in messages:
            content = msg.content
            import re
            content = re.sub(r'!\[.*?\]\(.*?\)', '[image]', content)
            content = re.sub(r'<img[^>]*>', '[image]', content)
            if content != msg.content:
                cleaned.append(Message(
                    role=msg.role,
                    content=content,
                    timestamp=msg.timestamp,
                    token_count=self.estimate_tokens(content),
                    metadata=msg.metadata,
                ))
            else:
                cleaned.append(msg)
        return cleaned
