(function () {
  'use strict';

  const DEFAULT_TIMEOUT_MS = 30000;
  const state = window.KaguyaState || {
    provider: null,
    apiConfig: null,
    currentAgentRunId: null,
    currentAgentAbortController: null,
    currentWorkspace: null,
    uploadQueue: [],
    backendStatus: null,
    lastError: null,
  };

  function normalizeError(error, context) {
    const message = error && error.message ? error.message : String(error || 'Unknown error');
    return Object.assign({
      success: false,
      ok: false,
      error: 'request_failed',
      message,
    }, context || {});
  }

  function normalizeProviderPayload(data) {
    const input = data || {};
    const apiKey = String(input.api_key || input.apiKey || '').trim();
    const apiUrl = String(input.api_url || input.apiUrl || '').trim();
    return {
      provider: String(input.provider || '').trim(),
      api_key: apiKey,
      apiKey,
      api_url: apiUrl,
      apiUrl,
      model: String(input.model || '').trim(),
      enabled: Boolean(input.enabled || apiKey),
    };
  }

  function maskApiKey(apiKey) {
    const value = String(apiKey || '');
    if (!value) return '';
    if (value.includes('****')) return value;
    if (value.length <= 8) return value.slice(0, 2) + '****';
    return value.slice(0, 4) + '****' + value.slice(-4);
  }

  async function request(path, options) {
    const opts = Object.assign({}, options || {});
    const timeoutMs = opts.timeoutMs == null ? DEFAULT_TIMEOUT_MS : opts.timeoutMs;
    delete opts.timeoutMs;
    let timeoutId = null;
    const controller = opts.signal ? null : new AbortController();
    if (controller) {
      opts.signal = controller.signal;
    }
    if (timeoutMs > 0 && controller) {
      timeoutId = setTimeout(function () {
        controller.abort(new Error('request_timeout'));
      }, timeoutMs);
    }
    try {
      const response = await fetch(path, opts);
      const contentType = response.headers.get('Content-Type') || '';
      const text = await response.text();
      let body = text;
      if (contentType.includes('application/json')) {
        try {
          body = text ? JSON.parse(text) : {};
        } catch (error) {
          body = normalizeError(error, { error: 'invalid_json', status: response.status, path });
        }
      }
      if (!response.ok) {
        const payload = typeof body === 'object' && body !== null ? body : {};
        const normalized = Object.assign({
          success: false,
          ok: false,
          status: response.status,
          error: payload.error || 'http_error',
          message: payload.message || payload.detail || response.statusText || 'HTTP request failed',
          path,
        }, payload);
        state.lastError = normalized;
        return normalized;
      }
      return body;
    } catch (error) {
      const normalized = normalizeError(error, { path });
      state.lastError = normalized;
      return normalized;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  }

  function json(path, payload, options) {
    return request(path, Object.assign({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }, options || {}));
  }

  function get(path, options) {
    return request(path, Object.assign({ method: 'GET' }, options || {}));
  }

  function del(path, options) {
    return request(path, Object.assign({ method: 'DELETE' }, options || {}));
  }

  function put(path, payload, options) {
    return request(path, Object.assign({
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }, options || {}));
  }

  async function loadSavedConfig() {
    const data = await get('/api/account/saved-config');
    if (data && data.success && data.has_config) {
      state.apiConfig = {
        provider: data.provider || '',
        api_url: data.api_url || data.apiUrl || '',
        apiUrl: data.api_url || data.apiUrl || '',
        model: data.model || '',
        masked_api_key: data.masked_api_key || data.api_key || data.apiKey || '',
        hasSavedKey: true,
      };
      state.provider = state.apiConfig.provider || state.provider;
    }
    return data;
  }

  async function bindDeviceConfig(config) {
    const normalized = normalizeProviderPayload(config);
    const data = await json('/api/device/bind', normalized);
    if (data && data.success) {
      state.apiConfig = Object.assign({}, normalized, {
        api_key: '',
        apiKey: '',
        masked_api_key: data.masked_api_key || maskApiKey(normalized.api_key),
        hasSavedKey: true,
      });
      state.provider = normalized.provider || state.provider;
    }
    return data;
  }

  async function testProvider(config) {
    return json('/agent/api-test', normalizeProviderPayload(config), { timeoutMs: 45000 });
  }

  async function abortAgent(runId) {
    if (!runId) {
      return { success: false, aborted: false, error: 'missing_run_id', message: 'No active agent run.' };
    }
    return json('/agent/abort', { run_id: runId }, { timeoutMs: 10000 });
  }

  window.KaguyaState = state;
  window.KaguyaAPI = {
    request,
    get,
    del,
    put,
    json,
    normalizeProviderPayload,
    maskApiKey,
    loadSavedConfig,
    bindDeviceConfig,
    testProvider,
    abortAgent,
  };
})();
