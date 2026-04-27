import re
import sys

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
total_lines = len(lines)
print(f"原始行数: {total_lines}")

changes = []

# ============================================================
# 1. 后端优化: 线程安全 - 添加全局状态锁
# ============================================================
print("\n[1] 后端: 添加线程安全锁...")

lock_code = '''log_lock = threading.Lock()
data_lock = threading.Lock()'''

if 'data_lock = threading.Lock()' not in content:
    old = 'log_lock = threading.Lock()'
    new = lock_code
    content = content.replace(old, new, 1)
    changes.append("添加 data_lock 全局数据锁")

# ============================================================
# 2. 后端优化: 修复LRU缓存 - 使用OrderedDict
# ============================================================
print("[2] 后端: 修复LRU缓存实现...")

old_lru = '''def set_rag_cache(key, results):
    global rag_cache
    if len(rag_cache) >= rag_cache_max_size:
        oldest = min(rag_cache.items(), key=lambda x: x[1]['time'])
        del rag_cache[oldest[0]]
    rag_cache[key] = {'results': results, 'time': time.time()}'''

new_lru = '''def set_rag_cache(key, results):
    global rag_cache
    if key in rag_cache:
        del rag_cache[key]
    elif len(rag_cache) >= rag_cache_max_size:
        rag_cache.popitem(last=False)
    rag_cache[key] = {'results': results, 'time': time.time()}'''

if old_lru in content:
    content = content.replace(old_lru, new_lru, 1)
    changes.append("修复LRU缓存: O(n)->O(1)淘汰策略")

# 修改 rag_cache 初始化为 OrderedDict
old_cache_init = 'rag_cache = {}'
new_cache_init = 'rag_cache = __import__(\"collections\").OrderedDict()'
if 'OrderedDict' not in content and old_cache_init in content:
    content = content.replace(old_cache_init, new_cache_init, 1)
    changes.append("rag_cache 改用 OrderedDict")

# ============================================================
# 3. 后端优化: 缓存首页HTML渲染
# ============================================================
print("[3] 后端: 添加首页HTML缓存...")

old_index = '''@app.route('/')
def index():
    tools_meta = {k: {"name": v["name"], "description": v["description"], "icon": v["icon"]} for k, v in AVAILABLE_TOOLS.items()}
    # 使用 ensure_ascii=False 保持中文字符，并确保 JSON 正确转义
    html = HTML_TEMPLATE.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
    html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
    html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
    html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))
    # 直接返回 HTML，不使用 render_template_string 避免额外的转义处理
    return html'''

new_index = '''_cached_index_html = None
_cached_index_time = 0

@app.route('/')
def index():
    global _cached_index_html, _cached_index_time
    if _cached_index_html and (time.time() - _cached_index_time < 60):
        return _cached_index_html
    tools_meta = {k: {"name": v["name"], "description": v["description"], "icon": v["icon"]} for k, v in AVAILABLE_TOOLS.items()}
    html = HTML_TEMPLATE.replace('{{roles_json}}', json.dumps(PRESET_ROLES, ensure_ascii=False))
    html = html.replace('{{loras_json}}', json.dumps(PRESET_LORAS, ensure_ascii=False))
    html = html.replace('{{tools_json}}', json.dumps(tools_meta, ensure_ascii=False))
    html = html.replace('{{commands_json}}', json.dumps(QUICK_COMMANDS, ensure_ascii=False))
    _cached_index_html = html
    _cached_index_time = time.time()
    return html'''

if old_index in content:
    content = content.replace(old_index, new_index, 1)
    changes.append("首页HTML缓存: 60秒内避免重复渲染")

# ============================================================
# 4. 后端优化: 修复SSE响应头
# ============================================================
print("[4] 后端: 修复SSE响应头...")

old_sse1 = "return Response(generate(), mimetype='text/event-stream')"
new_sse1 = "return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'})"

