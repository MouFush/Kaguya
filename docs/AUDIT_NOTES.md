# KaguyaIDE 3.1.0 Audit Notes

## Entrypoints

- Electron entry: `resources/app.asar.src/electron/main.js`.
- Electron preload: `resources/app.asar.src/electron/preload.js`.
- Python backend entry used by Electron: temporary `kaguya_launcher.py` created by `Go backend startup`, which runs `resources/python-app/removed Flask monolith`.
- Python CLI entry: `resources/python-app/start_server.py`.
- Flask app: `removed Flask monolith`, with bootstrap routes registered from `kaguya_bootstrap.py`.

## Binding

- Desktop launcher binds Flask to `127.0.0.1` on the selected local port.
- `removed Flask monolith --localhost-only` binds to `127.0.0.1`; non-localhost binding is treated as remote exposure and high-risk routes require auth or are rejected.

## Runtime Data

These are runtime/user data, not source:

- `resources/python-app/ide_accounts.json`
- `resources/python-app/ide_workspaces/`
- `resources/python-app/audit_logs/`
- `resources/python-app/uploads/`
- `resources/python-app/code_executions/`
- `resources/python-app/rag_data/`
- `resources/python-app/audio_cache/`
- `resources/python-app/security_data/`
- `resources/python-app/data/`
- `resources/python-app/.kaguya/`
- `__pycache__/`, `.pytest_cache/`, `smoke-*.log`

## Permission Entrypoints

- API permission service: `resources/python-app/kaguya_api_permissions.py`.
- Legacy ACP permission manager: `resources/python-app/kaguya_permissions.py`.
- Bootstrap permission endpoint: `POST /permissions/check`.
- Workspace authorization: `resources/python-app/kaguya_workspace_security.py`.
- Terminal execution policy: `resources/python-app/kaguya_terminal_service.py`.

## High-Risk APIs

- File tree/read/write: `POST /agent/file-tree`, `POST /agent/read-file`, `POST /agent/write-file`, `POST /agent/file-write`.
- File mutation/revert/import/upload: `POST /agent/revert-file`, `POST /agent/import-files`, `POST /agent/upload-device-files`.
- Project trust/run: `POST /agent/open-project`, `POST /agent/run-project`, `POST /agent/stop-project`.
- Code/command execution: `POST /agent/terminal/exec`, `POST /agent/compile`, `POST /tool/execute`, `POST /code/execute`.
- External/network actions: `POST /agent/api-test`, `/deepseek/*`, `/external/*`, web fetch/search tools.

## Current Security Model

- Desktop mode no longer bypasses workspace authorization.
- Default file access is workspace-only.
- Explicit trusted imports are stored in `imported_paths` and validated with `realpath + commonpath`.
- `/agent/open-project` previews external folders but does not trust them unless the request includes explicit confirmation.
- Terminal execution uses `shell=False` by default and is denied unless the command is classified as low risk.
- Remote high-risk POST requests are rejected when auth is disabled.

