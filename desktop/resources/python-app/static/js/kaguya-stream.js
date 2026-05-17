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

  window.KaguyaStream = {
    readSSE,
  };
})();
