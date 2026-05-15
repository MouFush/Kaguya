# KaguyaIDE 3.1.0 Audit Notes

This file records the current executable facts after the Go backend migration.

## Entrypoints

- Electron entry: `resources/app.asar.src/electron/main.js`
- Electron preload: `resources/app.asar.src/electron/preload.js`
- Primary backend entry: `resources/go-backend/kaguya-go-backend.exe`
- Go source entry: `resources/go-backend/main.go`
- Optional Python worker entry: `resources/python-app/start_server.py --backend bootstrap`
- Static UI served by Go: `resources/go-backend/static/index.html`

## Startup And Binding

- Electron starts the Go backend on `127.0.0.1:<port>`.
- Python is not part of the default desktop startup path.
- Optional Python worker mode is opt-in through `KAGUYA_ENABLE_PYTHON_WORKER=1`.
- Mini server is a diagnostic fallback only and must report `mode: "mini"` plus `backend_available: false`.

## Runtime Data

Runtime/user data must live under Electron `userData/kaguya` or a caller-provided `--runtime-dir`, not under source directories.

Excluded runtime paths include:

- `__pycache__/`
- `.pytest_cache/`
- `smoke-*.log`
- `ide_accounts.json`
- `ide_workspaces/`
- `audit_logs/`
- `uploads/`
- `code_executions/`
- `rag_data/`
- `audio_cache/`
- `security_data/`
- `data/`

## Permission Entry Points

- Go permission and terminal policy: `resources/go-backend/terminal_permission_service.go`
- Go workspace authorization: `resources/go-backend/workspace_project_service.go`
- Go security/privacy status: `resources/go-backend/security_privacy_service.go`
- Go auth/account compatibility: `resources/go-backend/auth_account_service.go`

## Sensitive APIs

File/project APIs:

- `POST /agent/read-file`
- `POST /agent/write-file`
- `POST /agent/file-write`
- `POST /agent/revert-file`
- `POST /agent/file-tree`
- `POST /agent/open-project`
- `POST /agent/import-files`
- `POST /agent/upload-device-files`

Command/project execution APIs:

- `POST /agent/terminal/exec`
- `POST /agent/run-project`
- `POST /agent/compile`
- `POST /tool/execute`
- `POST /code/execute`

Device API-key APIs:

- `GET /api/device/info`
- `POST /api/device/bind`
- `POST /api/device/unbind`
- `GET /api/account/saved-config`
- `GET /api/account/auto-fill`

## Current Security Model

- Desktop mode does not bypass workspace authorization.
- Default file access is limited to the Go-managed workspace root.
- Explicit trusted project imports are stored and checked with real path plus common path rules.
- Terminal execution uses argv execution, shell mode is denied by default, and denied commands are audited.
- Electron preload exposes a narrow `kaguyaDesktop` API; generic shell and file-system IPC is disabled.
