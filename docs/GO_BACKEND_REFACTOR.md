# Go Backend Refactor Notes

The desktop backend has been moved to `desktop/resources/go-backend`. The former giant Python HTTP entry has been removed from this repository.

## Startup Model

- Electron starts `desktop/resources/go-backend/kaguya-go-backend.exe`.
- If no binary is present and `go` exists on PATH, Electron can run `go run .` from `desktop/resources/go-backend`.
- If Go cannot start, Electron opens the diagnostic/setup flow and may start mini server mode. Mini mode is not a full backend.
- Go serves `desktop/resources/go-backend/static/index.html` for `/`.
- Go serves assets from `--app-dir` for `/static/*`, `/assets/*`, `/header-img`, `/hero-img`, `/welcome-img`, `/background`, `/wallpaper`, `/deepseek-icon`, `/sidebar-icon`, and `/favicon.ico`.
- Desktop chrome image routes use explicit fallback aliases when legacy icon filenames are not present in `python-app/assets`.
- Optional Python worker mode uses `desktop/resources/python-app/start_server.py --backend bootstrap` and is enabled only by `KAGUYA_ENABLE_PYTHON_WORKER=1`.

## Go-Owned APIs

Go owns the core API surface:

- `/health`
- `/api/config`
- `/api/model-status`
- `/api/device/info`
- `/api/device/bind`
- `/api/device/unbind`
- `/api/account/saved-config`
- `/api/account/auto-fill`
- `/models`
- `/agent/api-test`
- `/deepseek/test`
- `/chat`
- `/api/chat`
- `/chat/completions`
- `/agent/tasks`
- `/agent/run`
- `/agent/abort`
- `/agent/file-tree`
- `/agent/read-file`
- `/agent/write-file`
- `/agent/file-write`
- `/agent/revert-file`
- `/agent/import-files`
- `/agent/upload-device-files`
- `/agent/terminal/exec`
- `/rag/documents`
- `/rag/add_text`
- `/rag/search`
- `/rag/stats`
- `/kb/add`
- `/kb/search`
- `/permissions/status`
- `/permissions/mode`
- `/permissions/check`
- `/security/status`
- `/privacy/settings`
- `/privacy/export`
- `/privacy/delete`

The archived route catalog tracks 241 historical routes and the Go router covers them through exact handlers or explicit prefix handlers.

`/agent/run` now emits a Go-owned SSE lifecycle. With a saved external provider key it sends the prompt through the Go provider client and emits an assistant message frame; without a key it returns a structured `missing_api_key` frame.

`/agent/compile` and `/agent/run-project` execute through the Go workspace and terminal permission services. Medium/high risk commands are denied in default `ask` mode and only execute after permission mode allows them.

`/agent/api-test` and `/deepseek/test` perform real OpenAI-compatible `/models` verification through the Go provider client. Kimi/Moonshot defaults use `https://api.moonshot.ai/v1` and `kimi-k2.6`; rejected keys and network errors return structured JSON without leaking the key.

## Safety Boundaries

- API keys are persisted in `device_vault.enc` with AES-GCM using a local runtime-derived key.
- API responses return only masked API keys.
- Workspace paths use real path and common path checks.
- Imported projects are trusted only after explicit confirmation.
- Terminal execution uses argv execution, denies shell mode by default, classifies risk, and writes audit records.
- Go does not pretend models are online. Missing provider config returns structured unavailable JSON.

## Build

```powershell
cd desktop\resources\go-backend
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\gofmt.exe -w .
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe test ./...
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe build -o kaguya-go-backend.exe .
```

## Deletion Status

- Former Python HTTP monolith: deleted.
- Electron default backend: Go.
- Route coverage gate: `python desktop\resources\python-app\scripts\go_route_coverage.py --fail-under 100`.
- Remaining Python modules are compatibility helpers, optional worker modules, or tests/scripts.

