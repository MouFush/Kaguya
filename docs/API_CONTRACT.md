# Kaguya IDE API Contract

This document records the integration baseline verified by tests. It does not assert model availability.

## Frontend Calls

The packaged frontend and Electron shell call these core paths:

- `/`
- `/chat`
- `/stream`
- `/agent/tasks`
- `/rag/documents`
- `/kaguya/features/flags`
- `/permissions/status`
- `/permissions/mode`
- `/permissions/check`
- `/agent/upload-device-files`
- `/agent/abort`
- `/api/device/info`
- `/api/device/bind`
- `/api/device/unbind`
- `/api/account/saved-config`
- `/api/account/auto-fill`
- Compatibility paths: `/api/chat`, `/api/model-status`, `/api/config`, `/models`, `/chat/completions`

Dynamic paths such as `/agent/tasks/<task_id>`, `/rag/delete/<doc_id>`, `/rag/preview/<doc_id>`, and `/services/<service_id>/restart` are exposed by Flask.

## Compatibility Shims

These routes exist to support older Electron or frontend callers:

- `POST /api/chat` delegates to the same logic as `POST /chat`.
- `GET|POST /api/model-status` returns structured backend/model status and does not claim Ollama is available when it is not.
- `GET /models` returns local and external model metadata; external providers require keys and are not marked available by default.
- `GET /api/config` returns basic runtime configuration.
- `POST /chat/completions` provides an OpenAI-compatible response only when an explicit external API config is supplied; otherwise it returns structured `501` JSON.

## Agent Cancellation

- `POST /agent/run` sends an SSE `run_started` frame with a `run_id` before model/tool work starts.
- `POST /agent/abort` sets the backend abort event for that `run_id`; the frontend browser abort alone is not treated as sufficient cancellation.
- Go-owned agent runs check the abort event before provider work and before terminal frames. With a saved provider key they emit an assistant `message` SSE frame; without a key they emit structured `missing_api_key`.
- Project subprocesses use terminal timeout handling rather than a persistent PTY-style process manager.

## Device API Config

- Full Flask mode stores device API config through the existing per-device account store and returns only masked keys.
- Full Flask mode stores runtime config under `KAGUYA_RUNTIME_DIR` or the platform user-data directory, not under `resources/python-app`.
- Electron mini mode stores the same config in `userData/kaguya/device_vault.enc`; full keys are not returned to the renderer.
- `apiKey`/`apiUrl` and `api_key`/`api_url` payloads are normalized to `api_key`/`api_url` before use.
- `/api/account/auto-fill` intentionally does not return the full API key.
- Masked-key round trips must not clear the saved provider key; status checks may use saved server-side config by `device_id`.

## Kimi/Moonshot Compatibility

- `kimi` and `moonshot` default to `https://api.moonshot.ai/v1`.
- Kimi K2-family chat payloads disable thinking explicitly and use `max_completion_tokens`; arbitrary `temperature` is omitted to avoid provider-side parameter rejection.

## Mini Fallback

- Mini fallback is only used when the Python backend does not become healthy.
- Mini responses identify themselves with `mode:"mini"` and `backend_available:false`.
- Mini chat returns `backend_unavailable` unless an encrypted external provider config exists. It must not claim Ollama or the Python backend is online.

## IDE File Upload

- `POST /agent/upload-device-files` accepts multipart file uploads with `files`, `device_id`, and optional `batch_index`/`batch_total` metadata.
- The web fallback batches large folder uploads at 100 files or 64 MB per request. This avoids browser or Werkzeug aborts that surface only as `Failed to fetch`.
- Electron native import should be preferred when the desktop preload bridge is available, because it imports by local path instead of sending a huge multipart body through Chromium.
- Upload failures must be surfaced as structured JSON when the request reaches Flask; browser-level aborts remain visible in the terminal log with batch context.

## Optional Dependencies

The base app must import and serve core APIs without these optional dependencies:

- Ollama service and local model
- `torch`
- `transformers`
- `peft`
- CLIP model weights

When Ollama is unavailable, chat endpoints return structured JSON with `available:false`, `reason:"ollama_unavailable"`, and a remediation message.

## Test Commands

Run from the packaged project root:

```powershell
python -m compileall .\resources\python-app
python -m unittest discover -s .\resources\python-app\tests -v
python .\resources\python-app\scripts\smoke_flask.py
node --check .\resources\app.asar.src\electron\main.js
node --check .\resources\app.asar.src\electron\preload.js
python .\resources\python-app\scripts\go_route_coverage.py --fail-under 100
```

