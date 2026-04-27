import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

total_lines = len(content.split('\n'))
print(f"Original lines: {total_lines}")

changes = []

# ============================================================
# 1. XSS防护: 批量替换 innerHTML 中的动态数据为 escapeHtml()
# ============================================================
print("[1] XSS: Adding escapeHtml() to innerHTML assignments...")

# Pattern: ${variable} inside template literals in innerHTML
# We need to wrap user-provided data with escapeHtml()

xss_replacements = [
    # RAG doc list
    ('title="${doc.filename}"', 'title="${escapeHtml(doc.filename)}"'),
    ('>${doc.filename}</span>', '>${escapeHtml(doc.filename)}</span>'),
    ('>${doc.chunk_count}', '>${doc.chunk_count}'),
    ('>${(doc.size / 1024).toFixed(1)} KB<', '>${(doc.size / 1024).toFixed(1)} KB<'),
    # Chat list
    ('${c.title || \'新对话\'}</span>', '${escapeHtml(c.title || \'新对话\')}</span>'),
    # Role list
    ('${r.name}</div>', '${escapeHtml(r.name)}</div>'),
    ('${r.description}</div>', '${escapeHtml(r.description)}</div>'),
    # Tool list
    ('${t.name}</div>', '${escapeHtml(t.name)}</div>'),
    ('${t.description}</div>', '${escapeHtml(t.description)}</div>'),
    # LoRA list
    ('${l.name}</div>', '${escapeHtml(l.name)}</div>'),
    ('${l.description}</div>', '${escapeHtml(l.description)}</div>'),
    # MCP plugins
    ('${p.name}', '${escapeHtml(p.name)}'),
    ('${p.desc}', '${escapeHtml(p.desc)}'),
    # Memory
    ('${m.content}', '${escapeHtml(m.content)}'),
    # Workflow
    ('${wf.name}', '${escapeHtml(wf.name)}'),
    ('${wf.description}', '${escapeHtml(wf.description)}'),
    # Global search
    ('${item.title}', '${escapeHtml(item.title)}'),
    ('${item.subtitle}', '${escapeHtml(item.subtitle)}'),
    # Artifacts
    ('${item.name}', '${escapeHtml(item.name)}'),
    # Scheduled tasks
    ('${t.name}', '${escapeHtml(t.name)}'),
    # Services
    ('${s.name}', '${escapeHtml(s.name)}'),
    # Git repos
    ('${r.name}', '${escapeHtml(r.name)}'),
    # Project templates
    ('${t.description}', '${escapeHtml(t.description)}'),
    # Console recommendations
    ('${item.action}', '${escapeHtml(item.action)}'),
    # Activity
    ('${item.detail}', '${escapeHtml(item.detail)}'),
    # Milestones
    ('${item.owner}', '${escapeHtml(item.owner)}'),
    # Risks
    ('${item.mitigation}', '${escapeHtml(item.mitigation)}'),
    # Ops campaigns
    ('${item.channel}', '${escapeHtml(item.channel)}'),
    # Release plans
    ('${item.version}', '${escapeHtml(item.version)}'),
    # Alert rules
    ('${item.metric}', '${escapeHtml(item.metric)}'),
    # AB experiments
    # Integration
    ('${item.provider}', '${escapeHtml(item.provider)}'),
    # Finetune
    ('${ds.name}', '${escapeHtml(ds.name)}'),
    ('${job.name}', '${escapeHtml(job.name)}'),
    ('${job.dataset_name}', '${escapeHtml(job.dataset_name)}'),
]

xss_count = 0
for old, new in xss_replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        xss_count += count

changes.append(f"XSS: {xss_count} 处动态数据添加 escapeHtml() 转义")

# ============================================================
# 2. CSS动画合并: pulse-glow + search-pulse -> 参数化
# ============================================================
print("[2] CSS: Merge pulse animations...")

old_pulse_glow = '''@keyframes pulse-glow {
            0%, 100% { box-shadow: 0 4px 15px rgba(102,126,234,0.4); }
            50% { box-shadow: 0 4px 25px rgba(102,126,234,0.6); }
        }'''

