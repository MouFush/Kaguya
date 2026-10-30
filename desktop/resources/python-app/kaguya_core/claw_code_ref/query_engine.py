"""
Claw Code Reference - Query Engine
Ported from https://github.com/ultraworkers/claw-code/src/query_engine.py

KEY ARCHITECTURE INSIGHTS FOR MEMORY MANAGEMENT:
1. max_turns = 8 (not 25!) - prevents runaway loops
2. compact_after_turns = 12 - auto-compacts message history
3. max_budget_tokens = 2000 - token budget limit
4. TranscriptStore.compact(keep_last=10) - keeps only recent messages
5. persist_session() - saves session to disk for resumption
6. from_saved_session() - loads previous session context
7. compact_messages_if_needed() - called after every turn
8. structured_output with retry - robust output parsing

MEMORY FIX PATTERN:
- After each turn, check if messages exceed compact_after_turns
- If so, keep only the system message + last N messages
- This prevents context window overflow and repetitive behavior
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class QueryEngineConfig:
    max_turns: int = 8
    max_budget_tokens: int = 2000
    compact_after_turns: int = 12
    structured_output: bool = False
    structured_retry_limit: int = 2


@dataclass(frozen=True)
class TurnResult:
    prompt: str
    output: str
    matched_commands: tuple[str, ...]
    matched_tools: tuple[str, ...]
    permission_denials: tuple = ()
    usage: object = None
    stop_reason: str = 'completed'


@dataclass
class UsageSummary:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_turn(self, prompt: str, output: str) -> 'UsageSummary':
        est_in = len(prompt) // 4
        est_out = len(output) // 4
        return UsageSummary(
            input_tokens=self.input_tokens + est_in,
            output_tokens=self.output_tokens + est_out,
        )
