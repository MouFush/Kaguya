/**
 * 辉夜AI - 高级增强功能模块
 * 功能: 数据分析、文档处理、智能工具
 */

class AdvancedFeaturesManager {
    constructor() {
        this.currentTab = 'analytics';
        this.analyticsData = null;
        this.documentContent = null;
        this.init();
    }

    init() {
        this._createUI();
        this._bindEvents();
        console.log('[高级功能] 初始化完成');
    }

    /**
     * 创建UI界面
     */
    _createUI() {
        // 创建主容器
        const container = document.createElement('div');
        container.id = 'advanced-features-panel';
        container.className = 'advanced-features-panel';
        container.innerHTML = `
            <div class="af-header">
                <h2>🔮 高级增强功能</h2>
                <button class="af-close-btn" onclick="advancedFeatures.close()">&times;</button>
            </div>
            <div class="af-tabs">
                <button class="af-tab active" data-tab="analytics">
                    <span class="af-tab-icon">📊</span>
                    <span>数据分析</span>
                </button>
                <button class="af-tab" data-tab="document">
                    <span class="af-tab-icon">📄</span>
                    <span>文档处理</span>
                </button>
                <button class="af-tab" data-tab="tools">
                    <span class="af-tab-icon">🛠️</span>
                    <span>智能工具</span>
                </button>
            </div>
            <div class="af-content">
                <!-- 数据分析面板 -->
                <div class="af-panel active" id="panel-analytics">
                    <div class="af-panel-header">
                        <h3>📊 高级数据分析</h3>
                        <p>数据清洗、统计分析、趋势预测</p>
                    </div>
                    <div class="af-panel-body">
                        <div class="af-input-section">
                            <label>数据输入 (JSON格式)</label>
                            <textarea id="analytics-input" placeholder='[
  {"date": "2024-01-01", "sales": 100, "customers": 50},
  {"date": "2024-01-02", "sales": 120, "customers": 55}
]'></textarea>
                        </div>
                        <div class="af-options">
                            <label class="af-checkbox">
                                <input type="checkbox" id="opt-clean-data" checked>
                                <span>数据清洗</span>
                            </label>
                            <label class="af-checkbox">
                                <input type="checkbox" id="opt-statistical" checked>
                                <span>统计分析</span>
                            </label>
                            <label class="af-checkbox">
                                <input type="checkbox" id="opt-trends">
                                <span>趋势分析</span>
                            </label>
                        </div>
                        <div class="af-trend-options" id="trend-options" style="display:none;">
                            <input type="text" id="time-column" placeholder="时间列名 (如: date)">
                            <input type="text" id="value-column" placeholder="数值列名 (如: sales)">
                        </div>
                        <button class="af-btn primary" onclick="advancedFeatures.analyzeData()">
                            <span class="btn-icon">🔍</span>
                            开始分析
                        </button>
                        <div class="af-results" id="analytics-results"></div>
                    </div>
                </div>

                <!-- 文档处理面板 -->
                <div class="af-panel" id="panel-document">
                    <div class="af-panel-header">
                        <h3>📄 智能文档处理</h3>
                        <p>文档解析、实体提取、智能摘要</p>
                    </div>
                    <div class="af-panel-body">
                        <div class="af-input-section">
                            <label>文档内容</label>
                            <textarea id="document-input" placeholder="粘贴文档内容..."></textarea>
                        </div>
                        <div class="af-select-row">
                            <select id="document-format">
                                <option value="text">纯文本</option>
                                <option value="markdown">Markdown</option>
                                <option value="json">JSON</option>
                                <option value="csv">CSV</option>
                                <option value="html">HTML</option>
                                <option value="xml">XML</option>
                                <option value="yaml">YAML</option>
                            </select>
                        </div>
                        <div class="af-options">
                            <label class="af-checkbox">
                                <input type="checkbox" id="doc-extract-entities" checked>
                                <span>提取实体</span>
                            </label>
                            <label class="af-checkbox">
                                <input type="checkbox" id="doc-generate-summary" checked>
                                <span>生成摘要</span>
                            </label>
                            <label class="af-checkbox">
                                <input type="checkbox" id="doc-extract-keywords" checked>
                                <span>提取关键词</span>
                            </label>
                        </div>
                        <button class="af-btn primary" onclick="advancedFeatures.processDocument()">
                            <span class="btn-icon">📝</span>
                            处理文档
                        </button>
                        <div class="af-results" id="document-results"></div>
                    </div>
                </div>

                <!-- 智能工具面板 -->
                <div class="af-panel" id="panel-tools">
                    <div class="af-panel-header">
                        <h3>🛠️ 智能工具箱</h3>
                        <p>实用工具集合</p>
                    </div>
                    <div class="af-panel-body">
                        <div class="af-tools-grid">
                            <div class="af-tool-card" onclick="advancedFeatures.openTool('summarizer')">
                                <span class="tool-icon">📝</span>
                                <span class="tool-name">文本摘要</span>
                                <span class="tool-desc">生成文本摘要和关键词</span>
                            </div>
                            <div class="af-tool-card" onclick="advancedFeatures.openTool('entity-extractor')">
                                <span class="tool-icon">🔍</span>
                                <span class="tool-name">实体提取</span>
                                <span class="tool-desc">提取邮箱、URL、日期等</span>
                            </div>
                            <div class="af-tool-card" onclick="advancedFeatures.openTool('format-converter')">
                                <span class="tool-icon">🔄</span>
                                <span class="tool-name">格式转换</span>
                                <span class="tool-desc">文档格式互转</span>
                            </div>
                            <div class="af-tool-card" onclick="advancedFeatures.openTool('data-cleaner')">
                                <span class="tool-icon">🧹</span>
                                <span class="tool-name">数据清洗</span>
                                <span class="tool-desc">清洗和标准化数据</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        this._addStyles();

        // 添加到页面
        document.body.appendChild(container);
        this.panel = container;
    }

    /**
     * 添加样式
     */
    _addStyles() {
        if (document.getElementById('advanced-features-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'advanced-features-styles';
        styles.textContent = `
            .advanced-features-panel {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 90%;
                max-width: 900px;
                height: 85%;
                max-height: 700px;
                background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
                border-radius: 16px;
                box-shadow: 0 25px 50px rgba(0,0,0,0.5);
                display: flex;
                flex-direction: column;
                z-index: 10000;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }

            .af-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 24px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .af-header h2 {
                margin: 0;
                font-size: 1.5rem;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .af-close-btn {
                background: none;
                border: none;
                color: #a0aec0;
                font-size: 28px;
                cursor: pointer;
                padding: 0;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 8px;
                transition: all 0.2s;
            }

            .af-close-btn:hover {
                background: rgba(255,255,255,0.1);
                color: #fff;
            }

            .af-tabs {
                display: flex;
                gap: 8px;
                padding: 16px 24px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .af-tab {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 12px 20px;
                background: rgba(255,255,255,0.05);
                border: none;
                border-radius: 8px 8px 0 0;
                color: #a0aec0;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
            }

            .af-tab:hover {
                background: rgba(255,255,255,0.1);
                color: #e2e8f0;
            }

            .af-tab.active {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #fff;
            }

            .af-tab-icon {
                font-size: 18px;
            }

            .af-content {
                flex: 1;
                overflow: hidden;
                position: relative;
            }

            .af-panel {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                padding: 24px;
                overflow-y: auto;
                display: none;
            }

            .af-panel.active {
                display: block;
            }

            .af-panel-header {
                margin-bottom: 20px;
            }

            .af-panel-header h3 {
                margin: 0 0 8px 0;
                font-size: 1.25rem;
                color: #e2e8f0;
            }

            .af-panel-header p {
                margin: 0;
                color: #a0aec0;
                font-size: 14px;
            }

            .af-input-section {
                margin-bottom: 16px;
            }

            .af-input-section label {
                display: block;
                margin-bottom: 8px;
                color: #e2e8f0;
                font-size: 14px;
                font-weight: 500;
            }

            .af-input-section textarea {
                width: 100%;
                min-height: 150px;
                padding: 12px;
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: #e2e8f0;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                resize: vertical;
                box-sizing: border-box;
            }

            .af-input-section textarea:focus {
                outline: none;
                border-color: #667eea;
            }

            .af-select-row {
                margin-bottom: 16px;
            }

            .af-select-row select {
                width: 100%;
                padding: 10px 12px;
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 14px;
            }

            .af-options {
                display: flex;
                flex-wrap: wrap;
                gap: 16px;
                margin-bottom: 16px;
            }

            .af-checkbox {
                display: flex;
                align-items: center;
                gap: 8px;
                cursor: pointer;
                font-size: 14px;
                color: #e2e8f0;
            }

            .af-checkbox input[type="checkbox"] {
                width: 18px;
                height: 18px;
                accent-color: #667eea;
            }

            .af-trend-options {
                display: flex;
                gap: 12px;
                margin-bottom: 16px;
            }

            .af-trend-options input {
                flex: 1;
                padding: 10px 12px;
                background: rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px;
                color: #e2e8f0;
                font-size: 14px;
            }

            .af-btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s;
            }

            .af-btn.primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #fff;
            }

            .af-btn.primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }

