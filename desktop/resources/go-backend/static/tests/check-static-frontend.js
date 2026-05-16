const fs = require('fs');
const path = require('path');

const staticRoot = path.resolve(__dirname, '..');
const index = fs.readFileSync(path.join(staticRoot, 'index.html'), 'utf8');
const apiClient = fs.readFileSync(path.resolve(staticRoot, '..', '..', 'python-app', 'static', 'js', 'kaguya-api-client.js'), 'utf8');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

assert(index.includes('/static/js/kaguya-api-client.js'), 'index must load the shared API client');
assert(apiClient.includes('window.KaguyaAPI'), 'API client must expose window.KaguyaAPI');
assert(apiClient.includes('normalizeProviderPayload'), 'API client must normalize provider payloads');
assert(apiClient.includes('/api/account/saved-config'), 'API client must support saved-config reload');
assert(apiClient.includes('/api/device/bind'), 'API client must bind device vault config');
assert(apiClient.includes('/agent/abort'), 'API client must expose backend agent abort');
assert(index.includes('sanitizeApiProvidersForStorage'), 'index must sanitize provider localStorage writes');
assert(!index.includes("localStorage.setItem('api_providers',JSON.stringify(cfg))"), 'index must not store full provider config directly');
assert(!index.includes('localStorage.setItem("api_providers",JSON.stringify(cfg))'), 'index must not store full provider config directly');

console.log('static frontend contract ok');
