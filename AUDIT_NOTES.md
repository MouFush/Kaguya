# KaguyaIDE 3.1.0 Audit Notes

This file records observed integration facts from the current desktop package source. It is not a security guarantee.

## Entrypoints

- Electron entry: `resources/app.asar.src/electron/main.js`
- Electron preload: `resources/app.asar.src/electron/preload.js`
- Packaged Electron archive used by the app: `resources/app.asar`
- Python backend entry used by Electron: `resources/python-app/removed_flask_monolith.py`
- Alternate bootstrap entry: `resources/python-app/start_server.py`
- Bootstrap module registered by `removed_flask_monolith.py`: `resources/python-app/kaguya_bootstrap.py`

## Startup And Binding

- Electron launches Python with `KAGUYA_ELECTRON=1`, `KAGUYA_DESKTOP_MODE=1`, `KAGUYA_DISABLE_NGROK=1`, and `KAGUYA_RUNTIME_DIR=<Electron userData>/kaguya/python-app`.
- Electron loads the web UI from `http://127.0.0.1:<port>/`.
- `removed_flask_monolith.py --localhost-only` binds Flask to `127.0.0.1`; the generic CLI default still accepts `--host` for non-desktop usage.
- Desktop mode must not be treated as unlimited file-system permission.

## Runtime Data

Python runtime/user data should live under `KAGUYA_RUNTIME_DIR` or the platform default user-data directory, not under `resources/python-app`.

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

- Flask permission status/check routes are registered through `kaguya_bootstrap.py`.
- API-side permission decisions are centralized through `resources/python-app/kaguya_api_permissions.py`.
- Terminal execution is centralized through `resources/python-app/kaguya_terminal_service.py`.
- Workspace path authorization is centralized through `resources/python-app/kaguya_workspace_security.py`.

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

The preload exposes only `kaguyaDesktop` with app info, device vault, and file/folder dialogs. Generic file-system and shell IPC handlers in `main.js` return disabled errors; the renderer should use Flask APIs for workspace-scoped actions.


