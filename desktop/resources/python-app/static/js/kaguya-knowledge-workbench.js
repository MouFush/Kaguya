// Template analytics and knowledge workbench extracted from the main shell.
        function knowledgeGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function knowledgePost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
        }

        function loadTemplateAnalysis() {
            const range = document.getElementById('templateAnalysisRange')?.value || '7d';
            knowledgeGet('/templates/analysis?range=' + range)
                .then(data => {
                    if (data.success) {
                        const el = (id) => document.getElementById(id);
                        if (el('workbenchTemplateCount')) el('workbenchTemplateCount').textContent = data.stats.total_templates || getAllTemplates().length;
                        if (el('workbenchFavoriteCount')) el('workbenchFavoriteCount').textContent = data.stats.favorites || PROMPT_FAVORITES.length;
                        if (el('workbenchUsageCount')) el('workbenchUsageCount').textContent = data.stats.usage || Object.values(PROMPT_USAGE).reduce((a,b) => a+b, 0);
                        if (el('workbenchCustomCount')) el('workbenchCustomCount').textContent = data.stats.custom || CUSTOM_TEMPLATES.length;
                    }
                }).catch(() => {});
        }

        function exportTemplateReport() {
            const allTpls = getAllTemplates();
            const report = {
                exportTime: new Date().toISOString(),
                totalTemplates: allTpls.length,
                presetTemplates: PROMPT_TEMPLATES.length,
                customTemplates: CUSTOM_TEMPLATES.length,
                favorites: PROMPT_FAVORITES.length,
                totalUsage: Object.values(PROMPT_USAGE).reduce((a,b) => a+b, 0),
                usageByTemplate: PROMPT_USAGE,
                templates: allTpls.map(t => ({
                    id: t.id, name: t.name, category: t.category, source: t.source,
                    tags: t.tags || [], isFavorite: PROMPT_FAVORITES.includes(t.id),
                    usageCount: PROMPT_USAGE[t.id] || 0, isCustom: !!t.custom
                }))
            };
            const blob = new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'template_report_' + new Date().toISOString().slice(0,10) + '.json';
            a.click(); URL.revokeObjectURL(url);
            showToast('报告已导出');
        }

        function refreshRagStats() {
            knowledgeGet('/rag/stats')
                .then(data => {
                    if (data.success) {
                        const docsEl = $('ragStatDocs');
                        const chunksEl = $('ragStatChunks');
                        const charsEl = $('ragStatChars');
                        const vectorsEl = document.getElementById('ragStatVectors');
                        if (docsEl) docsEl.textContent = data.stats.docs || 0;
                        if (chunksEl) chunksEl.textContent = data.stats.chunks || 0;
                        if (charsEl) charsEl.textContent = data.stats.chars || 0;
                        if (vectorsEl) vectorsEl.textContent = data.stats.vectors || 0;
                    }
                });
        }

        function openBatchImportModal() {
            const modal = createModal('batchImportModal', 'Batch Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📤 批量导入文档</h3>
                        <button class="modal-close" onclick="closeModal('batchImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">选择文件（支持多选）</label>
                            <input type="file" id="batchFiles" multiple accept=".txt,.md,.pdf,.docx,.html,.json,.csv" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">目标分类</label>
                            <select class="project-input" id="batchCategory" style="width:100%;">
                                <option value="doc">📄 文档</option>
                                <option value="code">💻 代码</option>
                                <option value="data">📊 数据</option>
                                <option value="web">🌐 网页</option>
                                <option value="text">📝 文本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('batchImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeBatchImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeBatchImport() {
            showToast('正在批量导入...');
            closeModal('batchImportModal');
        }

        function openUrlImportModal() {
            const modal = createModal('urlImportModal', 'URL Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>🌐 网页抓取</h3>
                        <button class="modal-close" onclick="closeModal('urlImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">网页 URL</label>
                            <input class="project-input" id="importUrl" placeholder="https://example.com" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">抓取深度</label>
                            <select class="project-input" id="crawlDepth" style="width:100%;">
                                <option value="1">仅当前页面</option>
                                <option value="2">2 层深度</option>
                                <option value="3">3 层深度</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('urlImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeUrlImport()">抓取</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeUrlImport() {
            const url = document.getElementById('importUrl').value;
            if (!url) {
                showToast('请输入 URL');
                return;
            }
            showToast('正在抓取网页...');
            closeModal('urlImportModal');
        }

        function openGitImportModal() {
            const modal = createModal('gitImportModal', 'Git Import', '', {maxWidth: '500px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📦 Git 仓库导入</h3>
                        <button class="modal-close" onclick="closeModal('gitImportModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">仓库 URL</label>
                            <input class="project-input" id="gitRepoUrl" placeholder="https://github.com/user/repo" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">分支</label>
                            <input class="project-input" id="gitBranch" placeholder="main" value="main" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">文件类型</label>
                            <div style="display:flex;gap:10px;flex-wrap:wrap;">
                                <label style="font-size:11px;"><input type="checkbox" checked> .py</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .js</label>
                                <label style="font-size:11px;"><input type="checkbox" checked> .md</label>
                                <label style="font-size:11px;"><input type="checkbox"> .txt</label>
                            </div>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('gitImportModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="executeGitImport()">导入</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function executeGitImport() {
            const url = document.getElementById('gitRepoUrl').value;
            if (!url) {
                showToast('请输入仓库 URL');
                return;
            }
            showToast('正在导入仓库...');
            closeModal('gitImportModal');
        }

        function openRagSettingsModal() {
            showToast('打开 RAG 设置面板');
        }

        function openKnowledgeGraphModal() {
            const modal = createModal('knowledgeGraphModal', 'Knowledge Graph', '', {maxWidth: '600px'});
            modal.querySelector('.modal-body').innerHTML =
            modal.innerHTML = `
                <div class="modal-content" style="max-width:800px;">
                    <div class="modal-header">
                        <h3>🧠 知识图谱</h3>
                        <button class="modal-close" onclick="closeModal('knowledgeGraphModal')">×</button>
                    </div>
                    <div class="modal-body" style="height:500px;">
                        <div class="graph-container" id="graphContainer">
                            <div class="graph-placeholder">
                                <div class="graph-visualization">
                                    <div class="node-center">知识库</div>
                                    <div class="node-ring">
                                        <div class="node-item">概念</div>
                                        <div class="node-item">实体</div>
                                        <div class="node-item">关系</div>
                                        <div class="node-item">属性</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function buildKnowledgeGraph() {
            showToast('正在构建知识图谱...');
            knowledgePost('/rag/build-graph')
                .then(data => {
                    if (data.success) {
                        document.getElementById('graphNodes').textContent = data.nodes || '--';
                        document.getElementById('graphEdges').textContent = data.edges || '--';
                        showToast('知识图谱构建完成');
                    }
                });
        }

        function loadRagAnalysis() {
            const range = document.getElementById('ragAnalysisRange')?.value || '7d';
            knowledgeGet('/rag/analysis?range=' + range)
                .then(data => {
                    if (data.success) {
                        document.getElementById('ragQueryCount').textContent = data.analysis.queries || '--';
                        document.getElementById('ragHitRate').textContent = data.analysis.hit_rate || '--';
                        document.getElementById('ragLatency').textContent = data.analysis.latency || '--';
                        document.getElementById('ragTopDoc').textContent = data.analysis.top_doc || '--';
                    }
                });
        }

        function exportRagReport() {
            showToast('正在导出 RAG 报告...');
        }

        function openVectorSettingsModal() {
            showToast('打开向量化设置面板');
        }