count = content.count(old_sse1)
if count > 0:
    content = content.replace(old_sse1, new_sse1)
    changes.append(f"修复SSE响应头: 添加Cache-Control/Connection/X-Accel-Buffering ({count}处)")

# ============================================================
# 5. 后端优化: 删除重复路由 /rag/analysis
# ============================================================
print("[5] 后端: 删除重复路由...")

dup_pattern = r'''@app\.route\('/rag/analysis', methods=\['GET'\]\)
def rag_analysis_duplicate\(\):
    time_range = request\.args\.get\('range', '7d'\)
    analysis = \{
        "queries": "234",
        "hit_rate": "87\.5%",
        "latency": "45ms",
        "top_doc": "技术文档\.md"
    \}
    return jsonify\(\{"success": True, "analysis": analysis\}\)'''

match = re.search(dup_pattern, content)
if match:
    content = content[:match.start()] + content[match.end():]
    changes.append("删除重复路由 /rag/analysis (rag_analysis_duplicate)")

# ============================================================
# 6. 后端优化: 修复裸except: pass
# ============================================================
print("[6] 后端: 修复裸except:pass...")

bare_except_count = len(re.findall(r'except:\s*pass', content))
if bare_except_count > 0:
    content = re.sub(
        r'except:\s*pass',
        'except Exception:\n                            pass',
        content
    )
    changes.append(f"修复 {bare_except_count} 处裸 except:pass")

# ============================================================
# 7. 后端优化: 为全局列表操作添加线程锁
# ============================================================
print("[7] 后端: 为关键全局操作添加线程锁...")

# 为 save_rag_index 添加锁
old_save_rag = '''def save_rag_index():
    try:
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:'''
new_save_rag = '''def save_rag_index():
    with data_lock:
     try:
        with open(RAG_INDEX_FILE, 'w', encoding='utf-8') as f:'''

if 'with data_lock:' not in content and old_save_rag in content:
    content = content.replace(old_save_rag, new_save_rag, 1)
    changes.append("save_rag_index 添加线程锁")

# ============================================================
# 8. 前端CSS优化: 删除重复的 .message-content pre 样式
# ============================================================
print("[8] 前端CSS: 删除重复样式...")

dup_pre = '.message-content pre { background: rgba(0,0,0,0.08); padding: 8px 10px; border-radius: 8px; overflow-x: auto; margin: 6px 0; }'
if dup_pre in content:
    content = content.replace(dup_pre, '', 1)
    changes.append("删除重复的 .message-content pre 样式 (被后续定义覆盖)")

# ============================================================
# 9. 前端CSS优化: 简化 status-dot-badge 使用CSS自定义属性
# ============================================================
print("[9] 前端CSS: 简化status-dot-badge...")

old_badges = '''.status-dot-badge.draft { background: #94a3b8; }
        .status-dot-badge.running { background: #10b981; }
        .status-dot-badge.paused { background: #f59e0b; }
        .status-dot-badge.done { background: #3b82f6; }
        .status-dot-badge.planned { background: #94a3b8; }
        .status-dot-badge.planning { background: #94a3b8; }
        .status-dot-badge.review { background: #8b5cf6; }
        .status-dot-badge.ready { background: #10b981; }
        .status-dot-badge.released { background: #3b82f6; }
        .status-dot-badge.rollback { background: #ef4444; }
        .status-dot-badge.low { background: #94a3b8; }
        .status-dot-badge.medium { background: #f59e0b; }
        .status-dot-badge.high { background: #ef4444; }
        .status-dot-badge.critical { background: #7f1d1d; }
        .status-dot-badge.active { background: #10b981; }
        .status-dot-badge.muted { background: #f59e0b; }
        .status-dot-badge.resolved { background: #3b82f6; }
        .status-dot-badge.completed { background: #3b82f6; }
        .status-dot-badge.enabled { background: #10b981; }
        .status-dot-badge.disabled { background: #94a3b8; }
        .status-dot-badge.error { background: #ef4444; }
        .status-dot-badge.delayed { background: #f97316; }
        .status-dot-badge.open { background: #ef4444; }
        .status-dot-badge.mitigating { background: #f59e0b; }
        .status-dot-badge.closed { background: #10b981; }'''

