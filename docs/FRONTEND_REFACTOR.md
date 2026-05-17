# Frontend Refactor Notes

The frontend is still the existing static HTML UI. The first optimization step is deliberately conservative: no framework migration, no visual redesign, and no page rewrite.

## Current Direction

- Keep `desktop/resources/go-backend/static/index.html` as the served page while reducing hidden state and API drift.
- Add shared frontend utilities under `desktop/resources/python-app/static/js/` because Go serves that directory through `/static/*`.
- Move high-risk behavior behind shared helpers before extracting larger modules.

## Added Shared Client

`/static/js/kaguya-api-client.js` exposes:

- `window.KaguyaState`
- `window.KaguyaAPI.request`
- `window.KaguyaAPI.get`
- `window.KaguyaAPI.json`
- `window.KaguyaAPI.normalizeProviderPayload`
- `window.KaguyaAPI.loadSavedConfig`
- `window.KaguyaAPI.bindDeviceConfig`
- `window.KaguyaAPI.testProvider`
- `window.KaguyaAPI.abortAgent`

The client normalizes `apiKey/api_key` and `apiUrl/api_url`, handles JSON and structured errors consistently, and provides request timeouts without wrapping global `fetch`.

## Immediate Fixes

- API provider tests now use the shared client and backend `/agent/api-test`.
- Provider config saving binds the device vault before persisting local state.
- `localStorage` no longer receives the raw provider config object with a full API key; it stores only masked/saved-key metadata.
- Agent mode now loads `/static/js/kaguya-agent.js`, stores the backend `run_id` from the `run_started` SSE frame, and the stop button calls backend `/agent/abort` in addition to aborting the browser reader.
- RAG file upload now loads `/static/js/kaguya-file-upload.js`, uses shared upload helpers, sends batch metadata, and reports structured upload errors instead of only surfacing browser-level `Failed to fetch`.
- Chat streaming now loads `/static/js/kaguya-stream.js` and routes the main `/stream` and `/deepseek/chat` readers through one SSE parser, so chunk buffering and stop handling are not copied into each chat path.
- The smoke script checks that the shared API, Agent, upload, and stream helpers are served.
- `desktop/resources/go-backend/static/tests/check-static-frontend.js` guards the API-client contract and localStorage sanitization.

## Next Frontend Cuts

1. Connect IDE/device folder upload to `kaguya-file-upload.js`.
2. Move chat message rendering into `chat.js`; the raw SSE reader is already shared.
3. Move provider config UI rendering into `providers.js`.
4. Move the remaining Agent frame rendering into `agent.js`.
5. Split CSS into base/layout/components once JS state is less tangled.
