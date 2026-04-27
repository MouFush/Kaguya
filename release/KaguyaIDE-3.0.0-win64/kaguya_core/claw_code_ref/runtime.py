"""
Claw Code Reference - Runtime
Ported from https://github.com/ultraworkers/claw-code/src/runtime.py

KEY ARCHITECTURE INSIGHTS:
1. bootstrap_session() - creates a full session with context, setup, history
2. run_turn_loop() - runs multiple turns with max_turns=3 limit
3. HistoryLog tracks: context, registry, routing, execution, turn, session_store
4. PortRuntime routes prompts to commands/tools before sending to LLM
5. Permission denials are tracked and reported
6. Sessions are persisted after each bootstrap
"""