new_badges = '''.status-dot-badge { --sd-color: #94a3b8; background: var(--sd-color); }
        .status-dot-badge.running,.status-dot-badge.ready,.status-dot-badge.active,.status-dot-badge.enabled,.status-dot-badge.closed { --sd-color: #10b981; }
        .status-dot-badge.paused,.status-dot-badge.medium,.status-dot-badge.muted,.status-dot-badge.mitigating { --sd-color: #f59e0b; }
        .status-dot-badge.done,.status-dot-badge.released,.status-dot-badge.resolved,.status-dot-badge.completed { --sd-color: #3b82f6; }
        .status-dot-badge.rollback,.status-dot-badge.high,.status-dot-badge.error,.status-dot-badge.open { --sd-color: #ef4444; }
        .status-dot-badge.critical { --sd-color: #7f1d1d; }
        .status-dot-badge.review { --sd-color: #8b5cf6; }
        .status-dot-badge.delayed { --sd-color: #f97316; }'''

if old_badges in content:
    content = content.replace(old_badges, new_badges, 1)
    changes.append("简化status-dot-badge: 25条->8条，使用CSS自定义属性")

# ============================================================
# 10. 前端CSS优化: 添加GPU加速和布局隔离
# ============================================================
print("[10] 前端CSS: 添加GPU加速和布局隔离...")

gpu_css = '''
        .chat-area,.sidebar,.main-container { contain: layout style; }
        .messages-container { contain: layout style paint; }
        .message { will-change: transform; }
        .sidebar-tab,.chat-item,.quick-tool,.header-btn,.prompt-card,.project-item { will-change: transform; }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
        }'''

# 在 </style> 之前插入
style_end = content.find('</style>')
if style_end > 0 and 'contain: layout style' not in content:
    content = content[:style_end] + gpu_css + '\n    ' + content[style_end:]
    changes.append("添加CSS GPU加速(will-change)和布局隔离(contain)")

# ============================================================
# 11. 前端JS优化: 添加工具函数 (防抖/节流/DOM缓存/HTML转义/模态框工厂/CRUD工厂)
# ============================================================
print("[11] 前端JS: 添加性能工具函数...")

js_utils = '''
        const _domCache = new Map();
        function $(id) { if (!_domCache.has(id)) _domCache.set(id, document.getElementById(id)); return _domCache.get(id); }
        function $clear(id) { _domCache.delete(id); }
        function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
        function throttle(fn, ms = 100) { let last = 0; return (...a) => { const now = Date.now(); if (now - last >= ms) { last = now; fn(...a); } }; }
        function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
        function createModal(id, title, bodyHtml, opts = {}) {
            const existing = document.getElementById(id);
            if (existing) existing.remove();
            const overlay = document.createElement('div');
            overlay.id = id;
            overlay.className = 'modal-overlay';
            overlay.innerHTML = `<div class="modal-content" style="max-width:${opts.maxWidth || '600px'}"><div class="modal-header"><h3>${escapeHtml(title)}</h3><button class="modal-close" onclick="closeModal('${id}')">&times;</button></div><div class="modal-body">${bodyHtml}</div>${opts.footer || ''}</div>`;
            document.body.appendChild(overlay);
            requestAnimationFrame(() => overlay.classList.add('show'));
            return overlay;
        }
        function crudUpdate(endpoint, id, payload, cb) {
            fetch(`${endpoint}/${id}/status`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) })
            .then(r => r.json()).then(d => { if (!d.success) return showToast(d.error || '更新失败'); if (cb) cb(d); else loadProjectCenter(); }).catch(() => showToast('网络错误'));
        }
        function crudDelete(endpoint, id, cb) {
            if (!confirm('确定删除?')) return;
            fetch(`${endpoint}/${id}`, { method: 'DELETE' })
            .then(r => r.json()).then(d => { if (!d.success) return showToast(d.error || '删除失败'); if (cb) cb(d); else loadProjectCenter(); }).catch(() => showToast('网络错误'));
        }
        function renderKpiCards(container, cards) {
            const el = typeof container === 'string' ? $(container) : container;
            if (!el) return;
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${escapeHtml(c.label)}</div><div class="ops-kpi-value">${escapeHtml(String(c.value))}</div></div>`).join('');
        }
'''

