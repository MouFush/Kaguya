(function () {
  'use strict';

  const activeControllers = new Map();
  const lsSaveTimers = {};
  const originalFetch = window.fetch ? window.fetch.bind(window) : null;
  const copyLabel = '\u590d\u5236';
  const copiedLabel = '\u5df2\u590d\u5236 \u2713';
  const expandLabel = '\u5c55\u5f00';
  const collapseLabel = '\u6298\u53e0';
  const expandTitle = '\u5c55\u5f00\u4ee3\u7801';
  const collapseTitle = '\u6298\u53e0\u4ee3\u7801';

  if (originalFetch && !window.__kaguyaFetchLogged) {
    window.fetch = function () {
      const args = arguments;
      return originalFetch.apply(window, args).catch(function (err) {
        console.warn('Fetch error:', args[0], err);
        throw err;
      });
    };
    window.__kaguyaFetchLogged = true;
  }

  function htmlEscape(value) {
    if (typeof window.escapeHtml === 'function') return window.escapeHtml(value);
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function esc(value) {
    return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function safeHighlight(root) {
    if (typeof hljs === 'undefined' || !root) return;
    root.querySelectorAll('pre code').forEach(function (block) {
      try {
        hljs.highlightElement(block);
      } catch (error) {
        console.warn('highlight failed:', error);
      }
    });
  }

  function setupMarkedRenderer() {
    if (typeof marked === 'undefined' || typeof hljs === 'undefined') return;
    const renderer = new marked.Renderer();
    renderer.del = function (text) { return text; };
    const foldThresholds = { default: 10, python: 12, javascript: 10, typescript: 10, json: 15, yaml: 12, html: 12, css: 10, sql: 12, bash: 8, shell: 8 };
    renderer.code = function (code, language) {
      const lang = (language || 'plaintext').toLowerCase();
      const codeStr = code || '';
      const lines = codeStr.split(String.fromCharCode(10));
      const lineCount = lines.length;
      let highlighted;
      try {
        highlighted = hljs.highlight(codeStr, { language: lang }).value;
      } catch (error) {
        highlighted = esc(codeStr);
      }
      const threshold = foldThresholds[lang] || foldThresholds.default;
      const isLong = lineCount > threshold;
      const codeId = 'cb_' + Math.random().toString(36).substr(2, 8);
      let foldStateClass = '';
      if (isLong) {
        try {
          if (localStorage.getItem('fold_' + lang + '_' + lineCount) === '1') foldStateClass = ' collapsed';
        } catch (error) {}
      }
      let headerActions = '<div class="code-actions">';
      if (isLong) {
        const isCollapsed = foldStateClass.indexOf('collapsed') >= 0;
        headerActions += '<button class="code-action-btn fold-btn' + (isCollapsed ? ' fold-active' : '') +
          '" onclick="toggleCodeFold(this)" title="' + (isCollapsed ? expandTitle : collapseTitle) +
          '"><span class="fold-chevron">v</span>' + (isCollapsed ? expandLabel : collapseLabel) + '</button>';
      }
      headerActions += '<button class="code-action-btn" onclick="copyCodeBlock(this)" title="' + copyLabel + '">' + copyLabel + '</button></div>';
      const foldSummary = isLong
        ? '<div class="code-fold-summary"><span class="summary-badge">' + lang + '</span><span>' + lineCount + ' lines, folded ' + (lineCount - 8) + '</span></div>'
        : '';
      const expandHint = isLong
        ? '<div class="code-expand-hint" onclick="expandCodeFromHint(this)"><span class="hint-chevron">v</span> ' + expandLabel + ' ' + lineCount + ' lines</div>'
        : '';
      return '<div class="code-block' + foldStateClass + '" data-lines="' + lineCount + '" data-lang="' + lang + '" id="' + codeId + '">' +
        '<div class="code-header"><span class="code-lang">' + lang + '</span><span class="code-line-count">' + lineCount + ' lines</span>' + headerActions + '</div>' +
        '<div class="code-body-wrapper"><pre><code class="hljs language-' + lang + '">' + highlighted + '</code></pre>' + expandHint + '</div>' +
        foldSummary + '</div>';
    };
    marked.setOptions({ renderer: renderer, breaks: true, gfm: true, mangle: false, headerIds: false });
  }

  function safeMarkedParse(content) {
    if (typeof marked !== 'undefined') {
      try {
        return marked.parse(content || '');
      } catch (error) {
        return content;
      }
    }
    return String(content || '').replace(/<\//g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
  }

  function toggleCodeFold(btn) {
    const block = btn.closest('.code-block');
    if (!block) return;
    const isCollapsing = !block.classList.contains('collapsed');
    block.classList.toggle('collapsed');
    btn.classList.toggle('fold-active', isCollapsing);
    let chevron = btn.querySelector('.fold-chevron');
    btn.innerHTML = '';
    if (!chevron) {
      chevron = document.createElement('span');
      chevron.className = 'fold-chevron';
    }
    chevron.textContent = isCollapsing ? '^' : 'v';
    btn.appendChild(chevron);
    btn.appendChild(document.createTextNode(isCollapsing ? expandLabel : collapseLabel));
    btn.title = isCollapsing ? expandTitle : collapseTitle;
    try {
      const lang = block.dataset.lang || block.querySelector('.code-lang');
      const langText = typeof lang === 'string' ? lang : (lang ? lang.textContent : '');
      localStorage.setItem('fold_' + langText + '_' + block.dataset.lines, isCollapsing ? '1' : '0');
    } catch (error) {}
  }

  function expandCodeFromHint(hint) {
    const block = hint.closest('.code-block');
    if (!block) return;
    block.classList.remove('collapsed');
    const foldBtn = block.querySelector('.fold-btn');
    if (foldBtn) {
      foldBtn.classList.remove('fold-active');
      let chevron = foldBtn.querySelector('.fold-chevron');
      foldBtn.innerHTML = '';
      if (!chevron) {
        chevron = document.createElement('span');
        chevron.className = 'fold-chevron';
      }
      chevron.textContent = 'v';
      foldBtn.appendChild(chevron);
      foldBtn.appendChild(document.createTextNode(collapseLabel));
      foldBtn.title = collapseTitle;
    }
    try {
      localStorage.setItem('fold_' + (block.dataset.lang || '') + '_' + block.dataset.lines, '0');
    } catch (error) {}
  }

  function collapseAllCodeBlocks() {
    document.querySelectorAll('.code-block:not(.collapsed)').forEach(function (block) {
      const foldBtn = block.querySelector('.fold-btn');
      if (foldBtn) toggleCodeFold(foldBtn);
    });
  }

  function expandAllCodeBlocks() {
    document.querySelectorAll('.code-block.collapsed').forEach(function (block) {
      const foldBtn = block.querySelector('.fold-btn');
      if (foldBtn) toggleCodeFold(foldBtn);
    });
  }

  function copyCodeBlock(btn) {
    const block = btn.closest('.code-block');
    if (!block) return;
    const code = block.querySelector('code');
    if (!code) return;
    const originalText = btn.textContent;
    navigator.clipboard.writeText(code.textContent).then(function () {
      btn.textContent = copiedLabel;
      btn.style.color = 'var(--success)';
      setTimeout(function () {
        btn.textContent = originalText;
        btn.style.color = '';
      }, 1500);
    }).catch(function () {});
  }

  function crudUpdate(endpoint, id, payload, cb) {
    if (!window.KaguyaAPI) return window.showToast && window.showToast('API client unavailable');
    window.KaguyaAPI.json(`${endpoint}/${id}/status`, payload)
      .then(function (data) {
        if (!data.success) return window.showToast && window.showToast(data.error || data.message || 'update_failed');
        if (cb) cb(data);
        else if (window.loadProjectCenter) window.loadProjectCenter();
      })
      .catch(function () { if (window.showToast) window.showToast('network_error'); });
  }

  function crudDelete(endpoint, id, cb) {
    if (!confirm('delete?')) return;
    if (!window.KaguyaAPI) return window.showToast && window.showToast('API client unavailable');
    window.KaguyaAPI.del(`${endpoint}/${id}`)
      .then(function (data) {
        if (!data.success) return window.showToast && window.showToast(data.error || data.message || 'delete_failed');
        if (cb) cb(data);
        else if (window.loadProjectCenter) window.loadProjectCenter();
      })
      .catch(function () { if (window.showToast) window.showToast('network_error'); });
  }

  function renderKpiCards(container, cards) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = (cards || []).map(function (card) {
      return '<div class="ops-kpi-card"><div class="ops-kpi-label">' +
        htmlEscape(card.label) + '</div><div class="ops-kpi-value">' +
        htmlEscape(String(card.value)) + '</div></div>';
    }).join('');
  }

  function saveToLS(key, data) {
    try {
      localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
      console.warn('LS save fail:', key, error);
    }
  }

  function debouncedSaveLS(key, data, ms) {
    clearTimeout(lsSaveTimers[key]);
    lsSaveTimers[key] = setTimeout(function () { saveToLS(key, data); }, ms == null ? 500 : ms);
  }

  function abortableFetch(key, url, opts) {
    if (!originalFetch) return Promise.reject(new Error('fetch_unavailable'));
    if (activeControllers.has(key)) activeControllers.get(key).abort();
    const ctrl = new AbortController();
    activeControllers.set(key, ctrl);
    const requestOptions = Object.assign({}, opts || {}, { signal: ctrl.signal });
    return window.fetch(url, requestOptions).finally(function () {
      activeControllers.delete(key);
    });
  }

  function safeFetch(url, opts) {
    if (!window.fetch) {
      return Promise.resolve({ json: function () { return Promise.resolve({ success: false, error: 'fetch_unavailable' }); } });
    }
    return window.fetch(url, opts || {}).catch(function (err) {
      console.warn('Fetch error:', url, err);
      return { json: function () { return Promise.resolve({ success: false, error: 'Network error' }); } };
    });
  }

  window.KaguyaUIUtils = {
    abortableFetch,
    collapseAllCodeBlocks,
    copyCodeBlock,
    crudDelete,
    crudUpdate,
    debouncedSaveLS,
    esc,
    expandAllCodeBlocks,
    expandCodeFromHint,
    renderKpiCards,
    safeFetch,
    safeHighlight,
    safeMarkedParse,
    saveToLS,
    setupMarkedRenderer,
    toggleCodeFold,
  };

  Object.assign(window, window.KaguyaUIUtils);
  setupMarkedRenderer();
})();
