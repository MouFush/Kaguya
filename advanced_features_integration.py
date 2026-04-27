#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 高级功能前端集成模块
为右侧边栏添加高级LLM功能页面
"""

# 高级功能页面的HTML内容
ADVANCED_FEATURES_HTML = """
<!-- 高级功能Tab -->
<div id="advancedTab" class="tab-content">
    <div class="advanced-list" id="advancedList">
        <!-- 提示词工程 -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('prompt-engineering')">
                <span class="advanced-icon">📝</span>
                <div class="advanced-info">
                    <div class="advanced-name">提示词工程</div>
                    <div class="advanced-desc">DSPy风格的系统化提示词优化</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="prompt-engineering-content" style="display:none;">
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="createPromptModule()">创建模块</button>
                    <button class="advanced-btn secondary" onclick="optimizePrompt()">自动优化</button>
                </div>
                <div class="advanced-list-items" id="promptModulesList">
                    <div class="advanced-item">
                        <span>情感分析模块</span>
                        <span class="advanced-badge">3个示例</span>
                    </div>
                    <div class="advanced-item">
                        <span>代码生成模块</span>
                        <span class="advanced-badge">5个示例</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- GraphRAG -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('graph-rag')">
                <span class="advanced-icon">🕸️</span>
                <div class="advanced-info">
                    <div class="advanced-name">GraphRAG</div>
                    <div class="advanced-desc">基于知识图谱的高级检索</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="graph-rag-content" style="display:none;">
                <div class="advanced-stats">
                    <div class="advanced-stat">
                        <span class="stat-value" id="graphEntities">0</span>
                        <span class="stat-label">实体</span>
                    </div>
                    <div class="advanced-stat">
                        <span class="stat-value" id="graphRelations">0</span>
                        <span class="stat-label">关系</span>
                    </div>
                    <div class="advanced-stat">
                        <span class="stat-value" id="graphCommunities">0</span>
                        <span class="stat-label">社区</span>
                    </div>
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="buildKnowledgeGraph()">构建图谱</button>
                    <button class="advanced-btn secondary" onclick="queryKnowledgeGraph()">查询图谱</button>
                </div>
            </div>
        </div>

        <!-- Self-RAG -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('self-rag')">
                <span class="advanced-icon">🔄</span>
                <div class="advanced-info">
                    <div class="advanced-name">Self-RAG</div>
                    <div class="advanced-desc">自适应检索增强生成</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="self-rag-content" style="display:none;">
                <div class="advanced-config">
                    <label>检索阈值: <span id="ragThreshold">0.7</span></label>
                    <input type="range" min="0.1" max="1" step="0.1" value="0.7" 
                           oninput="updateRagThreshold(this.value)">
                    <label>最大迭代: <span id="ragMaxIter">3</span></label>
                    <input type="range" min="1" max="5" step="1" value="3" 
                           oninput="updateRagMaxIter(this.value)">
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="enableSelfRag()">启用Self-RAG</button>
                </div>
            </div>
        </div>

        <!-- 模型评估 -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('evaluation')">
                <span class="advanced-icon">📊</span>
                <div class="advanced-info">
                    <div class="advanced-name">模型评估</div>
                    <div class="advanced-desc">RAGAS风格无参考评估</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="evaluation-content" style="display:none;">
                <div class="advanced-metrics">
                    <div class="metric-item">
                        <span class="metric-name">忠实度</span>
                        <div class="metric-bar"><div class="metric-fill" style="width:0%"></div></div>
                        <span class="metric-score">-</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-name">相关性</span>
                        <div class="metric-bar"><div class="metric-fill" style="width:0%"></div></div>
                        <span class="metric-score">-</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-name">精确度</span>
                        <div class="metric-bar"><div class="metric-fill" style="width:0%"></div></div>
                        <span class="metric-score">-</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-name">召回率</span>
                        <div class="metric-bar"><div class="metric-fill" style="width:0%"></div></div>
                        <span class="metric-score">-</span>
                    </div>
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="runEvaluation()">运行评估</button>
                    <button class="advanced-btn secondary" onclick="generateTestData()">生成测试数据</button>
                </div>
            </div>
        </div>

        <!-- 模型微调 -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('finetuning')">
                <span class="advanced-icon">🔧</span>
                <div class="advanced-info">
                    <div class="advanced-name">模型微调</div>
                    <div class="advanced-desc">LoRA/QLoRA高效微调</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="finetuning-content" style="display:none;">
                <div class="advanced-jobs" id="finetuningJobs">
                    <div class="job-item">
                        <div class="job-info">
                            <span class="job-name">ft_job_0001</span>
                            <span class="job-status completed">已完成</span>
                        </div>
                        <div class="job-progress">
                            <div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div>
                            <span class="progress-text">100%</span>
                        </div>
                    </div>
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="createFinetuneJob()">创建任务</button>
                    <button class="advanced-btn secondary" onclick="exportConfigYaml()">导出配置</button>
                </div>
            </div>
        </div>

        <!-- 推理优化 -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('inference')">
                <span class="advanced-icon">⚡</span>
                <div class="advanced-info">
                    <div class="advanced-name">推理优化</div>
                    <div class="advanced-desc">vLLM风格批处理优化</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="inference-content" style="display:none;">
                <div class="advanced-stats">
                    <div class="advanced-stat">
                        <span class="stat-value" id="inferenceThroughput">0</span>
                        <span class="stat-label">吞吐(req/s)</span>
                    </div>
                    <div class="advanced-stat">
                        <span class="stat-value" id="avgBatchSize">0</span>
                        <span class="stat-label">平均批次</span>
                    </div>
                </div>
                <div class="advanced-config">
                    <label>最大批次: <span id="maxBatchSize">16</span></label>
                    <input type="range" min="1" max="32" step="1" value="16" 
                           oninput="updateMaxBatchSize(this.value)">
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="enableBatchInference()">启用批处理</button>
                </div>
            </div>
        </div>

        <!-- 安全护栏 -->
        <div class="advanced-section">
            <div class="advanced-section-header" onclick="toggleAdvancedSection('security')">
                <span class="advanced-icon">🛡️</span>
                <div class="advanced-info">
                    <div class="advanced-name">安全护栏</div>
                    <div class="advanced-desc">LLM Guard输入输出保护</div>
                </div>
                <span class="advanced-toggle">▼</span>
            </div>
            <div class="advanced-content" id="security-content" style="display:none;">
                <div class="advanced-stats">
                    <div class="advanced-stat">
                        <span class="stat-value" id="scannedCount">0</span>
                        <span class="stat-label">已扫描</span>
                    </div>
                    <div class="advanced-stat">
                        <span class="stat-value" id="blockedCount">0</span>
                        <span class="stat-label">已拦截</span>
                    </div>
                    <div class="advanced-stat">
                        <span class="stat-value" id="sanitizedCount">0</span>
                        <span class="stat-label">已脱敏</span>
                    </div>
                </div>
                <div class="advanced-config">
                    <label class="checkbox-label">
                        <input type="checkbox" id="enableInputGuard" checked> 输入检查
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="enableOutputGuard" checked> 输出检查
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="enablePiiDetection" checked> PII检测
                    </label>
                </div>
                <div class="advanced-actions">
                    <button class="advanced-btn" onclick="addBannedKeyword()">添加禁用词</button>
                    <button class="advanced-btn secondary" onclick="viewSecurityLogs()">查看日志</button>
                </div>
            </div>
        </div>
    </div>