            .btn-icon {
                font-size: 16px;
            }

            .af-results {
                margin-top: 24px;
                padding: 20px;
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                display: none;
            }

            .af-results.show {
                display: block;
            }

            .af-results h4 {
                margin: 0 0 16px 0;
                color: #e2e8f0;
                font-size: 16px;
            }

            .af-result-section {
                margin-bottom: 20px;
            }

            .af-result-section h5 {
                margin: 0 0 12px 0;
                color: #a0aec0;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .af-insight-item {
                padding: 10px 12px;
                background: rgba(102, 126, 234, 0.1);
                border-left: 3px solid #667eea;
                border-radius: 0 8px 8px 0;
                margin-bottom: 8px;
                font-size: 13px;
                color: #e2e8f0;
            }

            .af-stat-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 12px;
            }

            .af-stat-card {
                padding: 16px;
                background: rgba(255,255,255,0.05);
                border-radius: 8px;
                text-align: center;
            }

            .af-stat-value {
                font-size: 24px;
                font-weight: 700;
                color: #667eea;
            }

            .af-stat-label {
                font-size: 12px;
                color: #a0aec0;
                margin-top: 4px;
            }

            .af-tools-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
            }

            .af-tool-card {
                padding: 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                cursor: pointer;
                transition: all 0.2s;
                text-align: center;
            }

            .af-tool-card:hover {
                background: rgba(255,255,255,0.1);
                transform: translateY(-4px);
            }

            .tool-icon {
                font-size: 32px;
                display: block;
                margin-bottom: 12px;
            }

            .tool-name {
                display: block;
                font-weight: 600;
                color: #e2e8f0;
                margin-bottom: 4px;
            }

            .tool-desc {
                display: block;
                font-size: 12px;
                color: #a0aec0;
            }

            .af-loading {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 40px;
                color: #a0aec0;
            }

            .af-spinner {
                width: 24px;
                height: 24px;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-top-color: #667eea;
                border-radius: 50%;
                animation: af-spin 1s linear infinite;
                margin-right: 12px;
            }

            @keyframes af-spin {
                to { transform: rotate(360deg); }
            }

            .af-error {
                padding: 16px;
                background: rgba(245, 101, 101, 0.1);
                border: 1px solid rgba(245, 101, 101, 0.3);
                border-radius: 8px;
                color: #fc8181;
            }

            .af-success {
                padding: 16px;
                background: rgba(72, 187, 120, 0.1);
                border: 1px solid rgba(72, 187, 120, 0.3);
                border-radius: 8px;
                color: #68d391;
            }

            .af-keyword-tag {
                display: inline-block;
                padding: 4px 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 20px;
                font-size: 12px;
                color: #fff;
                margin: 4px;
            }

            .af-entity-list {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .af-entity-item {
                padding: 6px 12px;
                background: rgba(102, 126, 234, 0.2);
                border-radius: 6px;
                font-size: 13px;
                color: #e2e8f0;
                font-family: monospace;
            }
        `;
        document.head.appendChild(styles);
    }

    /**
     * 绑定事件
     */
    _bindEvents() {
        // Tab切换
        this.panel.querySelectorAll('.af-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // 趋势分析选项显示/隐藏
        const trendCheckbox = document.getElementById('opt-trends');
        if (trendCheckbox) {
            trendCheckbox.addEventListener('change', (e) => {
                document.getElementById('trend-options').style.display = 
                    e.target.checked ? 'flex' : 'none';
            });
        }
    }

    /**
     * 切换Tab
     */
    switchTab(tabName) {
        this.currentTab = tabName;

        // 更新Tab按钮状态
        this.panel.querySelectorAll('.af-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // 更新面板显示
        this.panel.querySelectorAll('.af-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `panel-${tabName}`);
        });
    }

    /**
     * 打开面板
     */
    open() {
        this.panel.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    /**
     * 关闭面板
     */
    close() {
        this.panel.style.display = 'none';
        document.body.style.overflow = '';
    }

    /**
     * 数据分析
     */
    async analyzeData() {
        const inputEl = document.getElementById('analytics-input');
        const resultsEl = document.getElementById('analytics-results');

        let data;
        try {
            data = JSON.parse(inputEl.value);
            if (!Array.isArray(data)) {
                throw new Error('数据必须是数组格式');
            }
        } catch (e) {
            resultsEl.innerHTML = `<div class="af-error">数据格式错误: ${e.message}</div>`;
            resultsEl.classList.add('show');
            return;
        }

        const options = {
            clean_data: document.getElementById('opt-clean-data').checked,
            statistical_analysis: document.getElementById('opt-statistical').checked,
            cleaning_options: {
                remove_duplicates: true,
                fill_missing: 'auto',
                remove_outliers: false
            }
        };

        if (document.getElementById('opt-trends').checked) {
            options.time_column = document.getElementById('time-column').value;
            options.value_column = document.getElementById('value-column').value;
        }

        resultsEl.innerHTML = '<div class="af-loading"><div class="af-spinner"></div>分析中...</div>';
        resultsEl.classList.add('show');

        try {
            const response = await fetch('/api/analytics/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data, options })
            });

            const result = await response.json();

            if (result.success) {
                this._renderAnalyticsResults(result, resultsEl);
            } else {
                resultsEl.innerHTML = `<div class="af-error">分析失败: ${result.error}</div>`;
            }
        } catch (e) {
            resultsEl.innerHTML = `<div class="af-error">请求失败: ${e.message}</div>`;
        }
    }

    /**
     * 渲染数据分析结果
     */
    _renderAnalyticsResults(result, container) {
        const data = result.data;
        let html = '<h4>📊 分析结果</h4>';

        // 洞察
        if (result.insights && result.insights.length > 0) {
            html += '<div class="af-result-section"><h5>💡 数据洞察</h5>';
            result.insights.forEach(insight => {
                html += `<div class="af-insight-item">${insight}</div>`;
            });
            html += '</div>';
        }

        // 数据清洗结果
        if (data.data_cleaning) {
            const cleaning = data.data_cleaning;
            html += '<div class="af-result-section"><h5>🧹 数据清洗</h5>';
            html += '<div class="af-stat-grid">';
            html += `<div class="af-stat-card"><div class="af-stat-value">${cleaning.original_count}</div><div class="af-stat-label">原始数据</div></div>`;
            html += `<div class="af-stat-card"><div class="af-stat-value">${cleaning.cleaned_count}</div><div class="af-stat-label">清洗后</div></div>`;
            html += `<div class="af-stat-card"><div class="af-stat-value">${cleaning.quality_score}%</div><div class="af-stat-label">质量分数</div></div>`;
            html += '</div></div>';
        }

        // 统计分析
        if (data.statistical_analysis) {
            const stats = data.statistical_analysis;
            html += '<div class="af-result-section"><h5>📈 统计概览</h5>';
            html += '<div class="af-stat-grid">';
            html += `<div class="af-stat-card"><div class="af-stat-value">${stats.overview.total_rows}</div><div class="af-stat-label">数据行数</div></div>`;
            html += `<div class="af-stat-card"><div class="af-stat-value">${stats.overview.total_columns}</div><div class="af-stat-label">数据列数</div></div>`;
            html += '</div></div>';
        }

        // 趋势分析
        if (data.trend_analysis) {
            const trend = data.trend_analysis;
            html += '<div class="af-result-section"><h5>📉 趋势分析</h5>';
            if (trend.overall_trend) {
                html += `<div class="af-insight-item">趋势方向: ${trend.overall_trend.direction}</div>`;
                html += `<div class="af-insight-item">R²: ${trend.overall_trend.r_squared?.toFixed(3) || 'N/A'}</div>`;
            }
            if (trend.forecast && trend.forecast.length > 0) {
                html += `<div class="af-insight-item">预测值: ${trend.forecast.join(', ')}</div>`;
            }
            html += '</div>';
        }

        html += `<div style="margin-top:16px;font-size:12px;color:#a0aec0;text-align:right;">执行时间: ${result.execution_time?.toFixed(2) || 0}s</div>`;

        container.innerHTML = html;
    }

    /**
     * 处理文档
     */
    async processDocument() {
        const inputEl = document.getElementById('document-input');
        const resultsEl = document.getElementById('document-results');
        const content = inputEl.value.trim();

        if (!content) {
            resultsEl.innerHTML = '<div class="af-error">请输入文档内容</div>';
            resultsEl.classList.add('show');
            return;
        }

        const format = document.getElementById('document-format').value;
        const extractEntities = document.getElementById('doc-extract-entities').checked;
        const generateSummary = document.getElementById('doc-generate-summary').checked;
        const extractKeywords = document.getElementById('doc-extract-keywords').checked;

        resultsEl.innerHTML = '<div class="af-loading"><div class="af-spinner"></div>处理中...</div>';
        resultsEl.classList.add('show');

        try {
            const response = await fetch('/api/document/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content,
                    format,
                    extract_entities: extractEntities,
                    generate_summary: generateSummary,
                    extract_keywords: extractKeywords
                })
            });

            const result = await response.json();

            if (result.success) {
                this._renderDocumentResults(result, resultsEl);
            } else {
                resultsEl.innerHTML = `<div class="af-error">处理失败: ${result.error}</div>`;
            }
        } catch (e) {
            resultsEl.innerHTML = `<div class="af-error">请求失败: ${e.message}</div>`;
        }
    }

    /**
     * 渲染文档处理结果
     */
    _renderDocumentResults(result, container) {
        let html = '<h4>📝 处理结果</h4>';

        // 摘要
        if (result.summary) {
            html += '<div class="af-result-section"><h5>📋 文档摘要</h5>';
            html += `<div class="af-insight-item" style="border-left-color:#48bb78;">${result.summary}</div>`;
            html += '</div>';
        }

        // 关键词
        if (result.keywords && result.keywords.length > 0) {
            html += '<div class="af-result-section"><h5>🏷️ 关键词</h5>';
            html += '<div>';
            result.keywords.forEach(keyword => {
                html += `<span class="af-keyword-tag">${keyword}</span>`;
            });
            html += '</div></div>';
        }

        // 提取的实体
        if (result.extracted_data) {
            const entities = result.extracted_data;
            const hasEntities = Object.values(entities).some(arr => arr.length > 0);

            if (hasEntities) {
                html += '<div class="af-result-section"><h5>🔍 提取的实体</h5>';

                if (entities.emails && entities.emails.length > 0) {
                    html += '<p style="font-size:12px;color:#a0aec0;margin:8px 0 4px;">邮箱:</p>';
                    html += '<div class="af-entity-list">';
                    entities.emails.forEach(email => {
                        html += `<span class="af-entity-item">${email}</span>`;
                    });
                    html += '</div>';
                }

                if (entities.urls && entities.urls.length > 0) {
                    html += '<p style="font-size:12px;color:#a0aec0;margin:8px 0 4px;">URL:</p>';
                    html += '<div class="af-entity-list">';
                    entities.urls.forEach(url => {
                        html += `<span class="af-entity-item">${url}</span>`;
                    });
                    html += '</div>';
                }

                if (entities.phones && entities.phones.length > 0) {
                    html += '<p style="font-size:12px;color:#a0aec0;margin:8px 0 4px;">电话:</p>';
                    html += '<div class="af-entity-list">';
                    entities.phones.forEach(phone => {
                        html += `<span class="af-entity-item">${phone}</span>`;
                    });
                    html += '</div>';
                }

                if (entities.dates && entities.dates.length > 0) {
                    html += '<p style="font-size:12px;color:#a0aec0;margin:8px 0 4px;">日期:</p>';
                    html += '<div class="af-entity-list">';
                    entities.dates.forEach(date => {
                        html += `<span class="af-entity-item">${date}</span>`;
                    });
                    html += '</div>';
                }

                html += '</div>';
            }
        }

        // 元数据
        if (result.metadata) {
            html += '<div class="af-result-section"><h5>📊 元数据</h5>';
            html += '<div style="font-size:13px;color:#a0aec0;">';
            html += `<div>格式: ${result.metadata.format}</div>`;
            if (result.metadata.header_count !== undefined) {
                html += `<div>标题数: ${result.metadata.header_count}</div>`;
            }
            html += '</div></div>';
        }

        html += `<div style="margin-top:16px;font-size:12px;color:#a0aec0;text-align:right;">处理时间: ${result.processing_time?.toFixed(3) || 0}s</div>`;

        container.innerHTML = html;
    }

    /**
     * 打开工具
     */
    openTool(toolName) {
        switch(toolName) {
            case 'summarizer':
                this.switchTab('document');
                setTimeout(() => {
                    document.getElementById('doc-extract-entities').checked = false;
                    document.getElementById('doc-generate-summary').checked = true;
                    document.getElementById('doc-extract-keywords').checked = true;
                }, 100);
                break;
            case 'entity-extractor':
                this.switchTab('document');
                setTimeout(() => {
                    document.getElementById('doc-extract-entities').checked = true;
                    document.getElementById('doc-generate-summary').checked = false;
                    document.getElementById('doc-extract-keywords').checked = false;
                }, 100);
                break;
            case 'format-converter':
                this.switchTab('document');
                break;
            case 'data-cleaner':
                this.switchTab('analytics');
                setTimeout(() => {
                    document.getElementById('opt-clean-data').checked = true;
                    document.getElementById('opt-statistical').checked = false;
                    document.getElementById('opt-trends').checked = false;
                }, 100);
                break;
        }
    }
}

// 初始化全局实例
let advancedFeatures;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    advancedFeatures = new AdvancedFeaturesManager();
    advancedFeatures.close(); // 初始状态关闭
});

// 添加打开按钮到主界面
function addAdvancedFeaturesButton() {
    const toolbar = document.querySelector('.toolbar, .header-actions, nav');
    if (toolbar && !document.getElementById('af-open-btn')) {
        const btn = document.createElement('button');
        btn.id = 'af-open-btn';
        btn.className = 'af-open-btn';
        btn.innerHTML = '🔮 高级功能';
        btn.onclick = () => advancedFeatures.open();
        toolbar.appendChild(btn);

        // 添加按钮样式
        const style = document.createElement('style');
        style.textContent = `
            .af-open-btn {
                padding: 8px 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 8px;
                color: #fff;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
                margin-left: 8px;
            }
            .af-open-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
        `;
        document.head.appendChild(style);
    }
}

// 延迟添加按钮
setTimeout(addAdvancedFeaturesButton, 2000);