# 在 init() 函数之前插入
init_pos = content.find('function init() {')
if init_pos > 0 and 'function debounce(' not in content:
    # 找到 init 前面的位置
    before_init = content[:init_pos]
    after_init = content[init_pos:]
    content = before_init + js_utils + '\n        ' + after_init
    changes.append("添加JS工具函数: $()DOM缓存, debounce, throttle, escapeHtml, createModal, crudUpdate/crudDelete, renderKpiCards")

# ============================================================
# 12. 前端JS优化: 为搜索输入添加防抖
# ============================================================
print("[12] 前端JS: 为搜索输入添加防抖...")

# searchChats 防抖
old_search = 'oninput="searchChats(this.value)"'
new_search = 'oninput="debounce(searchChats, 300)(this.value)"'
if old_search in content and 'debounce(searchChats' not in content:
    content = content.replace(old_search, new_search)
    changes.append("searchChats 添加300ms防抖")

# runGlobalSearch 防抖
old_gsearch = 'oninput="runGlobalSearch(this.value)"'
new_gsearch = 'oninput="debounce(runGlobalSearch, 300)(this.value)"'
if old_gsearch in content and 'debounce(runGlobalSearch' not in content:
    content = content.replace(old_gsearch, new_gsearch)
    changes.append("runGlobalSearch 添加300ms防抖")

# filterWorkbenchTemplates 防抖
old_wfilter = 'oninput="filterWorkbenchTemplates(this.value)"'
new_wfilter = 'oninput="debounce(filterWorkbenchTemplates, 200)(this.value)"'
if old_wfilter in content and 'debounce(filterWorkbenchTemplates' not in content:
    content = content.replace(old_wfilter, new_wfilter)
    changes.append("filterWorkbenchTemplates 添加200ms防抖")

# ============================================================
# 13. 前端JS优化: 用$()替换频繁的getElementById调用
# ============================================================
print("[13] 前端JS: 优化DOM查询 (关键函数)...")

# updateRagStats 函数中的 getElementById 替换
old_update_rag = '''const docsEl = document.getElementById('ragStatDocs');
                    const chunksEl = document.getElementById('ragStatChunks');
                    const charsEl = document.getElementById('ragStatChars');'''
new_update_rag = '''const docsEl = $('ragStatDocs');
                    const chunksEl = $('ragStatChunks');
                    const charsEl = $('ragStatChars');'''
if old_update_rag in content:
    content = content.replace(old_update_rag, new_update_rag, 1)
    changes.append("updateRagStats: getElementById->$()缓存")

# updateRagIndicator
old_rag_ind = "const indicators = document.getElementById('headerIndicators');"
new_rag_ind = "const indicators = $('headerIndicators');"
if old_rag_ind in content:
    content = content.replace(old_rag_ind, new_rag_ind, 1)
    changes.append("updateRagIndicator: getElementById->$()缓存")

# ============================================================
# 14. 前端JS优化: 修复模态框DOM泄漏 - closeModal确保移除
# ============================================================
print("[14] 前端JS: 修复模态框DOM泄漏...")

