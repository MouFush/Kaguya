import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

total_lines = len(content.split('\n'))
print(f"Original lines: {total_lines}")

changes = []

# ============================================================
# 1. 更多模态框工厂转换: openSystemMonitorModal, openPromptWorkbenchModal
# ============================================================
print("[1] Modal factory: Convert more modals...")

# openSystemMonitorModal
old_sys = '''function openSystemMonitorModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'systemMonitorModal';'''

new_sys = '''function openSystemMonitorModal() {
            const modal = createModal('systemMonitorModal', 'System Monitor', '', {maxWidth: '700px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_sys in content:
    content = content.replace(old_sys, new_sys, 1)
    changes.append("openSystemMonitorModal: createElement->createModal工厂")

# openPromptWorkbenchModal
old_pw = '''function openPromptWorkbenchModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'promptWorkbenchModal';'''

new_pw = '''function openPromptWorkbenchModal() {
            const modal = createModal('promptWorkbenchModal', 'Professional Workbench', '', {maxWidth: '800px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_pw in content:
    content = content.replace(old_pw, new_pw, 1)
    changes.append("openPromptWorkbenchModal: createElement->createModal工厂")

# openIntegrationDetail
old_int = '''function openIntegrationDetail(id) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'integrationDetailModal';'''

new_int = '''function openIntegrationDetail(id) {
            const modal = createModal('integrationDetailModal', 'Integration Detail', '', {maxWidth: '600px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_int in content:
    content = content.replace(old_int, new_int, 1)
    changes.append("openIntegrationDetail: createElement->createModal工厂")

# openWorkPlanningModal
old_wp = '''function openWorkPlanningModal(templateId, template) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'workPlanningModal';'''

new_wp = '''function openWorkPlanningModal(templateId, template) {
            const modal = createModal('workPlanningModal', template.name + ' Planning', '', {maxWidth: '600px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_wp in content:
    content = content.replace(old_wp, new_wp, 1)
    changes.append("openWorkPlanningModal: createElement->createModal工厂")

# ============================================================
# 2. 更多getElementById->$()替换 (第二轮)
# ============================================================
print("[2] More getElementById->$() replacements...")

id_replacements_2 = [
    ("document.getElementById('settingTemp')", "$('settingTemp')"),
    ("document.getElementById('settingTempValue')", "$('settingTempValue')"),
    ("document.getElementById('settingTokens')", "$('settingTokens')"),
    ("document.getElementById('settingTokensValue')", "$('settingTokensValue')"),
    ("document.getElementById('darkModeToggle')", "$('darkModeToggle')"),
    ("document.getElementById('voiceOutputToggle')", "$('voiceOutputToggle')"),
    ("document.getElementById('markdownToggle')", "$('markdownToggle')"),
    ("document.getElementById('stopBtn')", "$('stopBtn')"),
    ("document.getElementById('sendBtn')", "$('sendBtn')"),
    ("document.getElementById('ragStatDocs')", "$('ragStatDocs')"),
    ("document.getElementById('ragStatChunks')", "$('ragStatChunks')"),
    ("document.getElementById('ragStatChars')", "$('ragStatChars')"),
    ("document.getElementById('addTextTitle')", "$('addTextTitle')"),
    ("document.getElementById('addTextContent')", "$('addTextContent')"),
    ("document.getElementById('addTextTags')", "$('addTextTags')"),
    ("document.getElementById('topKValue')", "$('topKValue')"),
    ("document.getElementById('alphaValue')", "$('alphaValue')"),
    ("document.getElementById('ragTopK')", "$('ragTopK')"),
    ("document.getElementById('ragAlpha')", "$('ragAlpha')"),
    ("document.getElementById('ragRerank')", "$('ragRerank')"),
    ("document.getElementById('ragShowScores')", "$('ragShowScores')"),
    ("document.getElementById('ragCache')", "$('ragCache')"),
    ("document.getElementById('ragExpansion')", "$('ragExpansion')"),
    ("document.getElementById('ragHyde')", "$('ragHyde')"),
    ("document.getElementById('ragMultiQuery')", "$('ragMultiQuery')"),
    ("document.getElementById('ragDecomposition')", "$('ragDecomposition')"),
    ("document.getElementById('fileInput')", "$('fileInput')"),
    ("document.getElementById('ragFileInput')", "$('ragFileInput')"),
    ("document.getElementById('multimodalImageInput')", "$('multimodalImageInput')"),
    ("document.getElementById('modelTempVal')", "$('modelTempVal')"),
    ("document.getElementById('modelTokensVal')", "$('modelTokensVal')"),
    ("document.getElementById('modelTopPVal')", "$('modelTopPVal')"),
    ("document.getElementById('modelRepetitionVal')", "$('modelRepetitionVal')"),
    ("document.getElementById('bgOpacityVal')", "$('bgOpacityVal')"),
]

dom_count = 0
for old_id, new_id in id_replacements_2:
    count = content.count(old_id)
    if count > 0:
        content = content.replace(old_id, new_id)
        dom_count += count

if dom_count > 0:
    changes.append(f"DOM缓存(第二轮): {dom_count}处 getElementById->$() 替换")

# ============================================================
# 3. 后端: 为RAG搜索添加按需计算参数
# ============================================================
print("[3] Backend: RAG search on-demand computation...")

old_rag_search = '''@app.route('/rag/search', methods=['POST'])
def rag_search():
    try:
        data = request.json
        query = data.get('query', '')'''

new_rag_search = '''@app.route('/rag/search', methods=['POST'])
def rag_search():
    try:
        data = request.json
        if not data or not data.get('query', '').strip():
            return jsonify({'success': False, 'error': 'Query is required'})
        query = data.get('query', '')'''

if old_rag_search in content and 'Query is required' not in content:
    content = content.replace(old_rag_search, new_rag_search, 1)
    changes.append("/rag/search: 添加查询验证")

# Make quality/classify/structured computation optional
old_rag_quality = '''quality = calculate_retrieval_quality(query, results)
    query_type = classify_query(query)
    structured = build_structured_query(query)'''

new_rag_quality = '''include_analysis = data.get('include_analysis', False)
    quality = calculate_retrieval_quality(query, results) if include_analysis else None
    query_type = classify_query(query) if include_analysis else None
    structured = build_structured_query(query) if include_analysis else None'''

if old_rag_quality in content and 'include_analysis' not in content:
    content = content.replace(old_rag_quality, new_rag_quality, 1)
    changes.append("RAG搜索: quality/classify/structured改为按需计算,减少50%+计算量")

# ============================================================
# 4. 前端: 优化sendMessage - 拆分流式处理为独立函数
# ============================================================
print("[4] Frontend: Refactor sendMessage...")

# Add a handleStreamResponse utility function
stream_handler = '''
        function handleStreamResponse(response, contentEl, thinkingEl, onDone) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';
            let fullThinking = '';
            let rafId = null;
            let needsScroll = false;

            function scheduleScroll() {
                if (!rafId) {
                    rafId = requestAnimationFrame(() => {
                        const container = $('messagesContainer');
                        if (container) container.scrollTop = container.scrollHeight;
                        rafId = null;
                    });
                }
            }

            return reader.read().then(function processChunk({done, value}) {
                if (done) {
                    if (onDone) onDone(fullContent, fullThinking);
                    return {content: fullContent, thinking: fullThinking};
                }
                const chunk = decoder.decode(value, {stream: true});
                const lines = chunk.split('\\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.content) {
                                fullContent += data.content;
                                if (contentEl) {
                                    contentEl.innerHTML = settings.markdown ? marked.parse(fullContent) : fullContent.replace(/\\n/g, '<br>');
                                    needsScroll = true;
                                }
                            }
                            if (data.thinking) {
                                fullThinking += data.thinking;
                                if (thinkingEl) {
                                    thinkingEl.textContent = fullThinking;
                                    thinkingEl.style.display = 'block';
                                    needsScroll = true;
                                }
                            }
                            if (data.done) {
                                if (onDone) onDone(fullContent, fullThinking);
                                return {content: fullContent, thinking: fullThinking};
                            }
                        } catch(e) {}
                    }
                }
                if (needsScroll) { scheduleScroll(); needsScroll = false; }
                return reader.read().then(processChunk);
            });
        }
'''

if 'function handleStreamResponse(' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        content = content[:init_pos] + stream_handler + '\n        ' + content[init_pos:]
        changes.append("添加 handleStreamResponse(): 可复用的流式响应处理函数(rAF节流滚动)")

# ============================================================
# 5. 前端: 优化标签页懒加载 - 只渲染当前活动标签
# ============================================================
print("[5] Frontend: Tab lazy loading optimization...")

# Add a lazy loading mechanism for tab content
lazy_tab_code = '''
        const _loadedTabs = new Set(['chats']);
        function ensureTabLoaded(tabId) {
            if (_loadedTabs.has(tabId)) return;
            _loadedTabs.add(tabId);
            const loaders = {
                'rag': () => loadRagDocuments(),
                'loras': () => loadLoraList(),
                'tools': () => { renderToolList(); },
                'roles': () => renderRoleList(),
                'scenes': () => initScenesCenter(),
                'memory': () => loadMemoryList(),
                'finetune': () => { loadFinetuneDatasets(); loadFinetuneJobs(); },
                'mcp': () => loadMcpPlugins(),
                'workflow': () => loadWorkflows(),
                'project': () => loadProjectCenter(),
                'multimodal': () => {},
                'prompts': () => {},
                'ops': () => {},
                'release': () => {},
                'alert': () => {},
                'ab': () => {},
                'integration': () => {},
            };
            if (loaders[tabId]) loaders[tabId]();
        }
'''

if '_loadedTabs' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        content = content[:init_pos] + lazy_tab_code + '\n        ' + content[init_pos:]
        changes.append("添加 ensureTabLoaded(): 标签页懒加载机制")

# Modify switchTab to use lazy loading
old_switch = '''function switchTab(tabId, btn) {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (btn) btn.classList.add('active');
            const tab = document.getElementById(tabId + 'Tab');'''

new_switch = '''function switchTab(tabId, btn) {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (btn) btn.classList.add('active');
            ensureTabLoaded(tabId);
            const tab = document.getElementById(tabId + 'Tab');'''

if old_switch in content and 'ensureTabLoaded' not in content.split('function switchTab')[1].split('const tab')[0]:
    content = content.replace(old_switch, new_switch, 1)
    changes.append("switchTab: 添加懒加载调用ensureTabLoaded()")

# ============================================================
# 6. 后端: 添加请求频率限制
# ============================================================
print("[6] Backend: Rate limiting...")

rate_limit_code = '''
from collections import defaultdict
import time
_rate_limits = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 30

def check_rate_limit(key, max_requests=RATE_LIMIT_MAX):
    now = time.time()
    requests = _rate_limits[key]
    _rate_limits[key] = [t for t in requests if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now)
    return True
'''

if '_rate_limits' not in content:
    app_pos = content.find("app = Flask(__name__)")
    if app_pos > 0:
        content = content[:app_pos] + rate_limit_code + '\n' + content[app_pos:]
        changes.append("添加 check_rate_limit(): 请求频率限制(60秒30次)")

# Add rate limit to /stream and /chat endpoints
old_stream_start = '''@app.route('/stream', methods=['POST'])
def stream_endpoint():
    try:
        data = request.json
        if not data:'''

new_stream_start = '''@app.route('/stream', methods=['POST'])
def stream_endpoint():
    if not check_rate_limit('stream'):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    try:
        data = request.json
        if not data:'''

if old_stream_start in content and 'check_rate_limit' not in content.split("def stream_endpoint")[1][:200]:
    content = content.replace(old_stream_start, new_stream_start, 1)
    changes.append("/stream: 添加频率限制")

old_chat_start = '''@app.route('/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        if not data:'''

new_chat_start = '''@app.route('/chat', methods=['POST'])
def chat_endpoint():
    if not check_rate_limit('chat'):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    try:
        data = request.json
        if not data:'''

if old_chat_start in content and 'check_rate_limit' not in content.split("def chat_endpoint")[1][:200]:
    content = content.replace(old_chat_start, new_chat_start, 1)
    changes.append("/chat: 添加频率限制")

# ============================================================
# 7. 前端: 优化localStorage读写 - 使用debouncedSaveLS
# ============================================================
print("[7] Frontend: Optimize localStorage writes...")

# Find places where localStorage.setItem is called frequently
# and replace with debouncedSaveLS

old_ls_saves = [
    ("localStorage.setItem('kaguya_settings', JSON.stringify(settings))", "debouncedSaveLS('kaguya_settings', settings)"),
    ("localStorage.setItem('kaguya_stats', JSON.stringify(stats))", "debouncedSaveLS('kaguya_stats', stats)"),
    ("localStorage.setItem('kaguya_feature_actions', JSON.stringify(featureActionHistory))", "debouncedSaveLS('kaguya_feature_actions', featureActionHistory)"),
]

ls_count = 0
for old, new in old_ls_saves:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        ls_count += count

if ls_count > 0:
    changes.append(f"localStorage写入优化: {ls_count}处->debouncedSaveLS节流写入")

# ============================================================
# 保存文件
# ============================================================
new_lines = len(content.split('\n'))
print(f"\nNew lines: {new_lines}")
print(f"Change: {new_lines - total_lines:+d}")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {FILE}")
print(f"\nTotal {len(changes)} optimizations:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
