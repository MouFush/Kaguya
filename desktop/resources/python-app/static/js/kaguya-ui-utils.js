(function () {
  'use strict';

  const activeControllers = new Map();
  const lsSaveTimers = {};
  const originalFetch = window.fetch ? window.fetch.bind(window) : null;

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
    chevron.textContent = isCollapsing ? '▲' : '▼';
    btn.appendChild(chevron);
    btn.appendChild(document.createTextNode(isCollapsing ? '展开' : '折叠'));
    btn.title = isCollapsing ? '展开代码' : '折叠代码';
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
      chevron.textContent = '▼';
      foldBtn.appendChild(chevron);
      foldBtn.appendChild(document.createTextNode('折叠'));
      foldBtn.title = '折叠代码';
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
      btn.textContent = '已复制 ✓';
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
        if (!data.success) return window.showToast && window.showToast(data.error || data.message || '更新失败');
        if (cb) cb(data);
        else if (window.loadProjectCenter) window.loadProjectCenter();
      })
      .catch(function () { if (window.showToast) window.showToast('网络错误'); });
  }

  function crudDelete(endpoint, id, cb) {
    if (!confirm('确定删除?')) return;
    if (!window.KaguyaAPI) return window.showToast && window.showToast('API client unavailable');
    window.KaguyaAPI.del(`${endpoint}/${id}`)
      .then(function (data) {
        if (!data.success) return window.showToast && window.showToast(data.error || data.message || '删除失败');
        if (cb) cb(data);
        else if (window.loadProjectCenter) window.loadProjectCenter();
      })
      .catch(function () { if (window.showToast) window.showToast('网络错误'); });
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
    expandAllCodeBlocks,
    expandCodeFromHint,
    renderKpiCards,
    safeFetch,
    safeHighlight,
    saveToLS,
    toggleCodeFold,
  };

  Object.assign(window, window.KaguyaUIUtils);
})();
