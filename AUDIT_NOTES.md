# KaguyaIDE 3.1.0 Audit Notes

This file records observed integration facts from the current desktop package source. It is not a security guarantee.

## Entrypoints

- Electron entry: `resources/app.asar.src/electron/main.js`
- Electron preload: `resources/app.asar.src/electron/preload.js`
- Go backend: `resources/go-backend/kaguya-go-backend.exe` (compiled binary, build with `go build -o build/kaguya-go-backend.exe .`)
- Python compatibility launcher: `resources/python-app/start_server.py` (spawns Go backend)

## Startup And Binding

- Electron launches Go backend directly with `KAGUYA_DESKTOP_MODE=1`, `KAGUYA_ELECTRON=1`, `KAGUYA_DISABLE_NGROK=1`, and `KAGUYA_RUNTIME_DIR=<Electron userData>/kaguya/go-backend`.
- Electron loads the web UI from `http://127.0.0.1:<port>/`.
- Go backend binds to `127.0.0.1:8766` by default.
- Desktop mode must not be treated as unlimited file-system permission.

## Runtime Data

Runtime data lives under `KAGUYA_RUNTIME_DIR` or the platform default user-data directory, not under `resources/`.

Runtime paths include:

- `uploads/`
- `audio_cache/`
- `code_executions/`
- `rag_data/`
- `data/`
- `project_center/`
- `external_api/`
- `memory_system/`
- `multimodal/`
- `finetune/`
- `.kaguya/`
- `.kaguya_file_history/`
- `audit_logs/`
- `security_data/`
- `ide_accounts.json`

These paths are excluded by `.gitignore`, `.packageignore`, and `.asarignore`.

## Permission Entry Points

- Go backend permission decisions are centralized through `resources/go-backend/terminal_permission_service.go`.
- Go backend workspace authorization is centralized through `resources/go-backend/workspace_project_service.go`.
- Go backend security/privacy is centralized through `resources/go-backend/security_privacy_service.go`.

## File/Command Sensitive APIs

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

External/network/model APIs:

- `POST /api/chat`
- `POST /chat`
- `POST /chat/completions`
- `POST /deepseek/chat`
- `POST /deepseek/test`
- `GET|POST /api/model-status`
- `GET|POST /api/config`

Device API-key APIs:

- `GET /api/device/info`
- `POST /api/device/bind`
- `POST /api/device/unbind`
- `GET /api/account/saved-config`
- `GET /api/account/auto-fill`

## Electron IPC Surface

The preload exposes only `kaguyaDesktop` with app info, device vault, and file/folder dialogs. Generic file-system and shell IPC handlers in `main.js` return disabled errors; the renderer uses Go backend APIs for workspace-scoped actions.
