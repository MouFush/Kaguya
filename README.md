# KaguyaIDE 3.1.0 Desktop Backend

KaguyaIDE 3.1.0 is a desktop distribution source tree. The desktop backend is now the Go service under `desktop/resources/go-backend`. The former giant Python HTTP entry has been physically removed from this repository.

## Current Layout

```text
KaguyaIDE-3.1.0-win64-Desktop/
|-- desktop/
|   |-- Kaguya IDE.exe
|   |-- *.dll / *.pak / Electron runtime files
|   |-- locales/
|   `-- resources/
|       |-- app.asar
|       |-- app.asar.src/
|       |   |-- electron/
|       |   |   |-- main.js
|       |   |   |-- preload.js
|       |   |   `-- tests/
|       |   `-- assets/
|       |-- go-backend/
|       |   |-- main.go
|       |   |-- server.go
|       |   |-- *_service.go
|       |   |-- *_test.go
|       |   |-- route_contract_generated.go
|       |   |-- legacy_symbol_catalog_generated.go
|       |   |-- static/
|       |   `-- kaguya-go-backend.exe
|       `-- python-app/
|           |-- kaguya_*.py
|           |-- start_server.py
|           |-- scripts/
|           `-- tests/
|-- docs/
`-- README.md
```

## Backend Responsibilities

The Go backend owns:

- HTTP routing and desktop API compatibility.
- Static UI and asset serving, including fallback aliases for desktop chrome images.
- Device API key vault and masked API-key responses.
- OpenAI-compatible provider chat for Kimi/Moonshot, DeepSeek, OpenAI-compatible custom providers, and others.
- Live external provider verification through `/agent/api-test` and `/deepseek/test`.
- Agent run IDs, SSE start frames, abort registry, provider-backed chat runs, and task snapshots.
- Workspace path authorization and trusted project allowlist.
- File tree, read, write, upload, and revert snapshots.
- Terminal command parsing, risk classification, permission decisions, execution, timeout handling, and audit log.
- Project compile/run execution through the same workspace and terminal permission services.
- Local KB/RAG document store, search, stats, preview, delete, and cache clear.
- Auth/account compatibility routes.
- Security and privacy status/export/delete routes.

Python is not the default HTTP backend. `desktop/resources/python-app/start_server.py --backend bootstrap` remains only as an optional compatibility worker entry for isolated Python capabilities.

## Runtime Rules

- Desktop HTTP must bind to `127.0.0.1`.
- Desktop mode does not grant unrestricted file access.
- File APIs are limited to the Go workspace root or explicitly trusted project roots.
- Terminal execution is never shell mode by default.
- Dangerous commands are denied before execution and audited.
- API keys must never be returned in full from renderer-facing APIs.
- Mini server mode is diagnostic fallback only; it must not pretend the Go backend is healthy.

## Build And Test

Run from repository root:

```powershell
python -m compileall .\desktop\resources\python-app
python -m unittest discover -s .\desktop\resources\python-app\tests -v
python .\desktop\resources\python-app\scripts\go_route_coverage.py --fail-under 100
python .\desktop\resources\python-app\scripts\smoke_flask.py
node --check .\desktop\resources\app.asar.src\electron\main.js
node --check .\desktop\resources\app.asar.src\electron\preload.js
node .\desktop\resources\app.asar.src\electron\tests\check-electron-ipc.js
```

Run from `desktop/resources/go-backend`:

```powershell
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe test ./...
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe build -o kaguya-go-backend.exe .
```

The smoke script name is historical; it starts the Go backend and validates the core HTTP surface.

## GitHub

The active repository target is [MouFush/Kaguya](https://github.com/MouFush/Kaguya).