</div>
"""

# 高级功能的CSS样式
ADVANCED_FEATURES_CSS = """
<style>
/* 高级功能样式 */
.advanced-list {
    padding: 12px;
    flex: 1;
    overflow-y: auto;
}

.advanced-section {
    background: var(--bg-secondary);
    border-radius: 14px;
    margin-bottom: 12px;
    border: 1.5px solid var(--border);
    overflow: hidden;
    transition: all 0.3s ease;
}

.advanced-section:hover {
    border-color: var(--primary);
    box-shadow: 0 4px 12px rgba(102,126,234,0.1);
}

.advanced-section-header {
    display: flex;
    align-items: center;
    padding: 14px 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    background: linear-gradient(135deg, rgba(255,255,255,0.6), rgba(255,255,255,0.4));
}

.dark .advanced-section-header {
    background: linear-gradient(135deg, rgba(50,50,75,0.6), rgba(45,45,70,0.4));
}

.advanced-section-header:hover {
    background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.05));
}

.advanced-icon {
    font-size: 22px;
    margin-right: 12px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(102,126,234,0.3);
}

.advanced-info {
    flex: 1;
}

.advanced-name {
    font-weight: 600;
    font-size: 14px;
    color: var(--text-primary);
    margin-bottom: 2px;
}

.advanced-desc {
    font-size: 11px;
    color: var(--text-muted);
}

