(function () {
  'use strict';

  const DEFAULT_BATCH_LIMIT = 100;
  const DEFAULT_BYTE_LIMIT = 64 * 1024 * 1024;

  function toArray(files) {
    return Array.prototype.slice.call(files || []);
  }

  function makeBatches(files, options) {
    const opts = options || {};
    const maxFiles = opts.maxFiles || DEFAULT_BATCH_LIMIT;
    const maxBytes = opts.maxBytes || DEFAULT_BYTE_LIMIT;
    const batches = [];
    let current = [];
    let bytes = 0;
    toArray(files).forEach(function (file) {
      const size = file && file.size ? file.size : 0;
      if (current.length && (current.length >= maxFiles || bytes + size > maxBytes)) {
        batches.push(current);
        current = [];
        bytes = 0;
      }
      current.push(file);
      bytes += size;
    });
    if (current.length) batches.push(current);
    return batches;
  }

  async function uploadForm(url, formData, options) {
    const response = await fetch(url, Object.assign({ method: 'POST', body: formData }, options || {}));
    const contentType = response.headers.get('Content-Type') || '';
    const text = await response.text();
    let body = text;
    if (contentType.includes('application/json')) {
      try {
        body = text ? JSON.parse(text) : {};
      } catch (error) {
        body = { success: false, error: 'invalid_json', message: error.message, raw: text.slice(0, 500) };
      }
    }
    if (!response.ok) {
      const payload = typeof body === 'object' && body !== null ? body : {};
      return Object.assign({
        success: false,
        error: payload.error || 'upload_http_error',
        message: payload.message || payload.detail || response.statusText,
        status: response.status,
      }, payload);
    }
    return body;
  }

  async function uploadFiles(url, files, options) {
    const opts = options || {};
    const fileList = toArray(files);
    const batches = makeBatches(fileList, opts);
    const results = [];
    for (let index = 0; index < batches.length; index += 1) {
      const batch = batches[index];
      const formData = new FormData();
      batch.forEach(function (file) {
        formData.append(opts.fieldName || 'files', file, file.webkitRelativePath || file.name);
      });
      if (opts.extraFields) {
        Object.keys(opts.extraFields).forEach(function (key) {
          const value = opts.extraFields[key];
          if (Array.isArray(value)) {
            value.forEach(function (item) { formData.append(key, item); });
          } else {
            formData.append(key, value);
          }
        });
      }
      formData.append('batch_index', String(index + 1));
      formData.append('batch_total', String(batches.length));
      if (opts.onProgress) {
        opts.onProgress({ batch: index + 1, totalBatches: batches.length, files: batch.length, totalFiles: fileList.length });
      }
      const result = await uploadForm(url, formData, opts.fetchOptions);
      results.push(result);
      if (result && result.success === false && opts.stopOnError !== false) {
        return { success: false, error: result.error || 'upload_failed', message: result.message || result.error || 'Upload failed', results };
      }
    }
    return { success: true, results, batches: batches.length, files: fileList.length };
  }

  function summarizeError(error) {
    if (!error) return 'Unknown error';
    if (typeof error === 'string') return error;
    return error.message || error.detail || error.error || 'Upload failed';
  }

  window.KaguyaUpload = {
    makeBatches,
    uploadForm,
    uploadFiles,
    summarizeError,
  };
})();
