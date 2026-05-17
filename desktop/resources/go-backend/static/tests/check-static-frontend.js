const fs = require('fs');
const path = require('path');

const staticRoot = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(staticRoot, 'index.html'), 'utf8');
const agentIde = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'agent_ide.html'), 'utf8');
const apiClient = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'js', 'kaguya-api-client.js'), 'utf8');
const agentClient = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'js', 'kaguya-agent.js'), 'utf8');
const uploadClient = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'js', 'kaguya-file-upload.js'), 'utf8');
const streamClient = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'js', 'kaguya-stream.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(index.includes('/static/js/kaguya-api-client.js'), 'index must load the shared API client');
assert(index.includes('/static/js/kaguya-agent.js'), 'index must load the shared agent client');
assert(index.includes('/static/js/kaguya-file-upload.js'), 'index must load the shared upload client');
assert(index.includes('/static/js/kaguya-stream.js'), 'index must load the shared stream client');
assert(index.includes('/static/agent_ide.html'), 'index IDE entry must open the static IDE page');
assert(index.includes('hydrateSavedApiConfig'), 'index must hydrate saved device API config on startup');
assert(index.includes('KaguyaAPI.loadSavedConfig'), 'saved API config hydration must use shared API client');
assert(apiClient.includes('window.KaguyaAPI'), 'API client must expose window.KaguyaAPI');
assert(apiClient.includes('normalizeProviderPayload'), 'API client must normalize provider payloads');
assert(apiClient.includes('/api/account/saved-config'), 'API client must support saved-config reload');
assert(apiClient.includes('/api/device/bind'), 'API client must bind device vault config');
assert(apiClient.includes('/agent/abort'), 'API client must expose backend agent abort');
assert(agentClient.includes('window.KaguyaAgent'), 'Agent client must expose window.KaguyaAgent');
assert(agentClient.includes('currentAgentRunId'), 'Agent client must track backend run id');
assert(agentClient.includes('currentAgentAbortController'), 'Agent client must track browser abort controller');
assert(agentClient.includes('abortAgent'), 'Agent client must call backend abort');
assert(uploadClient.includes('window.KaguyaUpload'), 'Upload client must expose window.KaguyaUpload');
assert(uploadClient.includes('makeBatches'), 'Upload client must support batching');
assert(uploadClient.includes('batch_index'), 'Upload client must submit batch metadata');
assert(uploadClient.includes('batch_total'), 'Upload client must submit batch metadata');
assert(uploadClient.includes('Array.isArray'), 'Upload client must support repeated multipart fields');
assert(uploadClient.includes('Unknown error'), 'Upload client error fallback must be readable');
assert(streamClient.includes('window.KaguyaStream'), 'Stream client must expose window.KaguyaStream');
assert(streamClient.includes('readSSE'), 'Stream client must expose readSSE');
assert(streamClient.includes('postSSE'), 'Stream client must expose checked POST SSE helper');
assert(streamClient.includes('parseErrorResponse'), 'Stream client must parse non-OK stream errors');
assert(streamClient.includes('TextDecoder'), 'Stream client must decode SSE chunks');
assert(index.includes('KaguyaUpload.uploadForm'), 'RAG single upload must use shared upload client');
assert(index.includes('KaguyaUpload.uploadFiles'), 'RAG batch upload must use shared upload client');
assert(index.includes("KaguyaUpload.uploadForm('/finetune/dataset/upload'"), 'Finetune dataset upload must use shared upload client');
assert(index.includes("KaguyaUpload.uploadForm('/multimodal/upload'"), 'Multimodal upload must use shared upload client');
assert(index.includes('upload_helper_unavailable'), 'upload actions must fail diagnostically if shared helper is missing');
assert(!index.includes("fetch('/rag/upload'"), 'RAG upload must not keep naked fetch fallback');
assert(!index.includes("fetch('/rag/batch_upload'"), 'RAG batch upload must not keep naked fetch fallback');
assert(!index.includes("fetch('/finetune/dataset/upload'"), 'Finetune upload must not keep naked fetch fallback');
assert(!index.includes("fetch('/multimodal/upload'"), 'Multimodal upload must not keep naked fetch fallback');
assert(agentIde.includes('/agent/upload-device-files'), 'Static IDE page must upload through the backend device upload API');
assert(agentIde.includes('webkitdirectory'), 'Static IDE page must support folder upload');
assert(agentIde.includes('KaguyaUpload.uploadFiles'), 'Static IDE page must use shared upload client');
assert(index.includes('KaguyaStream.readSSE'), 'Chat streams must use shared stream reader');
assert(index.includes('KaguyaStream.postSSE'), 'Chat streams must use shared checked stream opener');
assert(!index.includes('body.getReader'), 'index must not keep private stream readers');
assert(!index.includes('new TextDecoder'), 'index must not keep private stream decoders');
assert(index.includes('safeHighlight'), 'index must guard highlight.js usage when CDN is unavailable');
assert(!index.includes("const decoder = new TextDecoder();\n                let buffer = '';"), 'Agent run must not keep a private SSE parser');
assert(index.includes('KaguyaAgent.begin'), 'Agent run must register browser abort controller');
assert(index.includes('KaguyaAgent.observeFrame'), 'Agent SSE frames must be observed for run_id');
assert(index.includes("data.type === 'run_started'"), 'Agent SSE run_started frame must be handled');
assert(index.includes("data.type === 'aborted'"), 'Agent SSE aborted frame must be handled');
assert(index.includes('sanitizeApiProvidersForStorage'), 'index must sanitize provider localStorage writes');
assert(index.includes('legacy-key-not-migrated'), 'legacy DeepSeek migration must not copy plaintext API keys');
assert(!index.includes('m.deepseek=deepseekConfig'), 'legacy DeepSeek migration must not store raw config');
assert(index.includes("localStorage.removeItem('deepseek_config')"), 'legacy DeepSeek plaintext config must be removed after migration');
assert(index.includes("localStorage.removeItem('models_config')"), 'legacy models plaintext config must be removed after migration');
assert(index.includes('hasSavedKey'), 'frontend must preserve saved key state without plaintext key');
assert(!index.includes("localStorage.setItem('api_providers',JSON.stringify(cfg))"), 'index must not store full provider config directly');
assert(!index.includes('localStorage.setItem("api_providers",JSON.stringify(cfg))'), 'index must not store full provider config directly');
assert(!index.includes("localStorage.setItem('models_config'"), 'index must not persist models_config plaintext keys');
assert(!index.includes('localStorage.setItem("models_config"'), 'index must not persist models_config plaintext keys');

console.log('static frontend contract ok');
