(function () {
  'use strict';

  async function readSSE(response, handlers) {
    const opts = handlers || {};
    if (!response || !response.body) {
      throw new Error('stream_body_unavailable');
    }
    const reader = response.body.getReader();
    if (opts.onReader) opts.onReader(reader);
    const decoder = new TextDecoder();
    let buffer = '';
    try {
      while (true) {
        if (opts.shouldStop && opts.shouldStop()) break;
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (opts.onFrame) opts.onFrame(data);
          } catch (error) {
            if (opts.onParseError) opts.onParseError(error, line);
          }
        }
      }
      if (buffer.trim().startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.trim().slice(6));
          if (opts.onFrame) opts.onFrame(data);
        } catch (error) {
          if (opts.onParseError) opts.onParseError(error, buffer);
        }
      }
    } finally {
      if (opts.onReader) opts.onReader(null);
    }
  }

  async function parseErrorResponse(response) {
    const contentType = response.headers ? (response.headers.get('Content-Type') || '') : '';
    const text = await response.text().catch(function () { return ''; });
    if (contentType.includes('application/json')) {
      try {
        const data = text ? JSON.parse(text) : {};
        return data && (data.message || data.error || data.detail) ? data : { message: response.statusText || 'HTTP error' };
      } catch (error) {
        return { message: text || response.statusText || 'HTTP error', error: 'invalid_json' };
      }
    }
    return { message: text || response.statusText || 'HTTP error' };
  }

  async function openSSE(url, payload, options) {
    const opts = options || {};
    const requestOptions = Object.assign({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }, opts.request || {});
    if (opts.signal) requestOptions.signal = opts.signal;
    const response = await fetch(url, requestOptions);
    if (!response.ok) {
      const data = await parseErrorResponse(response);
      const err = new Error(data.message || data.error || ('HTTP ' + response.status));
      err.status = response.status;
      err.payload = data;
      throw err;
    }
    return response;
  }

  async function postSSE(url, payload, handlers, options) {
    const response = await openSSE(url, payload, options);
    return readSSE(response, handlers || {});
  }

  window.KaguyaStream = {
    openSSE,
    postSSE,
    readSSE,
  };
})();
