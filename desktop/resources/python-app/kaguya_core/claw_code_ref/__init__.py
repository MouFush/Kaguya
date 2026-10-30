"""
Claw Code Reference Package
Ported from https://github.com/ultraworkers/claw-code

This package contains reference implementations from the claw-code project,
adapted for the Kaguya AI Platform.

Key Architecture Patterns:
1. TranscriptStore - Message history with auto-compaction
2. SessionStore - Session persistence to disk
3. HistoryLog - Event tracking for debugging
4. QueryEngineConfig - max_turns=8, compact_after_turns=12
5. Runtime - Full session lifecycle management
"""
