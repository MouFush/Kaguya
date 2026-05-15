# Audit Notes

KaguyaIDE 3.1.0 now uses the Go backend as the primary desktop backend.

## Entrypoints

- Electron: `resources/app.asar.src/electron/main.js`
- Preload: `resources/app.asar.src/electron/preload.js`
- Backend binary: `resources/go-backend/kaguya-go-backend.exe`
- Backend source: `resources/go-backend/main.go`
- Optional Python worker: `resources/python-app/start_server.py --backend bootstrap`

## Binding

- Desktop HTTP binds to `127.0.0.1`.
- The Go backend owns API routing, static assets, device vault, workspace access, terminal permission, RAG/KB storage, and account compatibility routes.
- Python worker mode is optional and disabled by default.

## Runtime Data

Runtime data is excluded from source and packages:

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

## High-Risk APIs

- File APIs: `/agent/file-tree`, `/agent/read-file`, `/agent/write-file`, `/agent/file-write`, `/agent/revert-file`, `/agent/import-files`, `/agent/upload-device-files`
- Execution APIs: `/agent/terminal/exec`, `/agent/run-project`, `/agent/compile`, `/tool/execute`, `/code/execute`
- External provider APIs: `/api/chat`, `/chat`, `/chat/completions`, `/external/*`, `/deepseek/*`
- Device vault APIs: `/api/device/info`, `/api/device/bind`, `/api/device/unbind`, `/api/account/saved-config`, `/api/account/auto-fill`

## Security Model

- Workspace paths are authorized by `workspace_project_service.go`.
- Terminal commands are classified and executed by `terminal_permission_service.go`.
- Device API keys are encrypted in the local vault and are never returned in full to renderer/API responses.
- Electron IPC is documented in `IPC_CONTRACT.md` and does not expose arbitrary shell or file-system access.