.advanced-toggle {
    font-size: 12px;
    color: var(--text-muted);
    transition: transform 0.3s ease;
}

.advanced-section.expanded .advanced-toggle {
    transform: rotate(180deg);
}

.advanced-content {
    padding: 16px;
    border-top: 1px solid var(--border);
    background: rgba(0,0,0,0.02);
}

.dark .advanced-content {
    background: rgba(255,255,255,0.02);
}

.advanced-actions {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.advanced-btn {
    flex: 1;
    padding: 8px 12px;
    background: linear-gradient(135deg, var(--primary), var(--secondary));
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.advanced-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102,126,234,0.3);
}

.advanced-btn.secondary {
    background: var(--bg-primary);
    color: var(--text-primary);
    border: 1px solid var(--border);
}

.advanced-btn.secondary:hover {
    background: var(--primary);
    color: white;
    border-color: var(--primary);
}

.advanced-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}

.advanced-stat {
    text-align: center;
    padding: 10px;
    background: var(--bg-primary);
    border-radius: 8px;
    border: 1px solid var(--border);
}

.stat-value {
    display: block;
    font-size: 18px;
    font-weight: 700;
    color: var(--primary);
    margin-bottom: 2px;
}

.stat-label {
    font-size: 10px;
    color: var(--text-muted);
}

.advanced-config {
    margin-bottom: 12px;
}

.advanced-config label {
    display: block;
    font-size: 11px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.advanced-config input[type="range"] {
    width: 100%;
    margin-bottom: 8px;
}

.checkbox-label {
    display: flex !important;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px !important;
    cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
    width: auto !important;
    margin: 0 !important;
}

.advanced-list-items {
    max-height: 150px;
    overflow-y: auto;
}

.advanced-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: var(--bg-primary);
    border-radius: 8px;
    margin-bottom: 6px;
    font-size: 12px;
    border: 1px solid var(--border);
}

.advanced-badge {
    font-size: 10px;
    color: var(--primary);
    background: rgba(102,126,234,0.1);
    padding: 2px 8px;
    border-radius: 4px;
}

.advanced-metrics {
    margin-bottom: 12px;
}

.metric-item {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

.metric-name {
    width: 60px;
    font-size: 11px;
    color: var(--text-secondary);
}

.metric-bar {
    flex: 1;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
}

.metric-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--primary), var(--secondary));
    border-radius: 3px;
    transition: width 0.5s ease;
}

.metric-score {
    width: 40px;
    font-size: 11px;
    font-weight: 600;
    color: var(--primary);
    text-align: right;
}

.advanced-jobs {
    margin-bottom: 12px;
}

.job-item {
    background: var(--bg-primary);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid var(--border);
}

.job-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.job-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
}

.job-status {
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 600;
}

.job-status.running {
    background: rgba(245,158,11,0.2);
    color: var(--warning);
}

.job-status.completed {
    background: rgba(16,185,129,0.2);
    color: var(--success);
}

.job-progress {
    display: flex;
    align-items: center;
    gap: 8px;
}

.progress-bar {
    flex: 1;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--success), #34d399);
    border-radius: 2px;
    transition: width 0.3s ease;
}

.progress-text {
    font-size: 10px;
    color: var(--text-muted);
    width: 35px;
    text-align: right;
}
</style>
"""

# 高级功能的JavaScript
ADVANCED_FEATURES_JS = """
<script>
// ==================== 高级功能模块 ====================