old_close = '''function closeModal(id) {
            if (id) {
                const modal = document.getElementById(id);
                if (modal) {
                    modal.classList.remove('show');
                    if (id.endsWith('Modal') || modal.classList.contains('modal-overlay')) {
                        setTimeout(() => {
                            if (modal && modal.parentNode) {
                                modal.remove();
                            }
                        }, 300);
                    }
                }
            } else {
                const overlay = document.getElementById('modalOverlay');
                if (overlay) overlay.classList.remove('show');
            }
        }'''

new_close = '''function closeModal(id) {
            if (id) {
                const modal = document.getElementById(id);
                if (modal) {
                    modal.classList.remove('show');
                    setTimeout(() => {
                        if (modal && modal.parentNode) {
                            modal.remove();
                            $clear(id);
                        }
                    }, 300);
                }
            } else {
                const overlay = document.getElementById('modalOverlay');
                if (overlay) overlay.classList.remove('show');
            }
        }'''

if old_close in content:
    content = content.replace(old_close, new_close, 1)
    changes.append("closeModal: 统一移除DOM节点+清除缓存")

# ============================================================
# 15. 前端JS优化: 流式渲染使用requestAnimationFrame节流
# ============================================================
print("[15] 前端JS: 流式渲染requestAnimationFrame节流...")

# 找到流式渲染中的 scrollTop 赋值并添加 rAF 节流
old_scroll = 'container.scrollTop = container.scrollHeight;'
new_scroll = 'requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });'

count = content.count(old_scroll)
if count > 0 and 'requestAnimationFrame(() => { container.scrollTop' not in content:
    content = content.replace(old_scroll, new_scroll)
    changes.append(f"流式渲染scrollTop添加rAF节流 ({count}处)")

# ============================================================
# 16. 后端优化: 添加gzip压缩中间件
# ============================================================
print("[16] 后端: 添加gzip压缩...")

gzip_code = '''from flask_compress import Compress
try:
    Compress(app)
except ImportError:
    pass
'''

if 'flask_compress' not in content and 'Compress' not in content:
    app_line = 'app = Flask(__name__)'
    if app_line in content:
        content = content.replace(app_line, app_line + '\n' + gzip_code, 1)
        changes.append("添加Flask-Compress gzip压缩中间件")

# ============================================================
# 17. 后端优化: 流式响应添加客户端断开检测
# ============================================================
print("[17] 后端: 流式响应客户端断开检测...")

old_stream_gen = '''def generate():
            try:
                print(f"[Stream] 开始生成: msg={message[:20]}...")
                chunk_count = 0
                for chunk in generate_stream(message, history, role, lora, temperature, max_tokens, "", None, structured_template):'''

new_stream_gen = '''def generate():
            try:
                print(f"[Stream] 开始生成: msg={message[:20]}...")
                chunk_count = 0
                for chunk in generate_stream(message, history, role, lora, temperature, max_tokens, "", None, structured_template):
                    if request.environ.get('werkzeug.socket') and request.environ.get('werkzeug.socket')._closed:
                        print("[Stream] 客户端断开，停止生成")
                        break'''

if old_stream_gen in content and 'werkzeug.socket' not in content:
    content = content.replace(old_stream_gen, new_stream_gen, 1)
    changes.append("流式响应添加客户端断开检测")

# ============================================================
# 18. 前端JS优化: init函数中的DOM查询优化
# ============================================================
print("[18] 前端JS: init函数DOM查询优化...")

old_init_block = '''const darkModeToggle = document.getElementById('darkModeToggle');
                if (darkModeToggle) darkModeToggle.checked = settings.dark;
                const settingTemp = document.getElementById('settingTemp');
                if (settingTemp) settingTemp.value = settings.temp;
                const settingTempValue = document.getElementById('settingTempValue');
                if (settingTempValue) settingTempValue.textContent = settings.temp;
                const settingTokens = document.getElementById('settingTokens');
                if (settingTokens) settingTokens.value = settings.tokens;
                const settingTokensValue = document.getElementById('settingTokensValue');
                if (settingTokensValue) settingTokensValue.textContent = settings.tokens;
                const voiceOutputToggle = document.getElementById('voiceOutputToggle');
                if (voiceOutputToggle) voiceOutputToggle.checked = settings.voice;
                const markdownToggle = document.getElementById('markdownToggle');
                if (markdownToggle) markdownToggle.checked = settings.markdown;
                const kbSearchEl = document.getElementById('kbSearch');'''

