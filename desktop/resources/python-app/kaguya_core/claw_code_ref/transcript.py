"""
Claw Code Reference - Transcript Store
Ported from https://github.com/ultraworkers/claw-code/src/transcript.py

Key concepts:
- TranscriptStore maintains a list of message entries
- compact(keep_last=10) drops old entries, keeping only the most recent
- replay() returns all entries as a tuple
- flush() marks the store as flushed
- This is the core memory management mechanism - prevents context overflow
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class TranscriptStore:
    entries: list[str] = field(default_factory=list)
    flushed: bool = False

    def append(self, entry: str) -> None:
        self.entries.append(entry)
        self.flushed = False

    def compact(self, keep_last: int = 10) -> None:
        if len(self.entries) > keep_last:
            self.entries[:] = self.entries[-keep_last:]

    def replay(self) -> tuple[str, ...]:
        return tuple(self.entries)

    def flush(self) -> None:
        self.flushed = True
