const fs = require('fs');
const path = require('path');

const staticRoot = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(staticRoot, 'index.html'), 'utf8');
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
assert(streamClient.includes('window.KaguyaStream'), 'Stream client must expose window.KaguyaStream');
assert(streamClient.includes('readSSE'), 'Stream client must expose readSSE');
assert(streamClient.includes('TextDecoder'), 'Stream client must decode SSE chunks');
assert(index.includes('KaguyaUpload.uploadForm'), 'RAG single upload must use shared upload client');
assert(index.includes('KaguyaUpload.uploadFiles'), 'RAG batch upload must use shared upload client');
assert(index.includes("KaguyaUpload.uploadForm('/finetune/dataset/upload'"), 'Finetune dataset upload must use shared upload client');
assert(index.includes("KaguyaUpload.uploadForm('/multimodal/upload'"), 'Multimodal upload must use shared upload client');
assert(index.includes('KaguyaStream.readSSE'), 'Chat streams must use shared stream reader');
assert(!index.includes('body.getReader'), 'index must not keep private stream readers');
assert(!index.includes('new TextDecoder'), 'index must not keep private stream decoders');
assert(!index.includes("const decoder = new TextDecoder();\n                let buffer = '';"), 'Agent run must not keep a private SSE parser');
assert(index.includes('KaguyaAgent.begin'), 'Agent run must register browser abort controller');
assert(index.includes('KaguyaAgent.observeFrame'), 'Agent SSE frames must be observed for run_id');
assert(index.includes("data.type === 'run_started'"), 'Agent SSE run_started frame must be handled');
assert(index.includes("data.type === 'aborted'"), 'Agent SSE aborted frame must be handled');
assert(index.includes('sanitizeApiProvidersForStorage'), 'index must sanitize provider localStorage writes');
assert(!index.includes("localStorage.setItem('api_providers',JSON.stringify(cfg))"), 'index must not store full provider config directly');
assert(!index.includes('localStorage.setItem("api_providers",JSON.stringify(cfg))'), 'index must not store full provider config directly');

console.log('static frontend contract ok');
