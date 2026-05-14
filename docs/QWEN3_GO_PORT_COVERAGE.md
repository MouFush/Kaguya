# qwen3 to Go Port Coverage

The legacy monolith must not be deleted until the Go backend reaches route and behavior parity. The current state is intentionally tracked by `resources/python-app/scripts/go_route_coverage.py`.

Current local audit on 2026-05-15 after restoring the legacy monolith and expanding the Go HTTP surface:

- Legacy Flask routes in `resources/python-app/qwen3_web.py`: 241 static `@app.route` entries in the restored source
- Go HTTP handlers in `resources/go-backend/server.go`: 145
- Direct Go route coverage: 241 / 241 = 100%
- Missing legacy routes: 0
- Conclusion: the Go backend now has a mapped HTTP entrypoint for every static Flask route found by the audit. This is still not enough to delete the monolith: several routes are intentionally structured `unavailable` responses or durable local facades, not full behavior parity.

Hard deletion gate:

```powershell
python resources\python-app\scripts\go_route_coverage.py --fail-under 100
go test ./...
python resources\python-app\scripts\smoke_go.py
```

The monolith can be physically deleted only after the coverage gate passes and the remaining Python modules are libraries, not HTTP entrypoints.

Route coverage is a deletion prerequisite, not the deletion approval. The next gate is behavior parity for the high-risk domains: auth/session lifecycle, RAG document lifecycle, agent run/tool loop, external provider streaming, project execution, and workflow/MCP integrations.

Migration order:

1. Static UI, assets, device vault, config, permissions, file upload, terminal.
2. Auth, CSRF/security status, accounts, privacy, audit.
3. External provider chat, DeepSeek/Kimi/OpenAI-compatible routes, streaming.
4. RAG/KB/search document lifecycle.
5. Agent run loop, abort, task management, tool execution.
6. Project center, artifacts, playbooks, ops/release/alerts/integrations.
7. Multimodal, memory, finetune, workflows, MCP.
