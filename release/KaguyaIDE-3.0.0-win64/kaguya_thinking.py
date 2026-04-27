#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 增强思维链系统
参考 Claude Code 的 thinking.ts + ThinkingConfig 架构
实现：自适应思考模式、思考预算管理、推理追踪、思考过程可视化
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class ThinkingMode(Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    ADAPTIVE = "adaptive"


@dataclass
class ThinkingConfig:
    mode: ThinkingMode = ThinkingMode.ADAPTIVE
    budget_tokens: int = 10000
    max_budget_tokens: int = 32768
    min_budget_tokens: int = 1024
    ultrathink_budget: int = 32768
    ultrathink_keyword: str = "ultrathink"
    model_supports_thinking: bool = True
    model_supports_adaptive: bool = True


@dataclass
class ThinkingStep:
    step_id: str
    content: str
    step_type: str = "reasoning"
    timestamp: float = 0.0
    duration_ms: int = 0
    token_count: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThinkingChain:
    chain_id: str
    steps: List[ThinkingStep] = field(default_factory=list)
    total_tokens: int = 0
    total_duration_ms: int = 0
    conclusion: str = ""
    mode: ThinkingMode = ThinkingMode.ADAPTIVE
    start_time: float = 0.0
    end_time: float = 0.0

    def add_step(self, step: ThinkingStep):
        self.steps.append(step)
        self.total_tokens += step.token_count
        self.total_duration_ms += step.duration_ms

    def get_summary(self) -> str:
        if not self.steps:
            return ""
        parts = []
        for i, step in enumerate(self.steps, 1):
            parts.append(f"[Step {i}] {step.content[:200]}")
        return "\n".join(parts)


class ThinkingChainManager:
    def __init__(self, config: ThinkingConfig = None):
        self._config = config or ThinkingConfig()
        self._active_chains: Dict[str, ThinkingChain] = {}
        self._completed_chains: List[ThinkingChain] = []
        self._max_completed = 100

    def _generate_id(self) -> str:
        import hashlib
        return hashlib.sha256(f"chain:{time.time()}:{id(self)}".encode()).hexdigest()[:12]

    def should_enable_thinking(self, user_message: str = "") -> bool:
        if not self._config.model_supports_thinking:
            return False

        if self._config.mode == ThinkingMode.DISABLED:
            return False

        if self._config.mode == ThinkingMode.ENABLED:
            return True

        if self._config.mode == ThinkingMode.ADAPTIVE:
            if not self._config.model_supports_adaptive:
                return False

            complexity_indicators = [
                "分析", "分析一下", "解释", "为什么", "如何",
                "analyze", "explain", "why", "how", "compare",
                "debug", "调试", "优化", "optimize", "refactor",
                "重构", "设计", "design", "architect",
            ]
            msg_lower = user_message.lower()
            for indicator in complexity_indicators:
                if indicator in msg_lower:
                    return True

            if len(user_message) > 200:
                return True

            return False

        return False

    def get_thinking_budget(self, user_message: str = "") -> int:
        if self._config.mode == ThinkingMode.DISABLED:
            return 0

        if self._has_ultrathink_keyword(user_message):
            return self._config.ultrathink_budget

        if self._config.mode == ThinkingMode.ENABLED:
            return self._config.budget_tokens

        if self._config.mode == ThinkingMode.ADAPTIVE:
            complexity = self._estimate_complexity(user_message)
            budget = int(self._config.min_budget_tokens + complexity * (self._config.max_budget_tokens - self._config.min_budget_tokens))
            return min(budget, self._config.max_budget_tokens)

        return self._config.budget_tokens

    def _has_ultrathink_keyword(self, text: str) -> bool:
        if not text:
            return False
        pattern = re.compile(r'\bultrathink\b', re.IGNORECASE)
        return bool(pattern.search(text))

    def _estimate_complexity(self, text: str) -> float:
        if not text:
            return 0.0

        score = 0.0

        high_complexity = ["架构", "设计", "重构", "architect", "refactor", "design", "system"]
        for kw in high_complexity:
            if kw in text.lower():
                score += 0.3

        medium_complexity = ["分析", "解释", "比较", "analyze", "explain", "compare", "debug"]
        for kw in medium_complexity:
            if kw in text.lower():
                score += 0.2

        code_indicators = text.count("```")
        score += min(code_indicators * 0.1, 0.3)

        length_factor = min(len(text) / 1000, 0.3)
        score += length_factor

        return min(score, 1.0)

    def start_chain(self, user_message: str = "") -> ThinkingChain:
        chain_id = self._generate_id()
        mode = self._config.mode
        if self._has_ultrathink_keyword(user_message):
            mode = ThinkingMode.ENABLED

        chain = ThinkingChain(
            chain_id=chain_id,
            mode=mode,
            start_time=time.time(),
        )
        self._active_chains[chain_id] = chain
        return chain

    def add_thinking_step(
        self,
        chain_id: str,
        content: str,
        step_type: str = "reasoning",
        token_count: int = 0,
        duration_ms: int = 0,
    ) -> Optional[ThinkingStep]:
        chain = self._active_chains.get(chain_id)
        if not chain:
            return None

        step = ThinkingStep(
            step_id=f"{chain_id}-{len(chain.steps)}",
            content=content,
            step_type=step_type,
            timestamp=time.time(),
            token_count=token_count or max(1, len(content) // 4),
            duration_ms=duration_ms,
        )
        chain.add_step(step)
        return step

    def end_chain(self, chain_id: str, conclusion: str = "") -> Optional[ThinkingChain]:
        chain = self._active_chains.pop(chain_id, None)
        if not chain:
            return None

        chain.end_time = time.time()
        chain.conclusion = conclusion

        self._completed_chains.append(chain)
        if len(self._completed_chains) > self._max_completed:
            self._completed_chains = self._completed_chains[-self._max_completed // 2:]

        return chain

    def get_chain(self, chain_id: str) -> Optional[ThinkingChain]:
        chain = self._active_chains.get(chain_id)
        if chain:
            return chain
        for c in self._completed_chains:
            if c.chain_id == chain_id:
                return c
        return None

    def build_thinking_prompt_section(self, budget: int) -> str:
        if budget <= 0:
            return ""

        return (
            f"You have a thinking budget of {budget} tokens. "
            f"Use this budget to reason through the problem step by step before responding. "
            f"Structure your thinking as:\n"
            f"1. Understand the request and identify key requirements\n"
            f"2. Consider possible approaches and trade-offs\n"
            f"3. Plan the implementation or solution\n"
            f"4. Anticipate potential issues and edge cases\n\n"
            f"After thinking, provide your final response clearly and concisely."
        )

    def parse_thinking_from_response(self, content: str) -> Tuple[str, Optional[str]]:
        thinking_patterns = [
            (re.compile(r'<thinking>(.*?)</thinking>', re.DOTALL), True),
            (re.compile(r'<think >(.*?)</think >', re.DOTALL), True),
            (re.compile(r'```thinking\n(.*?)\n```', re.DOTALL), True),
        ]

        for pattern, _ in thinking_patterns:
            match = pattern.search(content)
            if match:
                thinking = match.group(1).strip()
                formal = content[:match.start()] + content[match.end():]
                return formal.strip(), thinking

        lines = content.split("\n")
        thinking_lines = []
        formal_lines = []
        in_thinking = False

        for line in lines:
            if not in_thinking:
                thinking_starts = ["Thinking Process", "思考过程", "Thought Process", "Let me think"]
                if any(line.strip().startswith(ts) for ts in thinking_starts):
                    in_thinking = True
                    thinking_lines.append(line)
                    continue
                formal_lines.append(line)
            else:
                if line.strip() == "" and thinking_lines and thinking_lines[-1].strip() == "":
                    in_thinking = False
                    formal_lines.append(line)
                    continue
                thinking_lines.append(line)

        if thinking_lines:
            thinking = "\n".join(thinking_lines).strip()
            formal = "\n".join(formal_lines).strip()
            if formal:
                return formal, thinking

        return content, None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_chains": len(self._active_chains),
            "completed_chains": len(self._completed_chains),
            "total_tokens": sum(c.total_tokens for c in self._completed_chains),
            "avg_duration_ms": (
                sum(c.total_duration_ms for c in self._completed_chains) / len(self._completed_chains)
                if self._completed_chains else 0
            ),
            "config": {
                "mode": self._config.mode.value,
                "budget_tokens": self._config.budget_tokens,
                "model_supports_thinking": self._config.model_supports_thinking,
            },
        }