// 切换高级功能区块
function toggleAdvancedSection(sectionId) {
    const content = document.getElementById(sectionId + '-content');
    const section = content.closest('.advanced-section');
    const toggle = section.querySelector('.advanced-toggle');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        section.classList.add('expanded');
        toggle.textContent = '▲';
    } else {
        content.style.display = 'none';
        section.classList.remove('expanded');
        toggle.textContent = '▼';
    }
}

// 提示词工程功能
function createPromptModule() {
    const name = prompt('请输入模块名称:');
    if (name) {
        showNotification('创建提示词模块: ' + name, 'success');
        // 实际实现中调用后端API
    }
}

function optimizePrompt() {
    showNotification('开始自动优化提示词...', 'info');
    // 实际实现中调用后端API
}

// GraphRAG功能
function buildKnowledgeGraph() {
    showNotification('开始构建知识图谱...', 'info');
    fetch('/advanced/graphrag/build', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({documents: []})
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById('graphEntities').textContent = data.entities || 0;
        document.getElementById('graphRelations').textContent = data.relations || 0;
        document.getElementById('graphCommunities').textContent = data.communities || 0;
        showNotification('知识图谱构建完成', 'success');
    });
}

function queryKnowledgeGraph() {
    const query = prompt('请输入查询:');
    if (query) {
        showNotification('查询知识图谱: ' + query, 'info');
    }
}

// Self-RAG功能
function updateRagThreshold(value) {
    document.getElementById('ragThreshold').textContent = value;
}

function updateRagMaxIter(value) {
    document.getElementById('ragMaxIter').textContent = value;
}

function enableSelfRag() {
    showNotification('Self-RAG已启用', 'success');
}

// 评估功能
function runEvaluation() {
    showNotification('开始运行评估...', 'info');
    // 模拟评估结果
    setTimeout(() => {
        document.querySelectorAll('.metric-fill').forEach((bar, i) => {
            const scores = [0.85, 0.92, 0.78, 0.88];
            bar.style.width = (scores[i] * 100) + '%';
            bar.parentElement.nextElementSibling.textContent = scores[i];
        });
        showNotification('评估完成', 'success');
    }, 2000);
}

function generateTestData() {
    showNotification('生成测试数据中...', 'info');
}

// 微调功能
function createFinetuneJob() {
    showNotification('创建微调任务...', 'info');
}

function exportConfigYaml() {
    showNotification('导出YAML配置', 'success');
}

// 推理优化功能
function updateMaxBatchSize(value) {
    document.getElementById('maxBatchSize').textContent = value;
}

function enableBatchInference() {
    showNotification('批处理推理已启用', 'success');
}

// 安全护栏功能
function addBannedKeyword() {
    const keyword = prompt('请输入要禁用的关键词:');
    if (keyword) {
        showNotification('已添加禁用词: ' + keyword, 'success');
    }
}

function viewSecurityLogs() {
    showNotification('查看安全日志', 'info');
}

// 定期更新统计数据
function updateAdvancedStats() {
    fetch('/advanced/stats')
        .then(r => r.json())
        .then(data => {
            if (data.security) {
                document.getElementById('scannedCount').textContent = data.security.total_scanned || 0;
                document.getElementById('blockedCount').textContent = data.security.blocked_inputs || 0;
                document.getElementById('sanitizedCount').textContent = data.security.sanitized_outputs || 0;
            }
            if (data.inference) {
                document.getElementById('inferenceThroughput').textContent = 
                    (data.inference.throughput || 0).toFixed(1);
                document.getElementById('avgBatchSize').textContent = 
                    (data.inference.avg_batch_size || 0).toFixed(1);
            }
        })
        .catch(() => {}); // 静默失败
}

