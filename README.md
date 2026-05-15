# KaguyaIDE 3.1.0 Desktop Backend

KaguyaIDE 3.1.0 is a desktop distribution source tree. The backend is now a Go service. The former giant Python HTTP monolith has been physically removed from this repository.

## Current Architecture

```text
KaguyaIDE-3.1.0-win64-Desktop
├── Kaguya IDE.exe
├── resources
│   ├── app.asar
│   ├── app.asar.src
│   │   └── electron
│   │       ├── main.js
│   │       ├── preload.js
│   │       └── tests
│   ├── go-backend
│   │   ├── main.go
│   │   ├── server.go
│   │   ├── *_service.go
│   │   ├── *_test.go
│   │   ├── route_contract_generated.go
│   │   ├── legacy_symbol_catalog_generated.go
│   │   ├── static
│   │   └── kaguya-go-backend.exe
│   └── python-app
│       ├── kaguya_*.py
│       ├── start_server.py
│       ├── scripts
│       └── tests
├── docs
├── AUDIT_NOTES.md
├── IPC_CONTRACT.md
└── README.md
```

## Backend Responsibilities

The Go backend owns:

- HTTP routing and desktop API compatibility
- Static UI and asset serving
- Device API key vault and masked API-key responses
- OpenAI-compatible provider chat for Kimi, Moonshot, DeepSeek, OpenAI-compatible custom providers, and others
- Agent run IDs, SSE start frames, abort registry, and task snapshots
- Workspace path authorization and trusted project allowlist
- File tree, read, write, upload, and revert snapshots
- Terminal command parsing, risk classification, permission decisions, execution, timeout handling, and audit log
- Local KB/RAG document store, search, stats, preview, delete, and cache clear
- Auth/account compatibility routes
- Security and privacy status/export/delete routes

Python is no longer the default HTTP backend. `resources/python-app/start_server.py --backend bootstrap` remains only as an optional compatibility worker entry for future isolated Python capabilities.

## Important Runtime Rules

- Desktop HTTP must bind to `127.0.0.1`.
- Desktop mode does not grant unrestricted file access.
- File APIs are limited to the Go workspace root or explicitly trusted project roots.
- Terminal execution is never shell mode by default.
- Dangerous commands are denied before execution and audited.
- API keys must never be returned in full from renderer-facing APIs.
- Mini server mode is diagnostic fallback only; it must not pretend the backend is healthy.

## Build And Test

Run from repository root:

```powershell
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe test ./...
```

Run from `resources/go-backend`:

```powershell
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe build -o kaguya-go-backend.exe .
```

Python helper tests:

```powershell
python -m unittest discover -s resources\python-app\tests -v
```

Route coverage gate:

```powershell
python resources\python-app\scripts\go_route_coverage.py --fail-under 100
```

Electron syntax checks:

```powershell
node --check resources\app.asar.src\electron\main.js
node --check resources\app.asar.src\electron\preload.js
```

Go backend smoke:

```powershell
python resources\python-app\scripts\smoke_flask.py
```

The smoke script name is historical; it starts the Go backend and validates the core API surface.

## GitHub

The active repository target is:

[MouFush/Kaguya](https://github.com/MouFush/Kaguya)