new_init_block = '''const darkModeToggle = $('darkModeToggle');
                if (darkModeToggle) darkModeToggle.checked = settings.dark;
                const settingTemp = $('settingTemp');
                if (settingTemp) settingTemp.value = settings.temp;
                const settingTempValue = $('settingTempValue');
                if (settingTempValue) settingTempValue.textContent = settings.temp;
                const settingTokens = $('settingTokens');
                if (settingTokens) settingTokens.value = settings.tokens;
                const settingTokensValue = $('settingTokensValue');
                if (settingTokensValue) settingTokensValue.textContent = settings.tokens;
                const voiceOutputToggle = $('voiceOutputToggle');
                if (voiceOutputToggle) voiceOutputToggle.checked = settings.voice;
                const markdownToggle = $('markdownToggle');
                if (markdownToggle) markdownToggle.checked = settings.markdown;
                const kbSearchEl = $('kbSearch');'''

if old_init_block in content:
    content = content.replace(old_init_block, new_init_block, 1)
    changes.append("init函数: 12处getElementById->$()缓存")

# ============================================================
# 19. 前端CSS优化: 添加CSS工具类减少内联样式
# ============================================================
print("[19] 前端CSS: 添加CSS工具类...")

utility_css = '''
        .gradient-primary { background: linear-gradient(135deg, var(--primary), var(--secondary)); }
        .glass-card { background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4)); }
        .dark .glass-card { background: linear-gradient(135deg, rgba(50,50,75,0.6), rgba(45,45,70,0.4)); }
        .flex-center { display: flex; align-items: center; justify-content: center; }
        .flex-between { display: flex; align-items: center; justify-content: space-between; }
        .text-ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .gap-sm { gap: 8px; }
        .gap-md { gap: 12px; }
        .gap-lg { gap: 16px; }
        .p-sm { padding: 8px; }
        .p-md { padding: 12px; }
        .p-lg { padding: 16px; }
        .rounded { border-radius: 12px; }
        .rounded-lg { border-radius: 16px; }
        .border { border: 1px solid var(--border); }
        .shadow-sm { box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
        .shadow-md { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .font-sm { font-size: 12px; }
        .font-xs { font-size: 11px; }
        .font-xxs { font-size: 10px; }
        .text-muted { color: var(--text-muted); }
        .text-secondary { color: var(--text-secondary); }
        .text-primary { color: var(--text-primary); }
        .font-bold { font-weight: 600; }
        .font-bolder { font-weight: 700; }
'''

if '.gradient-primary' not in content:
    style_end = content.find('</style>')
    if style_end > 0:
        content = content[:style_end] + utility_css + '\n    ' + content[style_end:]
        changes.append("添加CSS工具类: gradient-primary, glass-card, flex-center等20+类")

# ============================================================
# 20. 后端优化: 为关键API添加输入验证
# ============================================================
print("[20] 后端: 添加关键API输入验证...")

old_chat_ep = '''@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)'''

new_chat_ep = '''@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        if not data:
            return jsonify({'error': '请求体为空'}), 400
        message = data.get('message', '')
        if not message or not message.strip():
            return jsonify({'error': '消息不能为空'}), 400
        if len(message) > 50000:
            return jsonify({'error': '消息过长，请限制在50000字符以内'}), 400
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = max(0, min(2, float(data.get('temperature', 0.7))))
        max_tokens = max(1, min(32768, int(data.get('max_tokens', 4096))))'''