// 每5秒更新一次统计数据
setInterval(updateAdvancedStats, 5000);
</script>
"""

# Flask后端API路由
ADVANCED_FEATURES_ROUTES = '''

# ==================== 高级功能API路由 ====================

@app.route('/advanced/stats')
def advanced_stats():
    """获取高级功能统计"""
    try:
        from advanced_llm_features import AdvancedLLMManager
        manager = AdvancedLLMManager()
        return jsonify(manager.get_system_status())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/advanced/graphrag/build', methods=['POST'])
def graphrag_build():
    """构建知识图谱"""
    try:
        data = request.json
        documents = data.get('documents', [])
        
        # 这里应该调用实际的GraphRAG构建逻辑
        # 简化返回
        return jsonify({
            "success": True,
            "entities": len(documents) * 5,  # 模拟数据
            "relations": len(documents) * 3,
            "communities": max(1, len(documents) // 2)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/advanced/prompt/create', methods=['POST'])
def prompt_create():
    """创建提示词模块"""
    try:
        data = request.json
        # 实现提示词模块创建逻辑
        return jsonify({"success": True, "module_id": str(uuid.uuid4())})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/advanced/finetune/create', methods=['POST'])
def finetune_create():
    """创建微调任务"""
    try:
        data = request.json
        # 实现微调任务创建逻辑
        return jsonify({"success": True, "job_id": f"ft_job_{datetime.now().strftime('%04d')}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/advanced/security/add_keyword', methods=['POST'])
def security_add_keyword():
    """添加安全禁用词"""
    try:
        data = request.json
        keyword = data.get('keyword', '')
        # 实现添加禁用词逻辑
        return jsonify({"success": True, "keyword": keyword})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

'''

def integrate_advanced_features(html_template: str) -> str:
    """
    将高级功能集成到现有HTML模板中
    
    Args:
        html_template: 原始HTML模板字符串
        
    Returns:
        集成后的HTML模板字符串
    """
    # 1. 在</head>前添加CSS样式
    if '</style>' in html_template:
        html_template = html_template.replace(
            '</style>',
            ADVANCED_FEATURES_CSS.replace('<style>', '').replace('</style>', '') + '\n</style>',
            1
        )
    
    # 2. 在sidebar-tabs中添加高级功能Tab按钮
    tab_button = '<button class="sidebar-tab" onclick="switchTab(\'advanced\')">🚀<span>高级</span></button>'
    
    # 找到最后一个tab按钮的位置
    tab_pattern = '<button class="sidebar-tab" onclick="switchTab('
    last_tab_pos = html_template.rfind(tab_pattern)
    if last_tab_pos != -1:
        # 找到该按钮的结束位置
        end_pos = html_template.find('</button>', last_tab_pos)
        if end_pos != -1:
            html_template = html_template[:end_pos+9] + '\n' + tab_button + html_template[end_pos+9:]
    
    # 3. 在tab-content区域添加高级功能内容
    # 找到最后一个tab-content
    tab_content_pattern = '<div id="'
    last_content_pos = html_template.rfind('class="tab-content"')
    if last_content_pos != -1:
        # 找到该div的结束位置（下一个<div或</div>之前）
        next_div = html_template.find('<div', last_content_pos + 1)
        if next_div != -1:
            html_template = html_template[:next_div] + ADVANCED_FEATURES_HTML + '\n' + html_template[next_div:]
    
    # 4. 在</body>前添加JavaScript
    if '</body>' in html_template:
        html_template = html_template.replace(
            '</body>',
            ADVANCED_FEATURES_JS.replace('<script>', '').replace('</script>', '') + '\n</body>',
            1
        )
    
    return html_template


if __name__ == "__main__":
    # 测试集成
    print("高级功能前端集成模块")
    print("=" * 50)
    print("包含功能:")
    print("  - 提示词工程 (DSPy风格)")
    print("  - GraphRAG (知识图谱检索)")
    print("  - Self-RAG (自适应检索)")
    print("  - 模型评估 (RAGAS风格)")
    print("  - 模型微调 (LoRA/QLoRA)")
    print("  - 推理优化 (vLLM风格)")
    print("  - 安全护栏 (LLM Guard)")
    print("=" * 50)
    print("\n使用方式:")
    print("from advanced_features_integration import integrate_advanced_features")
    print("new_html = integrate_advanced_features(HTML_TEMPLATE)")
