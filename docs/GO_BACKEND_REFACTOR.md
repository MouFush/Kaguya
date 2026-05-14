# Go Backend Refactor Notes

This build introduces a Go backend in `resources/go-backend`. The migration target is to remove `qwen3_web.py` as an HTTP backend. Python is allowed only as an optional worker for model/agent/RAG internals during migration.

## Startup Model

- Electron first tries `resources/go-backend/kaguya-go-backend.exe`.
- If no binary is present and `go` is available, Electron runs `go run .` from `resources/go-backend`.
- If Go cannot start, Electron opens the diagnostic/setup flow. Legacy `qwen3_web.py` fallback is disabled unless `KAGUYA_ALLOW_LEGACY_QWEN3=1` is explicitly set.
- Go serves `resources/go-backend/static/index.html` directly for `/`.
- Go serves legacy static resources from `--app-dir` for `/static/*`, `/assets/*`, `/header-img`, `/hero-img`, `/welcome-img`, `/background`, `/wallpaper`, and `/favicon.ico`.
- Go starts Python as a localhost-only worker only when `--python-script` is provided. Electron no longer passes that flag by default; set `KAGUYA_ENABLE_PYTHON_WORKER=1` only for migration debugging.

## Go-Owned APIs

Go directly owns the minimum safe facade for:

- `GET /health`
- `GET|POST /api/config`
- `GET /api/model-status`
- `GET /api/device/info`
- `POST /api/device/bind`
- `POST /api/device/unbind`
- `GET /api/account/saved-config`
- `GET /api/account/auto-fill`
- `GET /models`
- `POST /chat`
- `POST /api/chat`
- `POST /chat/completions`
- `GET /agent/tasks`
- `POST /agent/abort`
- `GET /rag/documents`
- `GET /kaguya/features/flags`
- `GET /permissions/status`
- `GET|POST /permissions/mode`
- `POST /permissions/check`
- `/agent/file-tree`, `/agent/read-file`, `/agent/write-file`, `/agent/upload-device-files`
- `POST /agent/terminal/exec`

Heavy agent, RAG, and local model calls are the only remaining Python-worker responsibilities. Legacy UI delivery is no longer a Python responsibility.

## Safety Boundaries

- API keys are persisted in `device_vault.enc` with AES-GCM using a local device/runtime-derived key.
- API responses return only `masked_api_key`; full API keys are never returned to the renderer.
- File APIs normalize through real path checks and reject workspace escapes.
- Terminal execution uses `exec.CommandContext` with `shell=false`, blocks destructive commands and shell metacharacters, and writes audit records to `audit_logs/go_audit.jsonl`.
- Go does not pretend models are online. Without a saved key or Python worker it returns structured unavailable JSON.

## Build

Install Go, then run:

```powershell
cd resources\go-backend
gofmt -w .
go test ./...
go build -o kaguya-go-backend.exe .
```

The binary should stay outside `app.asar`, at `resources/go-backend/kaguya-go-backend.exe`.

## qwen3_web.py Removal Gate

`resources/python-app/qwen3_web.py` is no longer a normal startup dependency. Do not physically delete it until all of these are true:

- `resources/go-backend/kaguya-go-backend.exe` is built and bundled.
- Electron starts Go without `KAGUYA_ENABLE_PYTHON_WORKER=1`.
- `GET /`, image aliases, `/static/*`, config, device vault, file upload, terminal, permissions, external API, and agent facade routes pass smoke tests through Go.
- Python worker responsibilities are moved into small modules that are not Flask apps.
- `start_server.py`, Electron startup diagnostics, and docs no longer reference `qwen3_web.py`.