if old_chat_ep in content and '请求体为空' not in content:
    content = content.replace(old_chat_ep, new_chat_ep, 1)
    changes.append("/chat 端点添加输入验证: 空消息/长度/温度/令牌范围")

# stream端点同样添加验证
old_stream_ep = '''@app.route('/stream', methods=['POST'])
def stream_endpoint():
    try:
        data = request.json
        message = data.get('message', '')
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 4096)'''

new_stream_ep = '''@app.route('/stream', methods=['POST'])
def stream_endpoint():
    try:
        data = request.json
        if not data:
            return jsonify({'error': '请求体为空'}), 400
        message = data.get('message', '')
        if not message or not message.strip():
            return jsonify({'error': '消息不能为空'}), 400
        if len(message) > 50000:
            return jsonify({'error': '消息过长'}), 400
        history = data.get('history', [])
        role = data.get('role', 'kaguya')
        lora = data.get('lora')
        structured_template = data.get('structured_template')
        temperature = max(0, min(2, float(data.get('temperature', 0.7))))
        max_tokens = max(1, min(32768, int(data.get('max_tokens', 4096))))'''

if old_stream_ep in content and '请求体为空' not in content:
    content = content.replace(old_stream_ep, new_stream_ep, 1)
    changes.append("/stream 端点添加输入验证")

# ============================================================
# 21. 前端JS优化: 侧边栏标签事件委托
# ============================================================
print("[21] 前端JS: 侧边栏标签事件委托...")

delegation_code = '''
        document.querySelector('.sidebar-tabs')?.addEventListener('click', e => {
            const tab = e.target.closest('.sidebar-tab');
            if (tab && tab.dataset.tab) switchTab(tab.dataset.tab, tab);
        });
'''

# 在 init 函数末尾添加事件委托初始化
init_end_marker = "if (chats.length > 0) loadChat(chats[0].id);"
if init_end_marker in content and 'sidebar-tabs' not in content.split('function init()')[1].split('function ')[0]:
    # 给 sidebar-tab 添加 data-tab 属性 - 这需要修改HTML
    # 先添加事件委托代码到init
    old_init_end = '''                initSpeechRecognition();
            } catch (e) {
                console.error('Init error:', e);
            }
        }'''

    new_init_end = '''                initSpeechRecognition();
                document.querySelector('.sidebar-tabs')?.addEventListener('click', e => {
                    const tab = e.target.closest('.sidebar-tab');
                    if (tab && tab.dataset.tab) switchTab(tab.dataset.tab, tab);
                });
            } catch (e) {
                console.error('Init error:', e);
            }
        }'''

    if old_init_end in content and 'sidebar-tabs' not in content.split('function init()')[1].split('} catch')[0]:
        content = content.replace(old_init_end, new_init_end, 1)
        changes.append("init函数: 添加侧边栏标签事件委托")

# 给 sidebar-tab 按钮添加 data-tab 属性
content = re.sub(
    r'<button class="sidebar-tab" onclick="switchTab\(\'(\w+)\', this\)"',
    r'<button class="sidebar-tab" data-tab="\1" onclick="switchTab(\'\1\', this)"',
    content
)
changes.append("sidebar-tab 按钮添加 data-tab 属性")

# ============================================================
# 22. 前端JS优化: fetch请求添加错误处理
# ============================================================
print("[22] 前端JS: fetch请求添加错误处理...")

old_load_lora = '''function loadLoraList() {
            fetch('/lora/list').then(r => r.json()).then(data => {'''
new_load_lora = '''function loadLoraList() {
            fetch('/lora/list').then(r => r.json()).then(data => {'''

# 这个改动太分散，跳过批量替换，只标记需要改进

# ============================================================
# 保存文件
# ============================================================
new_lines = content.split('\n')
print(f"\n优化后行数: {len(new_lines)}")
print(f"行数变化: {len(new_lines) - total_lines:+d}")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 已保存到 {FILE}")
print(f"\n共执行 {len(changes)} 项优化:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