new_pulse_glow = '''@keyframes pulse-glow {
            0%, 100% { box-shadow: 0 4px 15px var(--glow-color, rgba(102,126,234,0.4)); }
            50% { box-shadow: 0 4px 25px var(--glow-color, rgba(102,126,234,0.6)); }
        }'''

if old_pulse_glow in content:
    content = content.replace(old_pulse_glow, new_pulse_glow, 1)
    changes.append("pulse-glow动画参数化: 使用--glow-color CSS变量")

old_search_pulse = '''@keyframes search-pulse {
            0%, 100% { box-shadow: 0 4px 15px rgba(16,185,129,0.35); }
            50% { box-shadow: 0 4px 22px rgba(16,185,129,0.5); }
        }'''

new_search_pulse = '''@keyframes search-pulse {
            0%, 100% { box-shadow: 0 4px 15px var(--glow-color, rgba(16,185,129,0.35)); }
            50% { box-shadow: 0 4px 22px var(--glow-color, rgba(16,185,129,0.5)); }
        }'''

if old_search_pulse in content:
    content = content.replace(old_search_pulse, new_search_pulse, 1)
    changes.append("search-pulse动画参数化: 使用--glow-color CSS变量")

# ============================================================
# 3. 模态框工厂: 转换更多手动创建的模态框
# ============================================================
print("[3] Modal factory: Convert more modals...")

# openQuickSceneModal
old_quick_scene = '''function openQuickSceneModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'quickSceneModal';'''

