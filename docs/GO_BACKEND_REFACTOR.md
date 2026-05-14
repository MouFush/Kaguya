# Go Backend Refactor Notes

This build introduces a Go backend skeleton in `resources/go-backend` while keeping the existing Python Flask app as a compatibility worker.

## Startup Model

- Electron first tries `resources/go-backend/kaguya-go-backend.exe`.
- If no binary is present and `go` is available, Electron runs `go run .` from `resources/go-backend`.
- If Go cannot start, Electron falls back to the existing Python `qwen3_web.py` startup path.
- Go starts Python as a localhost-only worker when `--python-script` is provided, then reverse-proxies routes that are not owned by Go.

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

Heavy agent, RAG, chat provider calls, and legacy UI routes remain Python-worker responsibilities.

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