new_quick_scene = '''function openQuickSceneModal() {
            const modal = createModal('quickSceneModal', 'Quick Scene', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_quick_scene in content:
    content = content.replace(old_quick_scene, new_quick_scene, 1)
    changes.append("openQuickSceneModal: createElement->createModal工厂")

# openBatchImportModal
old_batch = '''function openBatchImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'batchImportModal';'''

new_batch = '''function openBatchImportModal() {
            const modal = createModal('batchImportModal', 'Batch Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_batch in content:
    content = content.replace(old_batch, new_batch, 1)
    changes.append("openBatchImportModal: createElement->createModal工厂")

# openUrlImportModal
old_url = '''function openUrlImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'urlImportModal';'''

new_url = '''function openUrlImportModal() {
            const modal = createModal('urlImportModal', 'URL Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_url in content:
    content = content.replace(old_url, new_url, 1)
    changes.append("openUrlImportModal: createElement->createModal工厂")

# openGitImportModal
old_git = '''function openGitImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'gitImportModal';'''

new_git = '''function openGitImportModal() {
            const modal = createModal('gitImportModal', 'Git Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_git in content:
    content = content.replace(old_git, new_git, 1)
    changes.append("openGitImportModal: createElement->createModal工厂")

# openKnowledgeGraphModal
old_kg = '''function openKnowledgeGraphModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'knowledgeGraphModal';'''

new_kg = '''function openKnowledgeGraphModal() {
            const modal = createModal('knowledgeGraphModal', 'Knowledge Graph', '', {maxWidth: '600px'});
            modal.querySelector('.modal-body').innerHTML ='''

if old_kg in content:
    content = content.replace(old_kg, new_kg, 1)
    changes.append("openKnowledgeGraphModal: createElement->createModal工厂")

# ============================================================
# 4. 后端: 错误信息脱敏 - 不暴露内部异常细节
# ============================================================
print("[4] Backend: Error message sanitization...")

# Add a sanitize_error function
sanitize_func = '''
def sanitize_error(e):
    msg = str(e)
    for pattern in [r'[A-Z]:\\\\[^\s]+', r'/[a-z]+/[a-z_]+', r'api[_-]?key[=:]["\']?[\w-]+', r'Bearer [\w-]+']:
        msg = re.sub(pattern, '[REDACTED]', msg, flags=re.IGNORECASE)
    return msg[:200]
'''

if 'def sanitize_error(' not in content:
    # Insert before app = Flask
    app_pos = content.find("app = Flask(__name__)")
    if app_pos > 0:
        content = content[:app_pos] + sanitize_func + '\n' + content[app_pos:]
        changes.append("添加 sanitize_error() 错误信息脱敏函数")

# Replace str(e) in error responses with sanitize_error(e)
# Only in jsonify error responses, not in print/logging
old_error_pattern = "return jsonify({'success': False, 'error': str(e)})"
new_error_pattern = "return jsonify({'success': False, 'error': sanitize_error(e)})"
count = content.count(old_error_pattern)
if count > 0:
    content = content.replace(old_error_pattern, new_error_pattern)
    changes.append(f"错误响应脱敏: {count}处 str(e)->sanitize_error(e)")

# Also fix the deepseek chat error
old_ds_error = "return jsonify({'error': str(e)}), 500"
new_ds_error = "return jsonify({'error': sanitize_error(e)}), 500"
count = content.count(old_ds_error)
if count > 0:
    content = content.replace(old_ds_error, new_ds_error)
    changes.append(f"DeepSeek错误脱敏: {count}处 str(e)->sanitize_error(e)")

# ============================================================
# 5. 后端: 更多端点输入验证
# ============================================================
print("[5] Backend: More input validation...")

# /rag/upload - validate file size
old_rag_upload = '''@app.route('/rag/upload', methods=['POST'])
def rag_upload():
    try:'''
new_rag_upload = '''@app.route('/rag/upload', methods=['POST'])
def rag_upload():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        file = request.files['file']
        if file.content_length and file.content_length > 50 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'File too large (max 50MB)'})'''

if old_rag_upload in content and 'No file provided' not in content:
    content = content.replace(old_rag_upload, new_rag_upload, 1)
    changes.append("/rag/upload: 添加文件验证")

# /code/execute - validate code length
old_code_exec = '''@app.route('/code/execute', methods=['POST'])
def code_execute():
    data = request.json
    code = data.get('code', '')'''
new_code_exec = '''@app.route('/code/execute', methods=['POST'])
def code_execute():
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Empty request'})
    code = data.get('code', '')
    if len(code) > 100000:
        return jsonify({'success': False, 'error': 'Code too long (max 100K chars)'})'''

if old_code_exec in content and 'Empty request' not in content:
    content = content.replace(old_code_exec, new_code_exec, 1)
    changes.append("/code/execute: 添加输入验证")

# /tool/execute - validate tool_id
old_tool_exec = '''@app.route('/tool/execute', methods=['POST'])
def tool_execute():
    data = request.json
    tool_id = data.get('tool')'''
new_tool_exec = '''@app.route('/tool/execute', methods=['POST'])
def tool_execute():
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Empty request'})
    tool_id = data.get('tool')
    if not tool_id:
        return jsonify({'success': False, 'error': 'Tool ID required'})'''

if old_tool_exec in content and 'Tool ID required' not in content:
    content = content.replace(old_tool_exec, new_tool_exec, 1)
    changes.append("/tool/execute: 添加输入验证")

# ============================================================
# 6. 前端: 添加AbortController支持
# ============================================================
print("[6] Frontend: AbortController support...")

abort_code = '''
        const _activeControllers = new Map();
        function abortableFetch(key, url, opts = {}) {
            if (_activeControllers.has(key)) _activeControllers.get(key).abort();
            const ctrl = new AbortController();
            _activeControllers.set(key, ctrl);
            opts.signal = ctrl.signal;
            return fetch(url, opts).finally(() => _activeControllers.delete(key));
        }
'''

if '_activeControllers' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        content = content[:init_pos] + abort_code + '\n        ' + content[init_pos:]
        changes.append("添加 abortableFetch(): AbortController请求取消支持")

# ============================================================
# 7. 前端: 模板数据去重 - 合并allTemplates到WORKBENCH_TEMPLATES
# ============================================================
print("[7] Frontend: Template data deduplication...")

# Add a unified WORKBENCH_TEMPLATES constant before the functions that use it
templates_const = '''
        const WORKBENCH_TEMPLATES = [
            {id:'code-review',name:'Code Review',icon:'🔍',desc:'Code review & quality check',category:'engineering',prompt:'Please review the following code for quality, security, and best practices...',steps:['Analyze','Report','Suggest']},
            {id:'doc-gen',name:'Doc Gen',icon:'📄',desc:'Generate documentation',category:'general',prompt:'Generate comprehensive documentation for the following...',steps:['Extract','Structure','Generate']},
            {id:'api-design',name:'API Design',icon:'🔌',desc:'Design API interfaces',category:'engineering',prompt:'Design a RESTful API based on the requirements...',steps:['Requirements','Design','Document']},
            {id:'test-gen',name:'Test Gen',icon:'🧪',desc:'Generate test cases',category:'engineering',prompt:'Generate comprehensive test cases for...',steps:['Analyze','Generate','Validate']},
            {id:'refactor',name:'Refactor',icon:'♻️',desc:'Code refactoring',category:'engineering',prompt:'Refactor the following code for better readability...',steps:['Analyze','Plan','Refactor']},
            {id:'security',name:'Security',icon:'🛡️',desc:'Security audit',category:'engineering',prompt:'Perform a security audit on...',steps:['Scan','Analyze','Report']},
            {id:'data-analysis',name:'Data Analysis',icon:'📊',desc:'Data analysis & insights',category:'data',prompt:'Analyze the following data and provide insights...',steps:['Collect','Analyze','Visualize']},
            {id:'report-gen',name:'Report Gen',icon:'📋',desc:'Generate reports',category:'general',prompt:'Generate a detailed report based on...',steps:['Gather','Structure','Generate']},
            {id:'creative-write',name:'Creative Write',icon:'✍️',desc:'Creative writing',category:'creative',prompt:'Write creative content about...',steps:['Brainstorm','Draft','Polish']},
        ];
'''

if 'WORKBENCH_TEMPLATES' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        content = content[:init_pos] + templates_const + '\n        ' + content[init_pos:]
        changes.append("添加 WORKBENCH_TEMPLATES 统一模板数据常量")

# Replace allTemplates in renderWorkbenchContent to use WORKBENCH_TEMPLATES
old_all_templates = '''const allTemplates = [
                {id: 'code-review', name: '代码审查', icon: '🔍', desc: '专业代码审查与质量检测', category: 'engineering'},
                {id: 'doc-gen', name: '文档生成', icon: '📄', desc: '智能文档生成与格式化', category: 'general'},
                {id: 'api-design', name: 'API设计', icon: '🔌', desc: 'RESTful API设计与文档', category: 'engineering'},
                {id: 'test-gen', name: '测试生成', icon: '🧪', desc: '自动化测试用例生成', category: 'engineering'},
                {id: 'refactor', name: '代码重构', icon: '♻️', desc: '代码重构与优化建议', category: 'engineering'},
                {id: 'security', name: '安全审计', icon: '🛡️', desc: '代码安全审计与漏洞检测', category: 'engineering'},
                {id: 'data-analysis', name: '数据分析', icon: '📊', desc: '数据洞察与可视化分析', category: 'data'},
                {id: 'report-gen', name: '报告生成', icon: '📋', desc: '专业报告自动生成', category: 'general'},
                {id: 'creative-write', name: '创意写作', icon: '✍️', desc: '创意内容与文案生成', category: 'creative'}
            ];'''

new_all_templates = 'const allTemplates = WORKBENCH_TEMPLATES;'

if old_all_templates in content:
    content = content.replace(old_all_templates, new_all_templates, 1)
    changes.append("renderWorkbenchContent: allTemplates->WORKBENCH_TEMPLATES引用")

# ============================================================
# 8. 后端: 为更多全局列表操作添加线程锁
# ============================================================
print("[8] Backend: More thread safety...")

# Add locks for ops_campaigns, release_plans, alert_rules, etc.
global_lists_to_lock = [
    ('ops_campaigns.append', 'ops_campaigns'),
    ('release_plans.append', 'release_plans'),
    ('alert_rules.append', 'alert_rules'),
    ('ab_experiments.append', 'ab_experiments'),
    ('integrations.append', 'integrations'),
    ('project_milestones.append', 'project_milestones'),
    ('project_risks.append', 'project_risks'),
]

lock_count = 0
for append_pattern, list_name in global_lists_to_lock:
    if append_pattern in content:
        old_append = f'{append_pattern}('
        new_append = f'with data_lock:\n            {list_name}.append('
        # Only replace the first occurrence
        idx = content.find(old_append)
        if idx > 0:
            content = content[:idx] + new_append + content[idx + len(old_append):]
            lock_count += 1

if lock_count > 0:
    changes.append(f"全局列表append添加线程锁: {lock_count}处")

# ============================================================
# 9. 前端: 更多getElementById->$()替换 (批量处理)
# ============================================================
print("[9] Frontend: More getElementById->$() replacements...")

# Target the most frequently accessed elements
id_replacements = [
    ("document.getElementById('mainInput')", "$('mainInput')"),
    ("document.getElementById('messagesContainer')", "$('messagesContainer')"),
    ("document.getElementById('ragDocList')", "$('ragDocList')"),
    ("document.getElementById('ragCategoryFilter')", "$('ragCategoryFilter')"),
    ("document.getElementById('ragSearchInput')", "$('ragSearchInput')"),
    ("document.getElementById('ragSearchResults')", "$('ragSearchResults')"),
    ("document.getElementById('ragToggle')", "$('ragToggle')"),
    ("document.getElementById('modalOverlay')", "$('modalOverlay')"),
    ("document.getElementById('globalSearchInput')", "$('globalSearchInput')"),
    ("document.getElementById('chatSearch')", "$('chatSearch')"),
    ("document.getElementById('logViewer')", "$('logViewer')"),
    ("document.getElementById('logLevelFilter')", "$('logLevelFilter')"),
    ("document.getElementById('kbSearch')", "$('kbSearch')"),
    ("document.getElementById('sceneProviderSelect')", "$('sceneProviderSelect')"),
    ("document.getElementById('sceneApiUrlInput')", "$('sceneApiUrlInput')"),
    ("document.getElementById('sceneApiKeyInput')", "$('sceneApiKeyInput')"),
    ("document.getElementById('sceneModelInput')", "$('sceneModelInput')"),
]

dom_count = 0
for old_id, new_id in id_replacements:
    count = content.count(old_id)
    if count > 0:
        content = content.replace(old_id, new_id)
        dom_count += count

if dom_count > 0:
    changes.append(f"DOM缓存: {dom_count}处 getElementById->$() 替换")

# ============================================================
# 10. 前端: fetch请求添加通用.catch()
# ============================================================
print("[10] Frontend: Add .catch() to fetch chains...")

# Pattern: .then(r => r.json()).then(data => { ... }); without .catch()
# Add .catch(() => showToast('Network error')) before the semicolon
# This is tricky to do with regex, so we'll target specific patterns

# Common pattern: fetch(...).then(r => r.json()).then(data => {...});
# We need to add .catch() before the closing

# Find fetch calls that end with }); without .catch
fetch_no_catch = re.findall(
    r'fetch\([^)]+\)\.then\(r\s*=>\s*r\.json\(\)\)\.then\([^)]+\s*=>\s*\{[^}]*\}\);',
    content
)

# Instead of complex regex, let's add a global fetch wrapper that auto-handles errors
fetch_wrapper = '''
        const _origFetch2 = window.fetch;
        window.fetch = function(...args) {
            const p = _origFetch2.apply(this, args);
            const chain = p.then(r => {
                if (!r.ok && r.status !== 200 && r.status !== 206) {
                    console.warn('Fetch warning:', r.status, args[0]);
                }
                return r;
            });
            return chain;
        };
'''

# Actually, we already have a fetch interceptor. Let's instead add .catch() to specific critical fetches
# Let's add a utility function
catch_util = '''
        function safeFetch(url, opts = {}) {
            return fetch(url, opts).catch(err => {
                console.warn('Fetch error:', url, err);
                return {json: () => Promise.resolve({success: false, error: 'Network error'})};
            });
        }
'''

if 'function safeFetch(' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        content = content[:init_pos] + catch_util + '\n        ' + content[init_pos:]
        changes.append("添加 safeFetch(): 自动错误处理的fetch包装函数")

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
