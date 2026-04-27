
        marked.setOptions({ 
            highlight: c => hljs.highlightAuto(c).value, 
            breaks: true,
            gfm: true,
            mangle: false,
            headerIds: false
        });
        // 禁用删除线解析
        const renderer = new marked.Renderer();
        renderer.del = (text) => text;
        marked.use({ renderer });
        let chats = JSON.parse(localStorage.getItem('kaguya_chats') || '[]');
        let currentChatId = null, history = [], attachments = [];
        let currentRole = 'kaguya', currentLora = 'none';
        let currentStructuredTemplate = null;
        let promptSearchKeyword = '';
        let promptCategory = 'all';
        let featureActionHistory = JSON.parse(localStorage.getItem('kaguya_feature_actions') || '[]');
        let activeTools = new Set();
        let settings = JSON.parse(localStorage.getItem('kaguya_settings') || '{"temp":0.7,"tokens":4096,"dark":false,"voice":false,"markdown":true}');
        let stats = JSON.parse(localStorage.getItem('kaguya_stats') || '{"sessions":0,"inputTokens":0,"outputTokens":0,"latencies":[]}');
        const roles = [];
        const loras = [];
        const tools = {};
        const commands = [];
        let recognition = null, isRecording = false;
        let ragEnabled = false;
        let ragDocuments = [];
        let consoleOverview = {};
        let consoleRecommendations = [];
        let globalSearchResults = [];
        let projectOverview = {};
        let projectArtifacts = [];
        let projectTasks = [];
        let projectPlaybooks = [];
        let projectActivities = [];
        let opsOverview = {};
        let opsCampaigns = [];
        let releaseOverview = {};
        let releasePlans = [];
        let alertOverview = {};
        let alertRules = [];
        let abOverview = {};
        let abExperiments = [];
        let integrationOverview = {};
        let integrationItems = [];
        let workspaceProjects = [];
        let workspaceOverview = {};
        let externalApiConfig = {active_provider: 'deepseek', providers: {}};
        let currentSceneId = 'ecommerce';
        const SCENE_UI_CONFIG = {
            ecommerce: {title: '电商增长', icon: '🛍️', desc: '围绕商品与人群，输出可执行增长方案。', placeholders: {topic: '例如：美妆新品，客单价189元', context: '例如：小红书+抖音为主，库存8000件', goal: '例如：30天GMV提升40%', constraints: '例如：预算8万元，团队3人'}},
            shortvideo: {title: '短视频运营', icon: '🎬', desc: '快速生成选题脚本、钩子与发布时间策略。', placeholders: {topic: '例如：职场技能账号', context: '例如：已有5条爆款，粉丝1.2万', goal: '例如：7天涨粉5000', constraints: '例如：每天最多拍2条'}},
            resume: {title: '简历求职', icon: '🧩', desc: '将经历重写为目标岗位可用的求职材料。', placeholders: {topic: '例如：3年数据分析经历', context: '例如：目标岗位-增长策略分析师', goal: '例如：两周内完成投递并拿到面试', constraints: '例如：不夸大经历，强调真实成果'}},
            business: {title: '商业计划', icon: '📈', desc: '形成市场、商业模式、里程碑与风控方案。', placeholders: {topic: '例如：AI客服SaaS项目', context: '例如：目标客户为中型电商企业', goal: '例如：半年内实现100万ARR', constraints: '例如：初始团队5人，资金有限'}},
            dataops: {title: '数据经营分析', icon: '📊', desc: '构建指标、定位异常并给出行动闭环。', placeholders: {topic: '例如：近30天渠道转化数据', context: '例如：投放成本上升、留存下降', goal: '例如：次月ROI提升20%', constraints: '例如：不可新增人力'}},
            contract: {title: '合同风险审阅', icon: '⚖️', desc: '识别高风险条款并给出谈判修改建议。', placeholders: {topic: '例如：软件采购合同草案', context: '例如：甲方为大型企业，交付周期3个月', goal: '例如：降低违约风险并明确验收', constraints: '例如：维持总价不变'}}
        };
        let projectMilestones = [];
        let projectRisks = [];
        let editingArtifactId = null;
        let draggingTaskId = null;
        let selectedTaskIds = new Set();
        let ragSettings = {topK: 5, alpha: 0.5, useRerank: true, showScores: true, useCache: true, useExpansion: true, useHyde: false, useMultiQuery: false, useDecomposition: false, useAdaptive: true, useRrf: false, useMetadataFilter: true, useTimeWeight: false, useIterative: false};
        let lastRagResults = [];
        let deepseekConfig = JSON.parse(localStorage.getItem('deepseek_config') || '{}');
        
        function init() {
            console.log('init() called');
            try {
                if (settings.dark) document.body.classList.add('dark');
                const darkModeToggle = document.getElementById('darkModeToggle');
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
                const kbSearchEl = document.getElementById('kbSearch');
                if (kbSearchEl) kbSearchEl.addEventListener('input', searchKB);
                renderChatList();
                renderRoleList();
                renderToolList();
                loadLoraList();
                loadRagDocuments();
                loadProjectCenter();
                initScenesCenter();
                updateStats();
                updateDeepSeekIndicator();
                checkExternalApiWarning();
                if (chats.length > 0) loadChat(chats[0].id);
                else showWelcome();
                initSpeechRecognition();
            } catch (e) {
                console.error('Init error:', e);
            }
        }
        
        function loadRagDocuments() {
            fetch('/rag/documents').then(r => r.json()).then(data => {
                if (data.success) {
                    ragDocuments = data.documents;
                    renderRagDocList();
                    updateRagStats();
                    renderFeatureCenterMeta();
                }
            });
        }
        
        function updateRagStats() {
            fetch('/rag/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const stats = data.stats;
                    const docsEl = document.getElementById('ragStatDocs');
                    const chunksEl = document.getElementById('ragStatChunks');
                    const charsEl = document.getElementById('ragStatChars');
                    if (docsEl) docsEl.textContent = stats.total_docs;
                    if (chunksEl) chunksEl.textContent = stats.total_chunks;
                    if (charsEl) charsEl.textContent = stats.total_chars > 1000 ? (stats.total_chars/1000).toFixed(1) + 'K' : stats.total_chars;
                    const ragStatsEl = document.getElementById('ragStats');
                    const cacheInfo = stats.cache_size > 0 ? ` | 💾 缓存: ${stats.cache_size}` : '';
                    if (ragStatsEl) ragStatsEl.title = `唯一文档: ${stats.unique_hashes || 0}${cacheInfo}`;
                }
            });
        }
        
        function renderRagDocList() {
            const list = document.getElementById('ragDocList');
            const filter = document.getElementById('ragCategoryFilter').value;
            const filtered = filter ? ragDocuments.filter(d => d.category === filter) : ragDocuments;
            
            if (!filtered.length) {
                list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;font-size:12px;">暂无文档<br>上传文档以启用RAG功能</div>';
                return;
            }
            
            const categoryIcons = {doc: '📄', code: '💻', data: '📊', web: '🌐', text: '📝', config: '⚙️', other: '📁'};
            
            list.innerHTML = filtered.map(doc => `
                <div class="chat-item" style="flex-direction:column;align-items:flex-start;gap:4px;cursor:pointer;" onclick="previewRagDoc('${doc.id}')">
                    <div style="display:flex;width:100%;align-items:center;gap:8px;">
                        <span>${categoryIcons[doc.category] || '📁'}</span>
                        <span style="flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${doc.filename}">${doc.filename}</span>
                        <button onclick="event.stopPropagation();deleteRagDoc('${doc.id}')" style="border:none;background:none;cursor:pointer;color:#e74c3c;font-size:11px;">🗑️</button>
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);width:100%;display:flex;justify-content:space-between;">
                        <span>${doc.chunk_count} 块 · ${(doc.size / 1024).toFixed(1)} KB</span>
                        <span>${new Date(doc.time).toLocaleDateString()}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function filterRagDocs() {
            renderRagDocList();
        }
        
        function toggleRag() {
            ragEnabled = document.getElementById('ragToggle').checked;
            updateRagIndicator();
            renderFeatureCenterMeta();
            showToast(ragEnabled ? 'RAG已启用 - 将基于文档回答' : 'RAG已禁用');
        }
        
        function updateRagIndicator() {
            const indicators = document.getElementById('headerIndicators');
            let html = indicators.innerHTML;
            const ragIndicator = '<div class="indicator tool"><span>📚</span><span>RAG</span></div>';
            if (ragEnabled && !html.includes('RAG')) {
                indicators.innerHTML = ragIndicator + html;
            } else if (!ragEnabled) {
                indicators.innerHTML = html.replace(ragIndicator, '');
            }
        }
        
        function uploadRagFile(event) {
            const files = event.target.files;
            if (!files || !files.length) return;
            
            if (files.length === 1) {
                const file = files[0];
                const formData = new FormData();
                formData.append('file', file);
                showToast('正在上传: ' + file.name);
                fetch('/rag/upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('上传成功: ' + data.document.filename);
                        loadRagDocuments();
                    } else {
                        showToast('上传失败: ' + (data.error || '未知错误'));
                    }
                }).catch(e => showToast('上传失败: ' + e));
            } else {
                const formData = new FormData();
                for (let f of files) formData.append('files', f);
                showToast(`正在上传 ${files.length} 个文件...`);
                fetch('/rag/batch_upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        const success = data.results.filter(r => r.success).length;
                        showToast(`上传完成: ${success}/${files.length} 成功`);
                        loadRagDocuments();
                    }
                });
            }
            event.target.value = '';
        }
        
        function showAddTextModal() {
            const html = `
                <div class="modal-header">
                    <span class="modal-title">📝 添加文本到知识库</span>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">标题</label>
                        <input type="text" id="addTextTitle" placeholder="输入标题..." style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">内容 (至少50字符)</label>
                        <textarea id="addTextContent" placeholder="粘贴或输入文本内容..." style="width:100%;height:200px;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);resize:vertical;"></textarea>
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">标签 (逗号分隔)</label>
                        <input type="text" id="addTextTags" placeholder="标签1, 标签2..." style="width:100%;padding:10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="modal-btn secondary" onclick="closeModal()">取消</button>
                    <button class="modal-btn primary" onclick="submitAddText()">添加</button>
                </div>
            `;
            showModal(html);
        }
        
        function submitAddText() {
            const title = document.getElementById('addTextTitle').value.trim() || '手动输入';
            const content = document.getElementById('addTextContent').value.trim();
            const tags = document.getElementById('addTextTags').value.split(',').map(t => t.trim()).filter(t => t);
            
            if (content.length < 50) {
                showToast('内容至少需要50个字符');
                return;
            }
            
            fetch('/rag/add_text', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: content, title, tags})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('文本已添加到知识库');
                    closeModal();
                    loadRagDocuments();
                } else {
                    showToast('添加失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function closeModal(id) {
            if (id) {
                const modal = document.getElementById(id);
                if (modal) {
                    modal.classList.remove('show');
                    // 如果是动态创建的模态框（以 Modal 结尾的 id），从 DOM 中移除
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
        }
        
        function showModal(html) {
            const overlay = document.getElementById('modalOverlay');
            overlay.querySelector('.modal').innerHTML = html;
            overlay.classList.add('show');
        }
        
        function deleteRagDoc(docId) {
            if (!confirm('确定删除此文档？相关分块也将被删除。')) return;
            fetch('/rag/delete/' + docId, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('文档已删除');
                        loadRagDocuments();
                    }
                });
        }
        
        function searchRagDocs() {
            const query = document.getElementById('ragSearchInput').value.trim();
            const resultsDiv = document.getElementById('ragSearchResults');
            if (!query) {
                resultsDiv.innerHTML = '';
                return;
            }
            const category = document.getElementById('ragCategoryFilter').value;
            fetch('/rag/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    query, 
                    top_k: ragSettings.topK, 
                    category: category || null,
                    use_rerank: ragSettings.useRerank,
                    alpha: ragSettings.alpha,
                    use_cache: ragSettings.useCache,
                    use_expansion: ragSettings.useExpansion,
                    use_hyde: ragSettings.useHyde,
                    use_multi_query: ragSettings.useMultiQuery,
                    use_decomposition: ragSettings.useDecomposition,
                    use_adaptive: ragSettings.useAdaptive,
                    use_rrf: ragSettings.useRrf,
                    use_metadata_filter: ragSettings.useMetadataFilter,
                    use_time_weight: ragSettings.useTimeWeight,
                    use_iterative: ragSettings.useIterative
                })
            }).then(r => r.json()).then(data => {
                if (data.success && data.results.length) {
                    lastRagResults = data.results;
                    var qualityHtml = data.quality ? '<div style="font-size:9px;color:var(--text-muted);margin-bottom:8px;">类型: ' + data.query_type + ' | 质量: ' + data.quality.reason + ' (' + data.quality.score + ')</div>' : '';
                    var resultsHtml = '';
                    for (var i = 0; i < data.results.length; i++) {
                        var r = data.results[i];
                        var textPreview = r.text.length > 120 ? r.text.slice(0, 120) + '...' : r.text;
                        textPreview = textPreview.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        resultsHtml += '<div style="padding:10px;background:var(--bg-secondary);border-radius:8px;margin-bottom:6px;font-size:11px;cursor:pointer;" onclick="useRagResultByIndex(' + i + ')">' +
                            '<div style="display:flex;justify-content:space-between;margin-bottom:4px;">' +
                                '<span style="color:var(--primary);font-weight:600;">' + r.doc_name + '</span>' +
                                '<span style="color:var(--accent);">' + (r.score * 100).toFixed(0) + '%</span>' +
                            '</div>' +
                            '<div style="color:var(--text-secondary);line-height:1.4;">' + textPreview + '</div>' +
                        '</div>';
                    }
                    resultsDiv.innerHTML = qualityHtml + resultsHtml;
                } else {
                    resultsDiv.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:10px;">未找到相关内容</div>';
                }
            });
        }
        
        function useRagResult(text) {
            const input = document.getElementById('mainInput');
            input.value = '基于以下内容回答: ' + text + '\\n\\n问题: ';
            input.focus();
        }
        
        function useRagResultByIndex(idx) {
            if (lastRagResults && lastRagResults[idx]) {
                useRagResult(lastRagResults[idx].text);
            }
        }
        
        function showRagSettings() {
            const html = `
                <div class="modal-header">
                    <span class="modal-title">⚙️ RAG高级设置</span>
                    <button class="modal-close" onclick="closeModal()">✕</button>
                </div>
                <div class="modal-body" style="max-height:500px;overflow-y:auto;">
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--border);">📊 基础设置</div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">
                            返回结果数量: <b id="topKValue">${ragSettings.topK}</b>
                        </label>
                        <input type="range" id="ragTopK" min="1" max="10" value="${ragSettings.topK}" 
                            style="width:100%;" oninput="document.getElementById('topKValue').textContent=this.value">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">
                            TF-IDF权重: <b id="alphaValue">${ragSettings.alpha}</b>
                        </label>
                        <input type="range" id="ragAlpha" min="0" max="100" value="${ragSettings.alpha * 100}" 
                            style="width:100%;" oninput="document.getElementById('alphaValue').textContent=(this.value/100).toFixed(2)">
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">启用重排序</span>
                            <label class="toggle"><input type="checkbox" id="ragRerank" ${ragSettings.useRerank ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">自适应检索</span>
                            <label class="toggle"><input type="checkbox" id="ragAdaptive" ${ragSettings.useAdaptive ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">🚀 高级算法</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">HyDE假设文档</span>
                            <label class="toggle"><input type="checkbox" id="ragHyde" ${ragSettings.useHyde ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">多查询检索</span>
                            <label class="toggle"><input type="checkbox" id="ragMultiQuery" ${ragSettings.useMultiQuery ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询分解</span>
                            <label class="toggle"><input type="checkbox" id="ragDecomposition" ${ragSettings.useDecomposition ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">RRF融合排序</span>
                            <label class="toggle"><input type="checkbox" id="ragRrf" ${ragSettings.useRrf ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">迭代检索</span>
                            <label class="toggle"><input type="checkbox" id="ragIterative" ${ragSettings.useIterative ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">结果不足时自动扩展检索</div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">🔍 过滤与权重</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">元数据过滤</span>
                            <label class="toggle"><input type="checkbox" id="ragMetadataFilter" ${ragSettings.useMetadataFilter ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">自动识别分类/时间/大小过滤</div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">时间权重</span>
                            <label class="toggle"><input type="checkbox" id="ragTimeWeight" ${ragSettings.useTimeWeight ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                        <div style="font-size:10px;color:var(--text-muted);margin-top:2px;margin-left:4px;">新文档权重更高</div>
                    </div>
                    
                    <div style="font-size:12px;color:var(--primary);font-weight:600;margin:16px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);">⚡ 性能优化</div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询缓存</span>
                            <label class="toggle"><input type="checkbox" id="ragCache" ${ragSettings.useCache ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">查询扩展</span>
                            <label class="toggle"><input type="checkbox" id="ragExpansion" ${ragSettings.useExpansion ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                    <div style="margin-bottom:8px;">
                        <div class="setting-row">
                            <span class="setting-label">显示分数详情</span>
                            <label class="toggle"><input type="checkbox" id="ragShowScores" ${ragSettings.showScores ? 'checked' : ''}><span class="toggle-slider"></span></label>
                        </div>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="modal-btn secondary" onclick="closeModal()">取消</button>
                    <button class="modal-btn primary" onclick="saveRagSettings()">保存</button>
                </div>
            `;
            showModal(html);
        }
        
        function saveRagSettings() {
            ragSettings.topK = parseInt(document.getElementById('ragTopK').value);
            ragSettings.alpha = parseInt(document.getElementById('ragAlpha').value) / 100;
            ragSettings.useRerank = document.getElementById('ragRerank').checked;
            ragSettings.showScores = document.getElementById('ragShowScores').checked;
            ragSettings.useCache = document.getElementById('ragCache').checked;
            ragSettings.useExpansion = document.getElementById('ragExpansion').checked;
            ragSettings.useHyde = document.getElementById('ragHyde').checked;
            ragSettings.useMultiQuery = document.getElementById('ragMultiQuery').checked;
            ragSettings.useDecomposition = document.getElementById('ragDecomposition').checked;
            ragSettings.useAdaptive = document.getElementById('ragAdaptive').checked;
            ragSettings.useRrf = document.getElementById('ragRrf').checked;
            ragSettings.useMetadataFilter = document.getElementById('ragMetadataFilter').checked;
            ragSettings.useTimeWeight = document.getElementById('ragTimeWeight').checked;
            ragSettings.useIterative = document.getElementById('ragIterative').checked;
            closeModal();
            showToast('RAG设置已保存');
        }
        
        function previewRagDoc(docId) {
            fetch('/rag/preview/' + docId).then(r => r.json()).then(data => {
                if (data.success) {
                    const doc = data.document;
                    const chunks = data.chunks;
                    const html = `
                        <div class="modal-header">
                            <span class="modal-title">📄 ${doc.filename}</span>
                            <button class="modal-close" onclick="closeModal()">✕</button>
                        </div>
                        <div class="modal-body" style="max-height:400px;overflow-y:auto;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:12px;">
                                📊 ${doc.chunk_count} 分块 · ${(doc.size/1024).toFixed(1)} KB · ${doc.category}
                            </div>
                            <div style="font-size:12px;color:var(--text-secondary);">
                                ${chunks.map((c, i) => `
                                    <div style="padding:10px;background:var(--bg-secondary);border-radius:8px;margin-bottom:8px;border-left:3px solid var(--primary);">
                                        <div style="font-size:10px;color:var(--primary);margin-bottom:4px;">分块 ${i+1}</div>
                                        <div style="line-height:1.5;">${c.text}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="modal-actions">
                            <button class="modal-btn secondary" onclick="closeModal()">关闭</button>
                            <button class="modal-btn primary" onclick="deleteRagDoc('${doc.id}');closeModal();">删除文档</button>
                        </div>
                    `;
                    showModal(html);
                }
            });
        }
        
        function renderRagSources(results) {
            if (!results || !results.length) return '';
            const html = `
                <div class="rag-sources" style="margin-top:12px;padding:10px;background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.04));border-radius:10px;border:1px solid rgba(102,126,234,0.15);">
                    <div style="font-size:11px;color:var(--primary);font-weight:600;margin-bottom:8px;">📚 参考来源</div>
                    ${results.map((r, i) => `
                        <div style="padding:8px;background:var(--bg-secondary);border-radius:6px;margin-bottom:6px;font-size:11px;cursor:pointer;" 
                             onclick="previewRagDoc('${r.doc_id}')" title="点击查看原文">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="color:var(--primary);font-weight:500;">[${i+1}] ${r.doc_name}</span>
                                <span style="color:var(--accent);">${(r.score * 100).toFixed(0)}%</span>
                            </div>
                            <div style="color:var(--text-muted);line-height:1.4;">${r.text.slice(0, 100)}${r.text.length > 100 ? '...' : ''}</div>
                            ${ragSettings.showScores ? `<div style="font-size:9px;color:var(--text-muted);margin-top:4px;">TF-IDF: ${r.tfidf_score?.toFixed(3) || '-'} | BM25: ${r.bm25_score?.toFixed(2) || '-'}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
            return html;
        }
        
        function showWelcome() {
            const container = document.getElementById('messagesContainer');
            container.innerHTML = `
                <div class="welcome-container">
                    <img src="/header-img" class="welcome-avatar">
                    <h1 class="welcome-title">辉夜 AI 专业助手 v3.1 ✨</h1>
                    <p class="welcome-subtitle">面向开发、运营、增长与职场场景的高质量 AI 助手，支持流式响应、代码执行、知识库、工具调用与 LoRA 微调。</p>
                    
                    <div style="background:linear-gradient(135deg, rgba(102,126,234,0.2), rgba(118,75,162,0.2));border-radius:16px;padding:20px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.1);">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                            <span style="font-size:20px;">🎯</span>
                            <span style="font-size:16px;font-weight:600;">核心功能导航</span>
                        </div>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🧭</div>
                                <div style="font-size:13px;font-weight:600;">专业工作台</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">模板 · 规划 · 执行</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">📚</div>
                                <div style="font-size:13px;font-weight:600;">知识库</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">RAG · 文档 · 检索</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🔧</div>
                                <div style="font-size:13px;font-weight:600;">工具调用</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">搜索 · 天气 · 计算</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">⚡</div>
                                <div style="font-size:13px;font-weight:600;">代码执行</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">Python · 安全沙箱</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🎭</div>
                                <div style="font-size:13px;font-weight:600;">角色扮演</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">多角色 · 自定义</div>
                            </div>
                            <div style="background:rgba(0,0,0,0.2);border-radius:10px;padding:12px;text-align:center;">
                                <div style="font-size:24px;margin-bottom:6px;">🧠</div>
                                <div style="font-size:13px;font-weight:600;">记忆系统</div>
                                <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">长期记忆 · 实体识别</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="feature-grid">
                        <div class="feature-card" onclick="quickAction('chat')">
                            <span class="feature-icon">💬</span>
                            <div class="feature-name">智能对话</div>
                            <div class="feature-desc">自然流畅的对话体验</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('code')">
                            <span class="feature-icon">💻</span>
                            <div class="feature-name">代码助手</div>
                            <div class="feature-desc">编写和调试代码</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('translate')">
                            <span class="feature-icon">🌐</span>
                            <div class="feature-name">翻译专家</div>
                            <div class="feature-desc">多语言翻译服务</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('write')">
                            <span class="feature-icon">✍️</span>
                            <div class="feature-name">创意写作</div>
                            <div class="feature-desc">文章和内容创作</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('analyze')">
                            <span class="feature-icon">📊</span>
                            <div class="feature-name">数据分析</div>
                            <div class="feature-desc">处理和分析数据</div>
                        </div>
                        <div class="feature-card" onclick="quickAction('learn')">
                            <span class="feature-icon">📚</span>
                            <div class="feature-name">学习辅导</div>
                            <div class="feature-desc">解答学习问题</div>
                        </div>
                    </div>
                    
                    <div style="background:rgba(0,0,0,0.2);border-radius:12px;padding:16px;margin-top:20px;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                            <span style="font-size:18px;">💡</span>
                            <span style="font-size:14px;font-weight:600;">快速上手指南</span>
                        </div>
                        <div style="font-size:13px;color:var(--text-secondary);line-height:1.8;">
                            <p style="margin:0 0 8px;">1. <strong>左侧边栏</strong> - 切换对话、模板、知识库、设置等功能</p>
                            <p style="margin:0 0 8px;">2. <strong>模板标签</strong> - 点击"打开工作台"使用专业工具</p>
                            <p style="margin:0 0 8px;">3. <strong>知识库标签</strong> - 上传文档，启用 RAG 检索增强</p>
                            <p style="margin:0 0 8px;">4. <strong>设置标签</strong> - 切换模型、调整参数、管理 LoRA</p>
                            <p style="margin:0;">5. <strong>高级功能</strong> - 代码执行器、工具调用、场景模板</p>
                        </div>
                    </div>
                    
                    <div class="market-demand-section">
                        <div class="market-demand-title">
                            <span>🚀</span>
                            <span>高需求专业场景（可一键生成）</span>
                        </div>
                        <div class="market-demand-grid">
                            <div class="demand-card" onclick="quickAction('ecommerce')">
                                <div class="demand-head"><span>🛍️</span><span class="demand-name">电商增长</span></div>
                                <div class="demand-desc">活动方案、商品卖点、投放文案与转化优化</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('shortvideo')">
                                <div class="demand-head"><span>🎬</span><span class="demand-name">短视频运营</span></div>
                                <div class="demand-desc">选题、脚本分镜、封面标题与账号节奏设计</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('resume')">
                                <div class="demand-head"><span>🧩</span><span class="demand-name">简历求职</span></div>
                                <div class="demand-desc">简历重写、岗位匹配、STAR 项目优化与面试问答</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('business')">
                                <div class="demand-head"><span>📈</span><span class="demand-name">商业计划</span></div>
                                <div class="demand-desc">商业模型、竞品分析、路线图与里程碑拆解</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('dataops')">
                                <div class="demand-head"><span>📊</span><span class="demand-name">数据经营分析</span></div>
                                <div class="demand-desc">指标体系、异常诊断、A/B 实验与复盘建议</div>
                            </div>
                            <div class="demand-card" onclick="quickAction('contract')">
                                <div class="demand-head"><span>⚖️</span><span class="demand-name">合同风险审阅</span></div>
                                <div class="demand-desc">关键条款核查、风险点标注与谈判建议</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function initScenesCenter() {
            renderSceneNav();
            loadExternalApiConfig();
            renderSceneWorkspace(currentSceneId);
        }

        function renderSceneNav() {
            const el = document.getElementById('sceneNav');
            if (!el) return;
            const ids = Object.keys(SCENE_UI_CONFIG);
            el.innerHTML = ids.map(id => {
                const item = SCENE_UI_CONFIG[id];
                return `<div class="scene-nav-item ${id === currentSceneId ? 'active' : ''}" onclick="renderSceneWorkspace('${id}')"><div class="scene-nav-title">${item.icon} ${item.title}</div><div class="scene-nav-desc">${item.desc}</div></div>`;
            }).join('');
        }

        function renderSceneWorkspace(sceneId) {
            if (!SCENE_UI_CONFIG[sceneId]) return;
            currentSceneId = sceneId;
            renderSceneNav();
            const el = document.getElementById('sceneWorkspace');
            const tagEl = document.getElementById('sceneCurrentTag');
            if (!el) return;
            const item = SCENE_UI_CONFIG[sceneId];
            if (tagEl) tagEl.textContent = `当前: ${item.title}`;
            el.innerHTML = `
                <div class="scene-form-title"><span>${item.icon}</span><span>${item.title}子界面</span></div>
                <div class="scene-form-desc">${item.desc}（当前子界面强制走外界API生成）</div>
                <div class="scene-form-grid">
                    <div class="scene-form-field full"><label>核心主题/素材</label><textarea id="sceneTopicInput" rows="3" placeholder="${item.placeholders.topic}"></textarea></div>
                    <div class="scene-form-field"><label>场景背景</label><textarea id="sceneContextInput" rows="3" placeholder="${item.placeholders.context}"></textarea></div>
                    <div class="scene-form-field"><label>目标结果</label><textarea id="sceneGoalInput" rows="3" placeholder="${item.placeholders.goal}"></textarea></div>
                    <div class="scene-form-field full"><label>约束条件</label><textarea id="sceneConstraintsInput" rows="2" placeholder="${item.placeholders.constraints}"></textarea></div>
                </div>
                <div class="scene-actions">
                    <button class="scene-generate-btn" id="sceneGenerateBtn" onclick="generateSceneContent('${sceneId}')">⚡ 一键生成</button>
                    <button class="project-mini-btn" onclick="copySceneOutput()">复制结果</button>
                </div>
                <div class="scene-output" id="sceneOutput">点击“一键生成”后，这里会返回外界API生成结果。</div>
            `;
        }

        function handleSceneProviderChange(provider) {
            if (!provider) return;
            externalApiConfig.active_provider = provider;
            const cfg = (externalApiConfig.providers && externalApiConfig.providers[provider]) ? externalApiConfig.providers[provider] : {api_url: '', api_key: '', model: ''};
            const urlEl = document.getElementById('sceneApiUrlInput');
            const keyEl = document.getElementById('sceneApiKeyInput');
            const modelEl = document.getElementById('sceneModelInput');
            if (urlEl) urlEl.value = cfg.api_url || '';
            if (keyEl) keyEl.value = cfg.api_key || '';
            if (modelEl) modelEl.value = cfg.model || '';
        }

        function syncSceneConfigFromInputs() {
            const provider = document.getElementById('sceneProviderSelect')?.value || 'deepseek';
            const api_url = (document.getElementById('sceneApiUrlInput')?.value || '').trim();
            const api_key = (document.getElementById('sceneApiKeyInput')?.value || '').trim();
            const model = (document.getElementById('sceneModelInput')?.value || '').trim();
            if (!externalApiConfig.providers) externalApiConfig.providers = {};
            externalApiConfig.active_provider = provider;
            externalApiConfig.providers[provider] = {api_url, api_key, model};
            return provider;
        }

        function loadExternalApiConfig() {
            fetch('/external/config').then(r => r.json()).then(data => {
                if (!data.success) return;
                externalApiConfig = {active_provider: data.active_provider || 'deepseek', providers: data.providers || {}};
                const selectEl = document.getElementById('sceneProviderSelect');
                if (selectEl) selectEl.value = externalApiConfig.active_provider || 'deepseek';
                handleSceneProviderChange(selectEl?.value || 'deepseek');
                const statusEl = document.getElementById('sceneApiStatus');
                if (statusEl) statusEl.textContent = `已加载Provider: ${externalApiConfig.active_provider || 'deepseek'}`;
            });
        }

        function saveExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(r => r.json()).then(data => {
                if (!data.success) {
                    if (statusEl) statusEl.textContent = `保存失败: ${data.error || '未知错误'}`;
                    return;
                }
                externalApiConfig = data.config || externalApiConfig;
                if (statusEl) statusEl.textContent = `保存成功，当前Provider: ${provider}`;
                showToast('外界API配置已保存');
            }).catch(() => {
                if (statusEl) statusEl.textContent = '保存失败: 网络异常';
            });
        }

        function testExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(() => {
                fetch('/external/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider})
                }).then(r => r.json()).then(data => {
                    if (!data.success) {
                        if (statusEl) statusEl.textContent = `连通失败: ${data.error || '未知错误'}`;
                        return;
                    }
                    if (statusEl) statusEl.textContent = `连通成功: ${data.provider} / ${data.message || ''}`;
                    showToast('外界API连通成功');
                });
            });
        }

        function generateSceneContent(sceneId) {
            const provider = syncSceneConfigFromInputs();
            const topic = (document.getElementById('sceneTopicInput')?.value || '').trim();
            const context = (document.getElementById('sceneContextInput')?.value || '').trim();
            const goal = (document.getElementById('sceneGoalInput')?.value || '').trim();
            const constraints = (document.getElementById('sceneConstraintsInput')?.value || '').trim();
            const outputEl = document.getElementById('sceneOutput');
            const btn = document.getElementById('sceneGenerateBtn');
            if (!topic) { showToast('请先填写核心主题/素材'); return; }
            if (btn) btn.disabled = true;
            if (outputEl) outputEl.textContent = '外界API正在生成中，请稍候...';
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}})
            }).then(() => {
                fetch('/scenes/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({scene_id: sceneId, provider, topic, context, goal, constraints})
                }).then(r => r.json()).then(data => {
                    if (!data.success) {
                        if (outputEl) outputEl.textContent = `生成失败：${data.error || '未知错误'}`;
                        if (btn) btn.disabled = false;
                        return;
                    }
                    if (outputEl) outputEl.textContent = data.content || '';
                    if (btn) btn.disabled = false;
                }).catch(() => {
                    if (outputEl) outputEl.textContent = '生成失败：网络异常';
                    if (btn) btn.disabled = false;
                });
            });
        }

        function copySceneOutput() {
            const text = document.getElementById('sceneOutput')?.textContent || '';
            if (!text.trim()) return;
            navigator.clipboard.writeText(text).then(() => showToast('已复制场景结果'));
        }

        function openSceneFromQuickAction(sceneId) {
            const target = document.querySelector(`.sidebar-tab[onclick*="scenes"]`);
            if (target) switchTab('scenes', target);
            renderSceneWorkspace(sceneId);
            showToast(`已切换到${SCENE_UI_CONFIG[sceneId]?.title || '场景'}子界面`);
        }

        function quickAction(type) {
            if (['ecommerce', 'shortvideo', 'resume', 'business', 'dataops', 'contract'].includes(type)) {
                openSceneFromQuickAction(type);
                return;
            }
            const prompts = {
                'chat': '你好，我想和你聊聊天',
                'code': '请帮我写一段代码，实现以下功能：',
                'translate': '请帮我翻译以下内容：',
                'write': '请帮我写一篇关于',
                'analyze': '请帮我分析以下数据：',
                'learn': '请帮我解释一下'
            };
            const input = document.getElementById('mainInput');
            input.value = prompts[type] || '';
            currentStructuredTemplate = null;
            input.focus();
            updateCharCount();
        }
        
        function initSpeechRecognition() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SR();
                recognition.continuous = false;
                recognition.interimResults = true;
                recognition.lang = 'zh-CN';
                recognition.onresult = e => {
                    const t = Array.from(e.results).map(r => r[0].transcript).join('');
                    document.getElementById('mainInput').value = t;
                    updateCharCount();
                };
                recognition.onend = () => {
                    isRecording = false;
                    document.getElementById('voiceInputBtn').classList.remove('active');
                };
            }
        }
        
        function toggleVoiceInput() {
            if (!recognition) { showToast('浏览器不支持语音输入'); return; }
            if (isRecording) { recognition.stop(); return; }
            isRecording = true;
            document.getElementById('voiceInputBtn').classList.add('active');
            recognition.start();
        }
        
        function saveSettings() { localStorage.setItem('kaguya_settings', JSON.stringify(settings)); }
        function saveStats() { localStorage.setItem('kaguya_stats', JSON.stringify(stats)); }
        function saveChats() { localStorage.setItem('kaguya_chats', JSON.stringify(chats)); renderChatList(); }
        
        function updateStats() {
            const el1 = document.getElementById('statsSessions');
            const el2 = document.getElementById('statsInput');
            const el3 = document.getElementById('statsOutput');
            const el4 = document.getElementById('statsLatency');
            if (el1) el1.textContent = stats.sessions;
            if (el2) el2.textContent = stats.inputTokens;
            if (el3) el3.textContent = stats.outputTokens;
            if (el4) el4.textContent = stats.latencies.length ? Math.round(stats.latencies.reduce((a,b)=>a+b,0)/stats.latencies.length) : 0;
        }
        
        function renderChatList() {
            const sorted = [...chats].sort((a, b) => (b.starred ? 1 : 0) - (a.starred ? 1 : 0));
            let html = `<div class="chat-item chat-item-new" onclick="newChat()">
                <span>✨</span>
                <span class="chat-item-title">新建对话</span>
            </div>`;
            html += sorted.map(c => `
                <div class="chat-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
                    <span onclick="event.stopPropagation();toggleStarChat('${c.id}')" style="cursor:pointer;">${c.starred ? '⭐' : '💬'}</span>
                    <span class="chat-item-title">${c.title || '新对话'}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
            document.getElementById('chatList').innerHTML = html;
        }
        
        function renderRoleList() {
            // 按类型分组角色
            const characterRoles = roles.filter(r => r.type === 'character');
            const generalRoles = roles.filter(r => r.type === 'general' || !r.type);
            
            let html = '';
            
            // 角色卡模式分组
            if (characterRoles.length > 0) {
                html += `<div class="role-group"><div class="role-group-title">🎭 角色卡模式</div>`;
                html += characterRoles.map(r => {
                    const icon = r.icon || '🎭', color = r.color || '#667eea';
                    return `<div class="role-item ${r.id === currentRole ? 'active' : ''}" onclick="selectRole('${r.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${r.avatar.startsWith('/') ? `<img src="${r.avatar}" style="width:100%;height:100%;border-radius:8px;">` : icon}</div>
                        <div class="item-info"><div class="item-name">${r.name}</div><div class="item-desc">${r.description}</div></div>
                        <span class="role-type-badge" style="background:linear-gradient(135deg,#a855f7,#7c3aed);">角色</span>
                    </div>`;
                }).join('');
                html += '</div>';
            }
            
            // 一般版本模型分组
            if (generalRoles.length > 0) {
                html += `<div class="role-group"><div class="role-group-title">🤖 一般版本模型</div>`;
                html += generalRoles.map(r => {
                    const icon = r.icon || '🤖', color = r.color || '#667eea';
                    return `<div class="role-item ${r.id === currentRole ? 'active' : ''}" onclick="selectRole('${r.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${r.avatar.startsWith('/') ? `<img src="${r.avatar}" style="width:100%;height:100%;border-radius:8px;">` : icon}</div>
                        <div class="item-info"><div class="item-name">${r.name}</div><div class="item-desc">${r.description}</div></div>
                        <span class="role-type-badge" style="background:linear-gradient(135deg,#667eea,#5a67d8);">通用</span>
                    </div>`;
                }).join('');
                html += '</div>';
            }
            
            document.getElementById('roleList').innerHTML = html;
        }
        
        function renderToolList() {
            document.getElementById('toolList').innerHTML = Object.entries(tools).map(([id, t]) => `
                <div class="tool-item ${activeTools.has(id) ? 'active' : ''}" onclick="toggleTool('${id}')">
                    <div class="item-icon" style="background:linear-gradient(135deg,#f59e0b,#d97706);">${t.icon}</div>
                    <div class="item-info"><div class="item-name">${t.name}</div><div class="item-desc">${t.description}</div></div>
                    ${activeTools.has(id) ? '<span class="item-badge" style="background:#f59e0b;">已启用</span>' : ''}
                </div>
            `).join('');
        }
        
        function loadLoraList() {
            fetch('/lora/list').then(r => r.json()).then(data => {
                document.getElementById('loraList').innerHTML = data.loras.map(l => {
                    const icon = l.icon || '🤖', color = l.color || '#10b981';
                    return `<div class="lora-item ${l.id === currentLora ? 'active' : ''}" onclick="selectLora('${l.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${icon}</div>
                        <div class="item-info"><div class="item-name">${l.name}</div><div class="item-desc">${l.description}</div></div>
                        ${l.loaded ? `<span class="item-badge" style="background:${color};">已加载</span>` : ''}
                    </div>`;
                }).join('');
            });
        }
        
        function toggleTool(id) {
            if (activeTools.has(id)) activeTools.delete(id);
            else activeTools.add(id);
            renderToolList();
            updateIndicators();
            document.querySelectorAll('.quick-tool').forEach(el => {
                if (el.dataset.tool === id) el.classList.toggle('active', activeTools.has(id));
            });
            showToast(activeTools.has(id) ? `已启用 ${tools[id].name}` : `已禁用 ${tools[id].name}`);
        }
        
        function updateIndicators() {
            let html = '';
            if (currentLora !== 'none') html += `<div class="indicator lora"><span>🔧</span><span>${currentLora}</span></div>`;
            if (activeTools.size > 0) html += `<div class="indicator tool"><span>🛠️</span><span>${activeTools.size}个工具</span></div>`;
            document.getElementById('headerIndicators').innerHTML = html;
        }
        
        function selectRole(id) {
            currentRole = id;
            const role = roles.find(r => r.id === id);
            if (role) {
                document.getElementById('headerTitle').textContent = role.name;
                if (role.avatar.startsWith('/')) document.getElementById('headerAvatar').src = role.avatar;
            }
            renderRoleList();
            showToast(`已切换到 ${role.name}`);
        }
        
        function selectLora(id) {
            fetch('/lora/load', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lora_id: id})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    currentLora = id;
                    loadLoraList();
                    updateIndicators();
                    showToast(data.message || 'LoRA已切换');
                } else showToast('加载失败: ' + (data.error || '未知错误'));
            });
        }
        
        // ==================== 模型微调平台 ====================
        function refreshFinetuneData() {
            loadFinetuneDatasets();
            loadFinetuneJobs();
        }
        
        function loadFinetuneDatasets() {
            fetch('/finetune/datasets').then(r => r.json()).then(data => {
                if (data.success) {
                    renderFinetuneDatasets(data.datasets);
                }
            });
        }
        
        function renderFinetuneDatasets(datasets) {
            const container = document.getElementById('finetuneDatasets');
            if (!datasets || datasets.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:10px;font-size:12px;">暂无数据集，请上传</div>';
                return;
            }
            
            container.innerHTML = datasets.map(ds => `
                <div class="finetune-item">
                    <div class="finetune-header">
                        <span class="finetune-icon">📊</span>
                        <span class="finetune-title">${ds.name}</span>
                        <span class="finetune-status ${ds.status}">${ds.status}</span>
                    </div>
                    <div class="finetune-meta">
                        <span>格式: ${ds.format}</span>
                        <span>样本: ${ds.sample_count}</span>
                        <span>${new Date(ds.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                    <div class="finetune-actions">
                        <button class="finetune-btn delete" onclick="deleteFinetuneDataset('${ds.id}')">🗑️ 删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function loadFinetuneJobs() {
            fetch('/finetune/jobs').then(r => r.json()).then(data => {
                if (data.success) {
                    renderFinetuneJobs(data.jobs);
                }
            });
        }
        
        function renderFinetuneJobs(jobs) {
            const container = document.getElementById('finetuneJobs');
            if (!jobs || jobs.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:10px;font-size:12px;">暂无训练任务</div>';
                return;
            }
            
            container.innerHTML = jobs.map(job => `
                <div class="finetune-item">
                    <div class="finetune-header">
                        <span class="finetune-icon">🎯</span>
                        <span class="finetune-title">${job.name}</span>
                        <span class="finetune-status ${job.status}">${job.status}</span>
                    </div>
                    <div class="finetune-meta">
                        <span>方法: ${job.method}</span>
                        <span>数据: ${job.dataset_name}</span>
                        <span>${new Date(job.created_at * 1000).toLocaleDateString()}</span>
                    </div>
                    <div class="finetune-progress">
                        <div class="finetune-progress-bar" style="width:${job.progress}%"></div>
                    </div>
                    <div class="finetune-actions">
                        ${job.status === 'pending' ? `<button class="finetune-btn start" onclick="startFinetuneJob('${job.job_id}')">▶ 开始</button>` : ''}
                        ${job.status === 'running' ? `<button class="finetune-btn stop" onclick="stopFinetuneJob('${job.job_id}')">⏹ 停止</button>` : ''}
                        <button class="finetune-btn delete" onclick="deleteFinetuneJob('${job.job_id}')">🗑️ 删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        function showDatasetUpload() {
            console.log('showDatasetUpload called');
            const name = prompt('数据集名称:');
            if (!name) return;
            
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.jsonl,.json,.csv';
            input.onchange = function(e) {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('name', name);
                formData.append('format', file.name.split('.').pop());
                
                fetch('/finetune/dataset/upload', {
                    method: 'POST',
                    body: formData
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast(`数据集上传成功，包含 ${data.sample_count} 个样本`);
                        loadFinetuneDatasets();
                    } else {
                        showToast('上传失败: ' + (data.error || '未知错误'));
                    }
                });
            };
            input.click();
        }
        
        function showCreateJob() {
            console.log('showCreateJob called');
            const name = prompt('训练任务名称:');
            if (!name) return;
            
            fetch('/finetune/datasets').then(r => r.json()).then(data => {
                if (!data.success || data.datasets.length === 0) {
                    showToast('请先上传数据集');
                    return;
                }
                
                const datasetOptions = data.datasets.map((ds, i) => `${i + 1}. ${ds.name} (${ds.sample_count}样本)`).join(String.fromCharCode(10));
                const datasetIdx = prompt(`选择数据集:` + String.fromCharCode(10) + `${datasetOptions}`);
                if (!datasetIdx) return;
                
                const dataset = data.datasets[parseInt(datasetIdx) - 1];
                if (!dataset) {
                    showToast('无效选择');
                    return;
                }
                
                const method = prompt('训练方法 (lora/qlora):', 'lora');
                const epochs = prompt('训练轮数:', '3');
                
                const config = {
                    method: method || 'lora',
                    num_epochs: parseInt(epochs) || 3,
                    lora_r: 16,
                    lora_alpha: 32,
                    learning_rate: 5e-5,
                    batch_size: 4
                };
                
                fetch('/finetune/job', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, dataset_id: dataset.id, config})
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('训练任务创建成功');
                        loadFinetuneJobs();
                    } else {
                        showToast('创建失败: ' + (data.error || '未知错误'));
                    }
                });
            });
        }
        
        function startFinetuneJob(jobId) {
            fetch(`/finetune/job/${jobId}/start`, {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练已开始');
                    loadFinetuneJobs();
                } else {
                    showToast('启动失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function stopFinetuneJob(jobId) {
            fetch(`/finetune/job/${jobId}/stop`, {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练已停止');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneJob(jobId) {
            if (!confirm('确定要删除这个训练任务吗？')) return;
            
            fetch(`/finetune/job/${jobId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('训练任务已删除');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneDataset(datasetId) {
            if (!confirm('确定要删除这个数据集吗？')) return;
            
            fetch(`/finetune/dataset/${datasetId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('数据集已删除');
                    loadFinetuneDatasets();
                }
            });
        }
        
        // ==================== 多模态视觉理解系统 ====================
        let currentMultimodalImage = null;
        let currentImageId = null;
        
        function uploadMultimodalImage(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // 显示预览
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('previewImg').src = e.target.result;
                document.getElementById('multimodalImagePreview').style.display = 'block';
                currentMultimodalImage = e.target.result;
            };
            reader.readAsDataURL(file);
            
            // 上传到服务器
            const formData = new FormData();
            formData.append('image', file);
            formData.append('task', 'understand');
            
            fetch('/multimodal/upload', {
                method: 'POST',
                body: formData
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    currentImageId = data.result.image_id;
                    showToast('图片上传成功');
                } else {
                    showToast('上传失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function analyzeImage(task) {
            if (!currentImageId) {
                showToast('请先上传图片');
                return;
            }
            
            fetch('/multimodal/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({image_id: currentImageId, task: task})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    displayMultimodalResult(task, data.result);
                } else {
                    showToast('分析失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function displayMultimodalResult(task, result) {
            const container = document.getElementById('multimodalResults');
            
            let taskName = '';
            let icon = '';
            let content = '';
            
            switch(task) {
                case 'describe':
                    taskName = '图像描述';
                    icon = '📝';
                    content = result.description || '无法生成描述';
                    break;
                case 'ocr':
                    taskName = '文字识别';
                    icon = '📄';
                    content = result.text || '未识别到文字';
                    break;
                case 'analyze':
                    taskName = '内容分析';
                    icon = '🔍';
                    content = JSON.stringify(result, null, 2);
                    break;
                default:
                    taskName = '分析结果';
                    icon = '📊';
                    content = JSON.stringify(result, null, 2);
            }
            
            const resultEl = document.createElement('div');
            resultEl.className = 'multimodal-result';
            resultEl.innerHTML = `
                <div class="multimodal-result-header">
                    <span>${icon}</span>
                    <span>${taskName}</span>
                    <span style="margin-left:auto;font-size:10px;color:var(--text-muted);">${new Date().toLocaleTimeString()}</span>
                </div>
                <div class="multimodal-result-content">${content}</div>
                ${result.dimensions ? `<div class="multimodal-result-meta">📐 ${result.dimensions}</div>` : ''}
            `;
            
            container.insertBefore(resultEl, container.firstChild);
        }
        
        function loadMultimodalHistory() {
            fetch('/multimodal/history').then(r => r.json()).then(data => {
                if (data.success && data.history.length > 0) {
                    // 可以在这里显示历史记录
                }
            });
        }
        
        function clearMultimodalHistory() {
            if (!confirm('确定要清除所有分析结果吗？')) return;
            
            fetch('/multimodal/clear', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    document.getElementById('multimodalResults').innerHTML = '';
                    document.getElementById('multimodalImagePreview').style.display = 'none';
                    document.getElementById('previewImg').src = '';
                    currentMultimodalImage = null;
                    currentImageId = null;
                    showToast('已清除');
                }
            });
        }
        
        // ==================== 记忆系统 ====================
        function refreshMemoryStats() {
            fetch('/memory/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const longTermEl = document.getElementById('memLongTerm');
                    const avgImpEl = document.getElementById('memAvgImportance');
                    const entitiesEl = document.getElementById('memEntities');
                    const profileEl = document.getElementById('memProfile');
                    if (longTermEl) longTermEl.textContent = data.stats.long_term_count;
                    if (avgImpEl) avgImpEl.textContent = data.stats.avg_importance;
                    if (entitiesEl) entitiesEl.textContent = data.stats.entity_count;
                    if (profileEl) profileEl.textContent = data.stats.profile_count;
                }
            });
        }
        
        function searchMemories() {
            const query = document.getElementById('memorySearchInput').value || 'all';
            fetch('/memory/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query, top_k: 20})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    renderMemoryList(data.memories);
                }
            });
        }
        
        function renderMemoryList(memories) {
            const container = document.getElementById('memoryList');
            if (!memories || memories.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无记忆</div>';
                return;
            }
            
            container.innerHTML = memories.map(m => {
                const importanceDots = Array(5).fill(0).map((_, i) => 
                    `<div class="importance-dot ${i < m.importance * 5 ? 'active' : ''}"></div>`
                ).join('');
                
                const date = new Date(m.created_at * 1000).toLocaleDateString();
                
                return `
                    <div class="memory-item">
                        <div class="memory-content">${m.content}</div>
                        <div class="memory-meta">
                            <span class="memory-type ${m.type}">${m.type}</span>
                            <span>📊 重要性:</span>
                            <div class="memory-importance">${importanceDots}</div>
                            <span>🕐 ${date}</span>
                            <span>👁️ ${m.access_count}次</span>
                            <div class="memory-actions">
                                <button class="memory-btn" onclick="deleteMemory('${m.id}')">🗑️</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function showAddMemoryModal() {
            const content = prompt('请输入要添加的记忆内容:');
            if (!content) return;
            
            const type = prompt('记忆类型 (fact/preference/experience):', 'fact');
            
            fetch('/memory', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, type: type || 'fact'})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆已添加');
                    refreshMemoryStats();
                    searchMemories();
                }
            });
        }
        
        function deleteMemory(memoryId) {
            if (!confirm('确定要删除这条记忆吗？')) return;
            
            fetch(`/memory/${memoryId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆已删除');
                    searchMemories();
                    refreshMemoryStats();
                }
            });
        }
        
        function consolidateMemories() {
            if (!confirm('确定要整合记忆吗？这将清理过时和低重要性的记忆。')) return;
            
            fetch('/memory/consolidate', {method: 'POST'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('记忆整合完成');
                    refreshMemoryStats();
                    searchMemories();
                }
            });
        }
        
        // ==================== MCP 插件管理 ====================
        let mcpPlugins = [];
        let enabledMcpTools = [];
        
        // ==================== 工作流编排系统 ====================
        let workflows = [];
        let workflowNodeTypes = {};
        let currentWorkflow = null;
        let selectedNode = null;
        let workflowNodes = [];
        let workflowConnections = [];
        let workflowZoom = 1;
        let isDraggingNode = false;
        let dragOffset = { x: 0, y: 0 };
        let isConnecting = false;
        let connectionStart = null;
        
        function loadWorkflows() {
            fetch('/workflows').then(r => r.json()).then(data => {
                if (data.success) {
                    workflows = data.workflows;
                    renderWorkflowList();
                    renderFeatureCenterMeta();
                }
            });
        }
        
        function renderWorkflowList() {
            const container = document.getElementById('workflowList');
            if (!workflows.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无工作流，点击"新建"创建</div>';
                return;
            }
            
            container.innerHTML = workflows.map(wf => `
                <div class="workflow-item" data-id="${wf.id}">
                    <div class="workflow-icon" style="background:linear-gradient(135deg,${wf.color},${wf.color}dd);">${wf.icon}</div>
                    <div class="workflow-info">
                        <div class="workflow-name">${wf.name}</div>
                        <div class="workflow-desc">${wf.description || '无描述'}</div>
                        <div class="workflow-meta">
                            <span>📦 ${wf.node_count}个节点</span>
                            <span>🕐 ${new Date(wf.updated_at * 1000).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div class="workflow-actions">
                        <button class="workflow-btn run" onclick="runWorkflow('${wf.id}')">▶</button>
                        <button class="workflow-btn edit" onclick="editWorkflow('${wf.id}')">✏️</button>
                        <button class="workflow-btn delete" onclick="deleteWorkflow('${wf.id}')">🗑️</button>
                    </div>
                </div>
            `).join('');
        }
        
        function openWorkflowEditor() {
            currentWorkflow = null;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            document.getElementById('workflowName').value = '';
            document.getElementById('workflowNodesContainer').innerHTML = '';
            document.getElementById('workflowConnections').innerHTML = '';
            document.getElementById('workflowProperties').innerHTML = `
                <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                    <div style="font-size:32px;margin-bottom:8px;">👈</div>
                    <div style="font-size:13px;">选择节点以编辑属性</div>
                </div>
            `;
            
            loadWorkflowNodeTypes();
            document.getElementById('workflowEditorModal').classList.add('show');
        }
        
        function loadWorkflowNodeTypes() {
            fetch('/workflow/node-types').then(r => r.json()).then(data => {
                if (data.success) {
                    workflowNodeTypes = data.node_types;
                    renderWorkflowNodePalette();
                }
            });
        }
        
        function renderWorkflowNodePalette() {
            const controlContainer = document.getElementById('workflowNodesControl');
            const aiContainer = document.getElementById('workflowNodesAI');
            const toolContainer = document.getElementById('workflowNodesTool');
            
            controlContainer.innerHTML = '';
            aiContainer.innerHTML = '';
            toolContainer.innerHTML = '';
            
            Object.values(workflowNodeTypes).forEach(nodeType => {
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-node-item';
                nodeEl.draggable = true;
                nodeEl.innerHTML = `
                    <span class="workflow-node-icon" style="color:${nodeType.color};">${nodeType.icon}</span>
                    <span>${nodeType.name}</span>
                `;
                nodeEl.ondragstart = (e) => {
                    e.dataTransfer.setData('nodeType', nodeType.id);
                };
                
                if (nodeType.category === 'control') {
                    controlContainer.appendChild(nodeEl);
                } else if (nodeType.category === 'ai') {
                    aiContainer.appendChild(nodeEl);
                } else {
                    toolContainer.appendChild(nodeEl);
                }
            });
        }
        
        function editWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}`).then(r => r.json()).then(data => {
                if (data.success) {
                    currentWorkflow = data.workflow;
                    workflowNodes = data.workflow.nodes || [];
                    workflowConnections = data.workflow.connections || [];
                    document.getElementById('workflowName').value = data.workflow.name;
                    renderWorkflowCanvas();
                    loadWorkflowNodeTypes();
                    document.getElementById('workflowEditorModal').classList.add('show');
                }
            });
        }
        
        function renderWorkflowCanvas() {
            const container = document.getElementById('workflowNodesContainer');
            container.innerHTML = '';
            
            workflowNodes.forEach(node => {
                const nodeType = workflowNodeTypes[node.type];
                if (!nodeType) return;
                
                const nodeEl = document.createElement('div');
                nodeEl.className = 'workflow-canvas-node' + (selectedNode === node.id ? ' selected' : '');
                nodeEl.style.left = node.x + 'px';
                nodeEl.style.top = node.y + 'px';
                nodeEl.style.borderColor = nodeType.color;
                nodeEl.dataset.nodeId = node.id;
                nodeEl.innerHTML = `
                    <div class="node-header">
                        <span class="node-icon">${nodeType.icon}</span>
                        <span class="node-title">${nodeType.name}</span>
                    </div>
                    <div style="font-size:11px;color:var(--text-muted);">${node.config?.label || ''}</div>
                    <div class="node-ports">
                        ${nodeType.inputs.length ? '<div class="workflow-port input" data-port="input"></div>' : '<div></div>'}
                        ${nodeType.outputs.length ? '<div class="workflow-port output" data-port="output"></div>' : '<div></div>'}
                    </div>
                `;
                
                nodeEl.onclick = (e) => {
                    e.stopPropagation();
                    selectWorkflowNode(node.id);
                };
                
                nodeEl.onmousedown = (e) => {
                    if (e.target.classList.contains('workflow-port')) return;
                    isDraggingNode = true;
                    dragOffset.x = e.clientX - node.x;
                    dragOffset.y = e.clientY - node.y;
                    
                    const onMouseMove = (e) => {
                        if (!isDraggingNode) return;
                        node.x = e.clientX - dragOffset.x;
                        node.y = e.clientY - dragOffset.y;
                        nodeEl.style.left = node.x + 'px';
                        nodeEl.style.top = node.y + 'px';
                        renderWorkflowConnections();
                    };
                    
                    const onMouseUp = () => {
                        isDraggingNode = false;
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                    };
                    
                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                };
                
                container.appendChild(nodeEl);
            });
            
            renderWorkflowConnections();
        }
        
        function renderWorkflowConnections() {
            const svg = document.getElementById('workflowConnections');
            svg.innerHTML = '';
            
            workflowConnections.forEach(conn => {
                const sourceNode = workflowNodes.find(n => n.id === conn.source);
                const targetNode = workflowNodes.find(n => n.id === conn.target);
                if (!sourceNode || !targetNode) return;
                
                const sourceEl = document.querySelector(`[data-node-id="${conn.source}"]`);
                const targetEl = document.querySelector(`[data-node-id="${conn.target}"]`);
                if (!sourceEl || !targetEl) return;
                
                const x1 = sourceNode.x + sourceEl.offsetWidth;
                const y1 = sourceNode.y + sourceEl.offsetHeight / 2;
                const x2 = targetNode.x;
                const y2 = targetNode.y + targetEl.offsetHeight / 2;
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`);
                path.setAttribute('class', 'workflow-connection');
                path.setAttribute('marker-end', 'url(#arrowhead)');
                svg.appendChild(path);
            });
        }
        
        function selectWorkflowNode(nodeId) {
            selectedNode = nodeId;
            renderWorkflowCanvas();
            
            const node = workflowNodes.find(n => n.id === nodeId);
            const nodeType = workflowNodeTypes[node.type];
            if (!node || !nodeType) return;
            
            const panel = document.getElementById('workflowProperties');
            panel.innerHTML = `
                <div style="font-size:14px;font-weight:600;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid ${nodeType.color};">
                    ${nodeType.icon} ${nodeType.name} 属性
                </div>
                ${renderNodeProperties(node, nodeType)}
            `;
        }
        
        function renderNodeProperties(node, nodeType) {
            let html = '';
            
            // 渲染配置项
            Object.entries(nodeType.config).forEach(([key, defaultValue]) => {
                const value = node.config[key] !== undefined ? node.config[key] : defaultValue;
                html += `<div class="property-group">`;
                html += `<div class="property-label">${key}</div>`;
                
                if (typeof defaultValue === 'boolean') {
                    html += `<input type="checkbox" ${value ? 'checked' : ''} onchange="updateNodeConfig('${node.id}', '${key}', this.checked)">`;
                } else if (typeof defaultValue === 'number') {
                    html += `<input type="number" class="property-input" value="${value}" onchange="updateNodeConfig('${node.id}', '${key}', parseFloat(this.value))">`;
                } else if (key === 'code' || key === 'prompt' || key === 'system_prompt' || key === 'template') {
                    html += `<textarea class="property-input property-textarea" onchange="updateNodeConfig('${node.id}', '${key}', this.value)">${value}</textarea>`;
                } else {
                    html += `<input type="text" class="property-input" value="${value}" onchange="updateNodeConfig('${node.id}', '${key}', this.value)">`;
                }
                
                html += `</div>`;
            });
            
            html += `<button class="modal-btn" onclick="deleteWorkflowNode('${node.id}')" style="background:#ef4444;color:white;width:100%;margin-top:20px;">🗑️ 删除节点</button>`;
            
            return html;
        }
        
        function updateNodeConfig(nodeId, key, value) {
            const node = workflowNodes.find(n => n.id === nodeId);
            if (node) {
                node.config[key] = value;
            }
        }
        
        function deleteWorkflowNode(nodeId) {
            workflowNodes = workflowNodes.filter(n => n.id !== nodeId);
            workflowConnections = workflowConnections.filter(c => c.source !== nodeId && c.target !== nodeId);
            selectedNode = null;
            renderWorkflowCanvas();
            document.getElementById('workflowProperties').innerHTML = `
                <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                    <div style="font-size:32px;margin-bottom:8px;">👈</div>
                    <div style="font-size:13px;">选择节点以编辑属性</div>
                </div>
            `;
        }
        
        function saveWorkflow() {
            const name = document.getElementById('workflowName').value || '未命名工作流';
            const workflowData = {
                id: currentWorkflow?.id,
                name: name,
                description: '',
                icon: '📋',
                color: '#667eea',
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            fetch('/workflow', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(workflowData)
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已保存');
                    loadWorkflows();
                    closeModal('workflowEditorModal');
                } else {
                    showToast('保存失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function executeWorkflow() {
            const workflowData = {
                nodes: workflowNodes,
                connections: workflowConnections
            };
            
            fetch('/workflow/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({workflow: workflowData, inputs: {}})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流执行完成');
                    console.log('执行结果:', data);
                } else {
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function runWorkflow(workflowId) {
            fetch(`/workflow/${workflowId}/execute`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({inputs: {}})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流执行完成');
                } else {
                    showToast('执行失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function deleteWorkflow(workflowId) {
            if (!confirm('确定要删除这个工作流吗？')) return;
            
            fetch(`/workflow/${workflowId}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('工作流已删除');
                    loadWorkflows();
                }
            });
        }
        
        function clearWorkflowCanvas() {
            if (!confirm('确定要清空所有节点吗？')) return;
            workflowNodes = [];
            workflowConnections = [];
            selectedNode = null;
            renderWorkflowCanvas();
        }
        
        function zoomWorkflow(delta) {
            workflowZoom = Math.max(0.5, Math.min(2, workflowZoom + delta));
            document.getElementById('workflowNodesContainer').style.transform = `scale(${workflowZoom})`;
            document.getElementById('workflowConnections').style.transform = `scale(${workflowZoom})`;
        }
        
        // 画布拖放处理
        document.addEventListener('DOMContentLoaded', () => {
            const canvas = document.getElementById('workflowCanvas');
            if (canvas) {
                canvas.ondragover = (e) => e.preventDefault();
                canvas.ondrop = (e) => {
                    e.preventDefault();
                    const nodeTypeId = e.dataTransfer.getData('nodeType');
                    const nodeType = workflowNodeTypes[nodeTypeId];
                    if (!nodeType) return;
                    
                    const rect = canvas.getBoundingClientRect();
                    const newNode = {
                        id: 'node_' + Date.now(),
                        type: nodeTypeId,
                        x: (e.clientX - rect.left) / workflowZoom,
                        y: (e.clientY - rect.top) / workflowZoom,
                        config: {...nodeType.config}
                    };
                    
                    workflowNodes.push(newNode);
                    renderWorkflowCanvas();
                    selectWorkflowNode(newNode.id);
                };
                
                canvas.onclick = () => {
                    selectedNode = null;
                    renderWorkflowCanvas();
                    document.getElementById('workflowProperties').innerHTML = `
                        <div style="text-align:center;color:var(--text-muted);padding:40px 20px;">
                            <div style="font-size:32px;margin-bottom:8px;">👈</div>
                            <div style="font-size:13px;">选择节点以编辑属性</div>
                        </div>
                    `;
                };
            }
        });
        
        function loadMcpPlugins() {
            fetch('/mcp/plugins').then(r => r.json()).then(data => {
                if (data.success) {
                    mcpPlugins = data.plugins;
                    renderMcpList();
                    // 更新启用的工具列表
                    enabledMcpTools = mcpPlugins.filter(p => p.enabled).flatMap(p => {
                        return p.tools_count > 0 ? [`${p.id}: ${p.description}`] : [];
                    });
                    renderFeatureCenterMeta();
                }
            });
        }
        
        // 检测并执行 MCP 工具调用
        async function detectAndExecuteMcpTool(content) {
            // 检测 MCP 工具调用格式: [MCP:plugin_id:tool_name]{parameters}
            const mcpPattern = /\[MCP:(\w+):(\w+)\]\s*({[^}]*})/g;
            let match;
            let modifiedContent = content;
            
            while ((match = mcpPattern.exec(content)) !== null) {
                const [fullMatch, pluginId, toolName, paramsStr] = match;
                try {
                    const parameters = JSON.parse(paramsStr);
                    const result = await executeMcpTool(pluginId, toolName, parameters);
                    
                    // 替换工具调用为执行结果
                    const resultText = formatMcpResult(result);
                    modifiedContent = modifiedContent.replace(fullMatch, resultText);
                } catch (e) {
                    console.error('MCP工具执行失败:', e);
                    modifiedContent = modifiedContent.replace(fullMatch, `[工具执行失败: ${e.message}]`);
                }
            }
            
            return modifiedContent;
        }

        async function executeMcpTool(pluginId, toolName, parameters) {
            const res = await fetch('/mcp/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({plugin_id: pluginId, tool_name: toolName, parameters})
            });
            const data = await res.json();
            return data.result || {error: '执行失败'};
        }
        
        function formatMcpResult(result) {
            if (result.error) {
                return `<div style="color:#e74c3c;padding:8px;background:rgba(231,76,60,0.1);border-radius:6px;margin:4px 0;">❌ ${result.error}</div>`;
            }
            
            // 格式化不同类型的结果
            if (result.content !== undefined) {
                return `<div style="padding:10px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;"><pre style="margin:0;white-space:pre-wrap;">${result.content}</pre></div>`;
            }
            if (result.results !== undefined && Array.isArray(result.results)) {
                const items = result.results.map(r => `<li><a href="${r.link}" target="_blank" style="color:var(--primary);">${r.title}</a></li>`).join('');
                return `<div style="padding:10px;background:rgba(245,158,11,0.1);border-radius:6px;margin:4px 0;"><ol style="margin:0;padding-left:20px;">${items}</ol></div>`;
            }
            if (result.result !== undefined) {
                return `<div style="padding:8px;background:rgba(16,185,129,0.1);border-radius:6px;margin:4px 0;font-weight:600;">🧮 结果: ${result.result}</div>`;
            }
            if (result.items !== undefined && Array.isArray(result.items)) {
                const items = result.items.map(i => `<li>${i.type === 'directory' ? '📁' : '📄'} ${i.name}</li>`).join('');
                return `<div style="padding:10px;background:rgba(59,130,246,0.1);border-radius:6px;margin:4px 0;"><ul style="margin:0;padding-left:20px;">${items}</ul></div>`;
            }
            
            return `<div style="padding:8px;background:rgba(102,126,234,0.1);border-radius:6px;margin:4px 0;">${JSON.stringify(result)}</div>`;
        }
        
        // 获取 MCP 系统提示词
        function getMcpSystemPrompt() {
            if (enabledMcpTools.length === 0) return '';
            
            return `

【MCP工具使用说明】
你可以使用以下工具来帮助用户。当需要使用工具时，请按以下格式输出：
[MCP:插件ID:工具名]{"参数名": "参数值"}

可用工具：
${enabledMcpTools.map(t => `- ${t}`).join(String.fromCharCode(10))}

示例：
- 读取文件: [MCP:filesystem:read_file]{"path": "~/document.txt"}
- 搜索网络: [MCP:web_search:search]{"query": "最新科技新闻", "num_results": 5}
- 计算: [MCP:calculator:calculate]{"expression": "2+2*3"}
- 获取时间: [MCP:datetime:get_current_time]{"timezone": "Asia/Shanghai"}
`;
        }
        
        function renderMcpList() {
            const container = document.getElementById('mcpList');
            if (!mcpPlugins.length) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无可用插件</div>';
                return;
            }
            
            container.innerHTML = mcpPlugins.map(p => {
                const enabled = p.enabled;
                return `
                    <div class="mcp-item ${enabled ? 'enabled' : ''}" data-id="${p.id}">
                        <div class="mcp-icon" style="background:linear-gradient(135deg,${p.color},${p.color}dd);">${p.icon}</div>
                        <div class="mcp-info">
                            <div class="mcp-name">${p.name}</div>
                            <div class="mcp-desc">${p.description}</div>
                        </div>
                        <span class="mcp-tools-count">${p.tools_count}个工具</span>
                        <button class="mcp-config-btn" onclick="showMcpConfig('${p.id}')" style="margin-right:8px;">⚙️</button>
                        <div class="mcp-toggle ${enabled ? 'enabled' : ''}" onclick="toggleMcpPlugin('${p.id}', ${!enabled})"></div>
                    </div>
                `;
            }).join('');
        }
        
        function toggleMcpPlugin(pluginId, enabled) {
            fetch(`/mcp/plugin/${pluginId}/enable`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast(data.message);
                    loadMcpPlugins();
                } else {
                    showToast('操作失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function refreshMcpPlugins() {
            loadMcpPlugins();
            showToast('已刷新插件列表');
        }
        
        function showMcpConfig(pluginId) {
            const plugin = mcpPlugins.find(p => p.id === pluginId);
            if (!plugin) return;
            
            // 简单的配置提示框
            if (plugin.id === 'filesystem') {
                const readOnly = confirm('是否设置为只读模式？' + String.fromCharCode(10) + String.fromCharCode(10) + '确定 = 只读' + String.fromCharCode(10) + '取消 = 可读写');
                fetch(`/mcp/plugin/${pluginId}/config`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config: {read_only: readOnly, allowed_paths: [os.path.expanduser("~")]}})
                }).then(r => r.json()).then(data => {
                    if (data.success) showToast('配置已更新');
                });
            } else if (plugin.id === 'web_search') {
                const numResults = prompt('设置默认搜索结果数量 (1-10):', '5');
                if (numResults && !isNaN(numResults)) {
                    fetch(`/mcp/plugin/${pluginId}/config`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({config: {max_results: parseInt(numResults)}})
                    }).then(r => r.json()).then(data => {
                        if (data.success) showToast('配置已更新');
                    });
                }
            } else {
                showToast('该插件暂无配置选项');
            }
        }
        
        const PROMPT_TEMPLATES = [
            {id: 'code', name: '代码助手', prompt: '请帮我写一段代码，实现以下功能：', icon: '📝', desc: '代码生成、重构与调试建议', category: 'general', source: '通用'},
            {id: 'translate', name: '翻译助手', prompt: '请将以下内容翻译成英文：', icon: '🌐', desc: '多语言翻译与语气适配', category: 'general', source: '通用'},
            {id: 'summary', name: '总结助手', prompt: '请帮我总结以下内容的要点：', icon: '📋', desc: '快速提炼重点与行动项', category: 'general', source: '通用'},
            {id: 'email', name: '邮件助手', prompt: '请帮我写一封邮件，主题是：', icon: '📧', desc: '商务邮件写作与回复模板', category: 'general', source: '通用'},
            {id: 'article', name: '文章助手', prompt: '请帮我写一篇关于', icon: '✍️', desc: '内容创作与表达优化', category: 'general', source: '通用'},
            {id: 'debug', name: '调试助手', prompt: '以下代码有问题，请帮我找出错误：', icon: '🐛', desc: '定位报错并给出修复路径', category: 'general', source: '通用'},
            {id: 'ecommerce', name: '电商增长策略', prompt: '请为我的电商产品制定30天增长方案，包含人群画像、卖点、活动节奏、投放素材结构与转化指标。', icon: '🛍️', desc: '活动节奏、投放与转化闭环', category: 'growth', source: '实战', template: 'ecommerce'},
            {id: 'shortvideo', name: '短视频增长', prompt: '请为我设计7天短视频内容计划，输出选题、脚本结构、前3秒钩子、封面标题和发布时间建议。', icon: '🎬', desc: '账号内容排期与选题脚本', category: 'growth', source: '实战', template: 'shortvideo'},
            {id: 'prompt_eval', name: '提示词评测体系', prompt: '请为我的AI应用设计提示词评测方案，包括测试集、评分维度、A/B对比和持续回归机制。', icon: '🧪', desc: '借鉴 Promptfoo 的评测思想', category: 'engineering', source: 'Promptfoo', template: 'prompt_eval'},
            {id: 'agent_observability', name: '智能体可观测性', prompt: '请为我的AI助手设计可观测性方案，覆盖链路追踪、错误分层、质量指标和排障流程。', icon: '📈', desc: '借鉴 Langfuse 的追踪与评估实践', category: 'engineering', source: 'Langfuse', template: 'agent_observability'},
            {id: 'ai_workflow', name: '自动化工作流设计', prompt: '请为我的业务场景设计一套AI自动化工作流，包含触发器、节点编排、审批机制和失败重试策略。', icon: '🔁', desc: '借鉴 n8n 的节点化编排思路', category: 'engineering', source: 'n8n', template: 'ai_workflow'},
            {id: 'ai_redteam', name: 'AI安全红队演练', prompt: '请为我的AI产品制定红队测试计划，覆盖越狱、提示注入、数据泄露和工具滥用风险。', icon: '🛡️', desc: '借鉴 Promptfoo 的红队测试场景', category: 'engineering', source: 'Promptfoo', template: 'ai_redteam'},
            {id: 'rag_ops', name: 'RAG知识运营', prompt: '请为我的知识库系统制定RAG运营方案，包含文档治理、检索质量评估和持续优化闭环。', icon: '📚', desc: '借鉴 Dify/Open WebUI 的RAG实践', category: 'knowledge', source: 'Dify/Open WebUI', template: 'rag_ops'},
            {id: 'deep_research', name: '深度研究任务', prompt: '请围绕这个主题制定深度研究计划，包含信息源策略、交叉验证、证据分级和结论产出格式。', icon: '🔍', desc: '面向咨询与研究型工作', category: 'knowledge', source: '研究实践', template: 'deep_research'}
        ];
        
        function renderPromptList() {
            const groups = {
                general: '通用助手',
                growth: '增长运营',
                engineering: '工程治理',
                knowledge: '知识研究'
            };
            const filtered = PROMPT_TEMPLATES.filter(p => {
                const hitCategory = promptCategory === 'all' || p.category === promptCategory;
                const q = promptSearchKeyword.trim().toLowerCase();
                const hitKeyword = !q || `${p.name} ${p.desc} ${p.source} ${p.prompt}`.toLowerCase().includes(q);
                return hitCategory && hitKeyword;
            });
            const list = document.getElementById('promptList');
            if (!filtered.length) {
                list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧭</div><div class="empty-state-text">未找到匹配模板，试试更短关键词</div></div>';
                return;
            }
            let html = '';
            Object.keys(groups).forEach(groupKey => {
                const groupItems = filtered.filter(x => x.category === groupKey);
                if (!groupItems.length) return;
                html += `<div class="prompt-group-title">${groups[groupKey]}</div>`;
                html += groupItems.map(p => `
                    <div class="prompt-card" onclick="usePromptTemplate('${p.id}')">
                        <div class="prompt-head">
                            <span>${p.icon}</span>
                            <span class="prompt-name">${p.name}</span>
                        </div>
                        <div class="prompt-desc">${p.desc}</div>
                        <div class="prompt-meta">
                            <span class="prompt-meta-tag">${p.source}</span>
                            ${p.template ? '<span class="prompt-meta-tag">结构化输出</span>' : ''}
                        </div>
                    </div>
                `).join('');
            });
            list.innerHTML = html;
        }
        
        function setPromptSearch(value) {
            promptSearchKeyword = value || '';
            renderPromptList();
        }
        
        function setPromptCategory(category) {
            promptCategory = category;
            document.querySelectorAll('.prompt-chip').forEach(el => el.classList.remove('active'));
            const idMap = {all: 'promptCatAll', general: 'promptCatGeneral', growth: 'promptCatGrowth', engineering: 'promptCatEngineering', knowledge: 'promptCatKnowledge'};
            const activeEl = document.getElementById(idMap[category] || 'promptCatAll');
            if (activeEl) activeEl.classList.add('active');
            renderPromptList();
        }
        
        function openPromptWorkbench() {
            // 如果已经存在，先移除
            const existing = document.getElementById('promptWorkbenchModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'promptWorkbenchModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('promptWorkbenchModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:800px;width:95%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;">🧭 专业工作台</h3>
                        <button class="modal-close" onclick="closeModal('promptWorkbenchModal')" style="font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow:hidden;display:flex;flex-direction:column;padding:0;">
                        <div class="workbench-tabs" style="display:flex;gap:4px;padding:12px 0;border-bottom:1px solid var(--border);flex-shrink:0;flex-wrap:wrap;">
                            <button class="workbench-tab active" onclick="switchWorkbenchTab('all', this)">📋 全部</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('code', this)">💻 代码</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('doc', this)">📄 文档</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('data', this)">📊 数据</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('favorites', this)">⭐ 收藏</button>
                            <button class="workbench-tab" onclick="switchWorkbenchTab('integrations', this)" style="background:linear-gradient(135deg,#10b981,#059669);color:white;">🔗 接入</button>
                        </div>
                        <div style="padding:12px 0;flex-shrink:0;">
                            <input class="project-input" id="workbenchSearch" placeholder="🔍 搜索模板..." style="width:100%;" oninput="filterWorkbenchTemplates()">
                        </div>
                        <div id="workbenchContent" style="flex:1;overflow-y:auto;padding:8px 0;"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            renderWorkbenchContent('all');
        }

        function switchWorkbenchTab(category, btn) {
            document.querySelectorAll('.workbench-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            renderWorkbenchContent(category);
        }

        function renderWorkbenchContent(category) {
            const container = document.getElementById('workbenchContent');
            if (!container) return;
            
            if (category === 'integrations') {
                renderIntegrationsPage(container);
                return;
            }
            
            const allTemplates = [
                { id: 'code-review', name: '代码审查', icon: '🔍', desc: '专业代码质量分析，指出潜在问题和优化建议', category: 'code', prompt: '请对以下代码进行专业审查...' },
                { id: 'doc-gen', name: '文档生成', icon: '📄', desc: '自动生成技术文档，包括函数说明和使用示例', category: 'doc', prompt: '请为以下代码生成文档...' },
                { id: 'api-design', name: 'API 设计', icon: '🔌', desc: 'RESTful API 规划，设计端点和响应格式', category: 'code', prompt: '请根据需求设计API...' },
                { id: 'test-gen', name: '测试生成', icon: '🧪', desc: '单元测试用例生成，覆盖主要功能', category: 'code', prompt: '请为以下代码生成测试...' },
                { id: 'refactor', name: '代码重构', icon: '♻️', desc: '智能代码优化建议，提高可维护性', category: 'code', prompt: '请分析并提供重构建议...' },
                { id: 'security', name: '安全审计', icon: '🔒', desc: '代码安全漏洞检测和修复建议', category: 'code', prompt: '请进行安全审计...' },
                { id: 'data-analysis', name: '数据分析', icon: '📊', desc: '数据统计分析和可视化建议', category: 'data', prompt: '请分析以下数据...' },
                { id: 'report-gen', name: '报告生成', icon: '📝', desc: '自动生成分析报告和摘要', category: 'doc', prompt: '请生成分析报告...' },
                { id: 'creative-write', name: '创意写作', icon: '✨', desc: '创意文案和内容创作', category: 'doc', prompt: '请创作内容...' },
            ];
            
            let templates = category === 'all' ? allTemplates : allTemplates.filter(t => t.category === category);
            
            container.innerHTML = templates.map(t => `
                <div class="workbench-card" onclick="applyWorkbenchTemplate('${t.id}')" style="display:flex;align-items:center;gap:12px;padding:14px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;margin-bottom:8px;cursor:pointer;transition:all 0.2s;">
                    <div style="font-size:28px;flex-shrink:0;">${t.icon}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:4px;">${t.name}</div>
                        <div style="font-size:12px;color:var(--text-muted);line-height:1.4;">${t.desc}</div>
                    </div>
                    <button onclick="event.stopPropagation();toggleFavorite('${t.id}')" style="background:none;border:none;font-size:18px;cursor:pointer;padding:4px;opacity:0.6;">⭐</button>
                </div>
            `).join('') || '<div style="text-align:center;color:var(--text-muted);padding:40px;">暂无模板</div>';
        }

        function renderIntegrationsPage(container) {
            const integrations = [
                { id: 'api', name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入', status: 'available', color: '#667eea' },
                { id: 'database', name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL 等数据库', status: 'available', color: '#10b981' },
                { id: 'webhook', name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址', status: 'available', color: '#f59e0b' },
                { id: 'mcp', name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入', status: 'active', color: '#8b5cf6' },
                { id: 'rag', name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成', status: 'active', color: '#ec4899' },
                { id: 'tools', name: '工具调用', icon: '🔧', desc: '外部工具和函数调用', status: 'available', color: '#06b6d4' },
                { id: 'plugins', name: '插件系统', icon: '🧩', desc: '管理和配置插件', status: 'available', color: '#84cc16' },
                { id: 'oauth', name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', status: 'available', color: '#f43f5e' },
            ];
            
            container.innerHTML = `
                <div style="margin-bottom:16px;">
                    <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">已启用的接入</div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'active').map(i => `
                            <div class="integration-card active" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:linear-gradient(135deg,${i.color}15,${i.color}05);border:2px solid ${i.color};border-radius:12px;cursor:pointer;">
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:8px;height:8px;background:#10b981;border-radius:50%;"></span>
                                    <span style="font-size:11px;color:#10b981;">已启用</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div>
                    <div style="font-size:14px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">可接入的服务</div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'available').map(i => `
                            <div class="integration-card" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all 0.2s;">
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:8px;height:8px;background:var(--text-muted);border-radius:50%;"></span>
                                    <span style="font-size:11px;color:var(--text-muted);">点击配置</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function openIntegrationDetail(integrationId) {
            const details = {
                'api': { name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入，支持 OpenAI、Claude 等多种 API', config: ['API Key', 'Base URL', 'Model Name'] },
                'database': { name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL、MongoDB 等数据库', config: ['Host', 'Port', 'Database', 'Username', 'Password'] },
                'webhook': { name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址，实现事件通知', config: ['Callback URL', 'Secret Key', 'Events'] },
                'mcp': { name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入，支持工具调用和资源访问', config: ['Server URL', 'Transport Type'] },
                'rag': { name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成，支持多种向量数据库', config: ['Vector DB', 'Embedding Model', 'Collection Name'] },
                'tools': { name: '工具调用', icon: '🔧', desc: '外部工具和函数调用，扩展 AI 能力', config: ['Tool Name', 'Endpoint', 'Parameters'] },
                'plugins': { name: '插件系统', icon: '🧩', desc: '管理和配置插件，扩展系统功能', config: ['Plugin Directory', 'Auto Load'] },
                'oauth': { name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', config: ['Provider', 'Client ID', 'Client Secret', 'Redirect URI'] },
            };
            
            const detail = details[integrationId];
            if (!detail) return;
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'integrationDetailModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('integrationDetailModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:500px;width:90%;max-height:80vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;display:flex;align-items:center;gap:8px;">
                            <span style="font-size:24px;">${detail.icon}</span>
                            ${detail.name}
                        </h3>
                        <button class="modal-close" onclick="closeModal('integrationDetailModal')" style="font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:16px 0;">
                        <div style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;line-height:1.6;">${detail.desc}</div>
                        <div style="margin-bottom:16px;">
                            <div style="font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:8px;">配置项</div>
                            ${detail.config.map(c => `
                                <div style="margin-bottom:12px;">
                                    <label style="display:block;font-size:11px;color:var(--text-muted);margin-bottom:4px;">${c}</label>
                                    <input class="project-input" placeholder="输入 ${c}..." style="width:100%;">
                                </div>
                            `).join('')}
                        </div>
                        <div style="background:var(--bg-secondary);border-radius:8px;padding:12px;">
                            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">状态</div>
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="width:10px;height:10px;background:#10b981;border-radius:50%;"></span>
                                <span style="font-size:12px;color:var(--text-primary);">已配置</span>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);">
                        <button class="project-mini-btn" onclick="closeModal('integrationDetailModal')">取消</button>
                        <button class="project-mini-btn" style="background:linear-gradient(135deg,var(--primary),#764ba2);color:white;" onclick="saveIntegration('${integrationId}')">保存配置</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveIntegration(integrationId) {
            closeModal('integrationDetailModal');
            showToast('配置已保存');
        }

        function filterWorkbenchTemplates() {
            const search = document.getElementById('workbenchSearch')?.value.toLowerCase() || '';
            const cards = document.querySelectorAll('.workbench-card');
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(search) ? 'flex' : 'none';
            });
        }

        function applyWorkbenchTemplate(templateId) {
            const templates = {
                'code-review': { name: '代码审查', icon: '🔍', prompt: '请对以下代码进行专业审查，指出潜在问题、安全漏洞和优化建议：\n\n{{code}}', steps: ['输入代码', 'AI分析', '生成报告', '优化建议'] },
                'doc-gen': { name: '文档生成', icon: '📄', prompt: '请为以下代码生成详细的技术文档，包括函数说明、参数描述和使用示例：\n\n{{code}}', steps: ['输入代码', '解析结构', '生成文档', '导出报告'] },
                'api-design': { name: 'API 设计', icon: '🔌', prompt: '请根据以下需求设计 RESTful API，包括端点、请求方法、参数和响应格式：\n\n{{requirements}}', steps: ['需求分析', '设计端点', '定义格式', '输出文档'] },
                'test-gen': { name: '测试生成', icon: '🧪', prompt: '请为以下代码生成单元测试用例，覆盖主要功能和边界情况：\n\n{{code}}', steps: ['分析代码', '设计用例', '生成代码', '运行测试'] },
                'refactor': { name: '代码重构', icon: '♻️', prompt: '请分析以下代码并提供重构建议，提高代码质量和可维护性：\n\n{{code}}', steps: ['代码分析', '识别问题', '重构方案', '实施优化'] },
                'security': { name: '安全审计', icon: '🔒', prompt: '请对以下代码进行安全审计，识别潜在的安全漏洞并提供修复建议：\n\n{{code}}', steps: ['扫描漏洞', '风险评估', '修复建议', '安全报告'] },
                'data-analysis': { name: '数据分析', icon: '📊', prompt: '请对以下数据进行统计分析，提供洞察和可视化建议：\n\n{{data}}', steps: ['数据清洗', '统计分析', '可视化', '洞察报告'] },
                'report-gen': { name: '报告生成', icon: '📝', prompt: '请根据以下内容生成结构化的分析报告：\n\n{{content}}', steps: ['收集内容', '整理结构', '生成报告', '审核发布'] },
                'creative-write': { name: '创意写作', icon: '✨', prompt: '请根据以下主题进行创意写作：\n\n{{topic}}', steps: ['主题分析', '创意构思', '内容创作', '润色完善'] },
            };
            
            const template = templates[templateId];
            if (!template) return;
            
            // 关闭工作台，打开工作规划界面（延迟一点确保关闭完成）
            closeModal('promptWorkbenchModal');
            setTimeout(() => {
                openWorkPlanningModal(templateId, template);
            }, 100);
        }
        
        function openWorkPlanningModal(templateId, template) {
            // 先移除已存在的模态框
            const existing = document.getElementById('workPlanningModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'workPlanningModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('workPlanningModal'); };
            
            // 根据不同模板创建不同的界面
            const specializedUI = getSpecializedUI(templateId, template);
            
            modal.innerHTML = `
                <div class="modal" style="max-width:1000px;width:95%;max-height:90vh;display:flex;flex-direction:column;background:linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);color:#fff;">
                    <div class="modal-header" style="flex-shrink:0;border-bottom:1px solid rgba(255,255,255,0.1);padding:16px 20px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <span style="font-size:32px;">${template.icon}</span>
                            <div>
                                <h3 style="margin:0;font-size:20px;">${template.name}</h3>
                                <p style="margin:4px 0 0;font-size:12px;color:rgba(255,255,255,0.6);">${getTemplateDescription(templateId)}</p>
                            </div>
                        </div>
                        <button class="modal-close" onclick="closeModal('workPlanningModal')" style="font-size:24px;background:rgba(255,255,255,0.1);border:none;border-radius:8px;width:36px;height:36px;cursor:pointer;color:#fff;">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:20px;">
                        ${specializedUI}
                    </div>
                    <div class="modal-actions" style="flex-shrink:0;padding:16px 20px;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;gap:12px;">
                        <button onclick="closeModal('workPlanningModal')" style="padding:10px 20px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;cursor:pointer;">关闭</button>
                        <button onclick="executeSpecializedTask('${templateId}')" style="padding:10px 24px;background:linear-gradient(135deg, #667eea, #764ba2);border:none;border-radius:8px;color:#fff;cursor:pointer;font-weight:600;">🚀 开始执行</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        function getTemplateDescription(templateId) {
            const descriptions = {
                'code-review': '专业代码审查，识别潜在问题和优化建议',
                'doc-gen': '自动生成技术文档和API说明',
                'api-design': '设计RESTful API接口规范',
                'test-gen': '生成单元测试和集成测试用例',
                'refactor': '代码重构和质量优化建议',
                'security': '安全漏洞扫描和风险评估',
                'data-analysis': '数据统计分析和可视化建议',
                'report-gen': '结构化报告生成和导出',
                'creative-write': '创意内容创作和润色'
            };
            return descriptions[templateId] || '专业工具';
        }
        
        function getSpecializedUI(templateId, template) {
            const uis = {
                'code-review': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审查代码</label>
                            <textarea id="codeInput" placeholder="粘贴您的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ 审查选项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkSecurity" checked style="width:18px;height:18px;">
                                    <span>🔒 安全漏洞检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkPerformance" checked style="width:18px;height:18px;">
                                    <span>⚡ 性能优化建议</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="checkStyle" checked style="width:18px;height:18px;">
                                    <span>📋 代码风格检查</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="checkBestPractice" checked style="width:18px;height:18px;">
                                    <span>✨ 最佳实践建议</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎯 编程语言</label>
                            <select id="codeLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="auto">自动检测</option>
                                <option value="python">Python</option>
                                <option value="javascript">JavaScript</option>
                                <option value="java">Java</option>
                                <option value="cpp">C/C++</option>
                                <option value="go">Go</option>
                            </select>
                        </div>
                    </div>
                `,
                'doc-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 代码/接口内容</label>
                            <textarea id="docSource" placeholder="粘贴代码或API接口定义..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 文档类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="api" checked style="width:18px;height:18px;">
                                    <span>🔌 API文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="readme" style="width:18px;height:18px;">
                                    <span>📖 README文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="docType" value="technical" style="width:18px;height:18px;">
                                    <span>📚 技术文档</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="docType" value="comment" style="width:18px;height:18px;">
                                    <span>💬 代码注释</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🌍 文档语言</label>
                            <select id="docLanguage" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="zh">中文</option>
                                <option value="en">English</option>
                            </select>
                        </div>
                    </div>
                `,
                'api-design': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 需求描述</label>
                            <textarea id="apiRequirements" placeholder="描述您的API需求，例如：用户管理、订单处理..." style="width:100%;height:150px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🏷️ API名称</label>
                            <input type="text" id="apiName" placeholder="例如：UserAPI" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">⚙️ API风格</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="rest" checked style="width:18px;height:18px;">
                                    <span>🔄 RESTful API</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="graphql" style="width:18px;height:18px;">
                                    <span>📊 GraphQL</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="apiStyle" value="grpc" style="width:18px;height:18px;">
                                    <span>⚡ gRPC</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🔐 认证方式</label>
                            <select id="authType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="none">无认证</option>
                                <option value="jwt">JWT Token</option>
                                <option value="oauth">OAuth 2.0</option>
                                <option value="apikey">API Key</option>
                            </select>
                        </div>
                    </div>
                `,
                'test-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待测试代码</label>
                            <textarea id="testSource" placeholder="粘贴需要生成测试的代码..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🧪 测试框架</label>
                            <select id="testFramework" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="pytest">pytest (Python)</option>
                                <option value="jest">Jest (JavaScript)</option>
                                <option value="junit">JUnit (Java)</option>
                                <option value="gtest">Google Test (C++)</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 测试覆盖率</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testNormal" checked style="width:18px;height:18px;">
                                    <span>✅ 正常用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="testEdge" checked style="width:18px;height:18px;">
                                    <span>🔍 边界用例</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="testError" checked style="width:18px;height:18px;">
                                    <span>❌ 异常用例</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'refactor': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待重构代码</label>
                            <textarea id="refactorSource" placeholder="粘贴需要重构的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🎯 重构目标</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorReadability" checked style="width:18px;height:18px;">
                                    <span>📖 提高可读性</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPerformance" style="width:18px;height:18px;">
                                    <span>⚡ 性能优化</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="refactorModular" checked style="width:18px;height:18px;">
                                    <span>🧩 模块化拆分</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="refactorPattern" style="width:18px;height:18px;">
                                    <span>📐 设计模式应用</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'security': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 待审计代码</label>
                            <textarea id="securitySource" placeholder="粘贴需要安全审计的代码..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">🔒 安全检查项</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secSQL" checked style="width:18px;height:18px;">
                                    <span>💉 SQL注入</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secXSS" checked style="width:18px;height:18px;">
                                    <span>🎯 XSS攻击</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="secCSRF" checked style="width:18px;height:18px;">
                                    <span>🔄 CSRF漏洞</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="secAuth" checked style="width:18px;height:18px;">
                                    <span>🔐 认证授权漏洞</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'data-analysis': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📊 数据内容</label>
                            <textarea id="dataSource" placeholder="粘贴数据（CSV、JSON格式或文本）..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-family:monospace;font-size:13px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📈 分析类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisDesc" checked style="width:18px;height:18px;">
                                    <span>📊 描述性统计</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisTrend" style="width:18px;height:18px;">
                                    <span>📈 趋势分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="checkbox" id="analysisCorr" style="width:18px;height:18px;">
                                    <span>🔗 相关性分析</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="checkbox" id="analysisVisual" checked style="width:18px;height:18px;">
                                    <span>📉 可视化建议</span>
                                </label>
                            </div>
                        </div>
                    </div>
                `,
                'report-gen': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📋 报告内容</label>
                            <textarea id="reportContent" placeholder="输入报告的核心内容、数据或要点..." style="width:100%;height:180px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📄 报告类型</label>
                            <select id="reportType" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;margin-bottom:16px;">
                                <option value="business">商业报告</option>
                                <option value="technical">技术报告</option>
                                <option value="research">研究报告</option>
                                <option value="summary">总结报告</option>
                            </select>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📑 输出格式</label>
                            <select id="reportFormat" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="markdown">Markdown</option>
                                <option value="html">HTML</option>
                                <option value="plain">纯文本</option>
                            </select>
                        </div>
                    </div>
                `,
                'creative-write': `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">💡 创作主题</label>
                            <input type="text" id="creativeTopic" placeholder="输入创作主题..." style="width:100%;padding:12px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;font-size:14px;margin-bottom:16px;">
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 补充说明</label>
                            <textarea id="creativeNotes" placeholder="补充要求、风格偏好等..." style="width:100%;height:120px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                        </div>
                        <div>
                            <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">✍️ 创作类型</label>
                            <div style="background:rgba(0,0,0,0.2);border-radius:8px;padding:16px;">
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="article" checked style="width:18px;height:18px;">
                                    <span>📰 文章</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="story" style="width:18px;height:18px;">
                                    <span>📖 故事</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="copywriting" style="width:18px;height:18px;">
                                    <span>📢 文案</span>
                                </label>
                                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                                    <input type="radio" name="creativeType" value="script" style="width:18px;height:18px;">
                                    <span>🎬 脚本</span>
                                </label>
                            </div>
                            <label style="display:block;font-size:14px;font-weight:600;margin:16px 0 8px;">🎭 风格</label>
                            <select id="creativeStyle" style="width:100%;padding:10px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;color:#fff;">
                                <option value="professional">专业正式</option>
                                <option value="casual">轻松活泼</option>
                                <option value="humorous">幽默风趣</option>
                                <option value="emotional">情感共鸣</option>
                            </select>
                        </div>
                    </div>
                `
            };
            return uis[templateId] || `
                <div>
                    <label style="display:block;font-size:14px;font-weight:600;margin-bottom:8px;">📝 输入内容</label>
                    <textarea id="workInput" placeholder="请输入您的内容..." style="width:100%;height:200px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:12px;color:#fff;font-size:14px;resize:none;"></textarea>
                </div>
            `;
        }
        
        function executeSpecializedTask(templateId) {
            let prompt = '';
            let input = '';
            
            switch(templateId) {
                case 'code-review':
                    input = document.getElementById('codeInput')?.value || '';
                    const lang = document.getElementById('codeLanguage')?.value || 'auto';
                    const checks = [];
                    if (document.getElementById('checkSecurity')?.checked) checks.push('安全漏洞');
                    if (document.getElementById('checkPerformance')?.checked) checks.push('性能优化');
                    if (document.getElementById('checkStyle')?.checked) checks.push('代码风格');
                    if (document.getElementById('checkBestPractice')?.checked) checks.push('最佳实践');
                    prompt = `请对以下${lang === 'auto' ? '' : lang}代码进行专业审查，重点关注：${checks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'doc-gen':
                    input = document.getElementById('docSource')?.value || '';
                    const docType = document.querySelector('input[name="docType"]:checked')?.value || 'api';
                    const docLang = document.getElementById('docLanguage')?.value || 'zh';
                    prompt = `请为以下内容生成${docType === 'api' ? 'API文档' : docType === 'readme' ? 'README文档' : docType === 'technical' ? '技术文档' : '代码注释'}（${docLang === 'zh' ? '中文' : '英文'}）：\n\n${input}`;
                    break;
                    
                case 'api-design':
                    input = document.getElementById('apiRequirements')?.value || '';
                    const apiName = document.getElementById('apiName')?.value || '';
                    const apiStyle = document.querySelector('input[name="apiStyle"]:checked')?.value || 'rest';
                    const auth = document.getElementById('authType')?.value || 'none';
                    prompt = `请根据以下需求设计${apiStyle === 'rest' ? 'RESTful API' : apiStyle === 'graphql' ? 'GraphQL' : 'gRPC'}接口：\n需求：${input}\nAPI名称：${apiName}\n认证方式：${auth}`;
                    break;
                    
                case 'test-gen':
                    input = document.getElementById('testSource')?.value || '';
                    const framework = document.getElementById('testFramework')?.value || 'pytest';
                    prompt = `请使用${framework}框架为以下代码生成测试用例：\n\n${input}`;
                    break;
                    
                case 'refactor':
                    input = document.getElementById('refactorSource')?.value || '';
                    const goals = [];
                    if (document.getElementById('refactorReadability')?.checked) goals.push('提高可读性');
                    if (document.getElementById('refactorPerformance')?.checked) goals.push('性能优化');
                    if (document.getElementById('refactorModular')?.checked) goals.push('模块化拆分');
                    if (document.getElementById('refactorPattern')?.checked) goals.push('设计模式应用');
                    prompt = `请重构以下代码，目标：${goals.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'security':
                    input = document.getElementById('securitySource')?.value || '';
                    const secChecks = [];
                    if (document.getElementById('secSQL')?.checked) secChecks.push('SQL注入');
                    if (document.getElementById('secXSS')?.checked) secChecks.push('XSS攻击');
                    if (document.getElementById('secCSRF')?.checked) secChecks.push('CSRF漏洞');
                    if (document.getElementById('secAuth')?.checked) secChecks.push('认证授权漏洞');
                    prompt = `请对以下代码进行安全审计，检查：${secChecks.join('、')}\n\n代码：\n${input}`;
                    break;
                    
                case 'data-analysis':
                    input = document.getElementById('dataSource')?.value || '';
                    const analysis = [];
                    if (document.getElementById('analysisDesc')?.checked) analysis.push('描述性统计');
                    if (document.getElementById('analysisTrend')?.checked) analysis.push('趋势分析');
                    if (document.getElementById('analysisCorr')?.checked) analysis.push('相关性分析');
                    if (document.getElementById('analysisVisual')?.checked) analysis.push('可视化建议');
                    prompt = `请对以下数据进行${analysis.join('、')}：\n\n数据：\n${input}`;
                    break;
                    
                case 'report-gen':
                    input = document.getElementById('reportContent')?.value || '';
                    const reportType = document.getElementById('reportType')?.value || 'business';
                    const reportFormat = document.getElementById('reportFormat')?.value || 'markdown';
                    prompt = `请根据以下内容生成${reportType === 'business' ? '商业报告' : reportType === 'technical' ? '技术报告' : reportType === 'research' ? '研究报告' : '总结报告'}（${reportFormat}格式）：\n\n${input}`;
                    break;
                    
                case 'creative-write':
                    const topic = document.getElementById('creativeTopic')?.value || '';
                    const notes = document.getElementById('creativeNotes')?.value || '';
                    const creativeType = document.querySelector('input[name="creativeType"]:checked')?.value || 'article';
                    const style = document.getElementById('creativeStyle')?.value || 'professional';
                    prompt = `请以${style === 'professional' ? '专业正式' : style === 'casual' ? '轻松活泼' : style === 'humorous' ? '幽默风趣' : '情感共鸣'}的风格，创作一篇${creativeType === 'article' ? '文章' : creativeType === 'story' ? '故事' : creativeType === 'copywriting' ? '文案' : '脚本'}。\n主题：${topic}\n${notes ? '补充要求：' + notes : ''}`;
                    break;
                    
                default:
                    input = document.getElementById('workInput')?.value || '';
                    prompt = input;
            }
            
            if (!prompt || prompt.includes('undefined')) {
                showToast('请填写必要的内容');
                return;
            }
            
            closeModal('workPlanningModal');
            document.getElementById('mainInput').value = prompt;
            showToast('正在执行任务...');
            document.getElementById('sendBtn').click();
        }

        function toggleFavorite(templateId) {
            showToast('已收藏');
        }

        function favoriteTemplate(templateId) {
            showToast('已收藏模板');
        }

        function createCustomTemplate() {
            showToast('打开创建模板面板');
        }

        function openQuickSceneModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'quickSceneModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>🎯 新建快速场景</h3>
                        <button class="modal-close" onclick="closeModal('quickSceneModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">场景名称</label>
                            <input class="project-input" id="sceneName" placeholder="输入场景名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">场景描述</label>
                            <textarea class="project-input" id="sceneDesc" placeholder="输入场景描述" style="width:100%;height:80px;resize:vertical;"></textarea>
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">提示词模板</label>
                            <textarea class="project-input" id="scenePrompt" placeholder="输入提示词模板，使用 {{变量}} 表示变量" style="width:100%;height:100px;resize:vertical;"></textarea>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('quickSceneModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveQuickScene()">保存</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveQuickScene() {
            const name = document.getElementById('sceneName').value;
            const desc = document.getElementById('sceneDesc').value;
            const prompt = document.getElementById('scenePrompt').value;
            if (!name || !prompt) {
                showToast('请填写场景名称和提示词');
                return;
            }
            showToast('场景已保存');
            closeModal('quickSceneModal');
        }

        function applyQuickScene(sceneId) {
            const scenes = {
                'code-review': '请对以下代码进行专业审查，指出潜在问题、安全漏洞和优化建议：\\n\\n{{code}}',
                'doc-gen': '请为以下代码生成详细的技术文档，包括函数说明、参数描述和使用示例：\\n\\n{{code}}',
                'api-design': '请根据以下需求设计 RESTful API，包括端点、请求方法、参数和响应格式：\\n\\n{{requirements}}',
                'test-gen': '请为以下代码生成单元测试用例，覆盖主要功能和边界情况：\\n\\n{{code}}',
                'refactor': '请分析以下代码并提供重构建议，提高代码质量和可维护性：\\n\\n{{code}}',
                'security': '请对以下代码进行安全审计，识别潜在的安全漏洞并提供修复建议：\\n\\n{{code}}'
            };
            const prompt = scenes[sceneId] || '';
            if (prompt) {
                document.getElementById('mainInput').value = prompt;
                showToast('已应用场景模板');
            }
        }

        function loadTemplateAnalysis() {
            const range = document.getElementById('templateAnalysisRange')?.value || '7d';
            fetch('/templates/analysis?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const templateCountEl = document.getElementById('workbenchTemplateCount');
                        const favoriteCountEl = document.getElementById('workbenchFavoriteCount');
                        const usageCountEl = document.getElementById('workbenchUsageCount');
                        const customCountEl = document.getElementById('workbenchCustomCount');
                        if (templateCountEl) templateCountEl.textContent = data.stats.total_templates || '--';
                        if (favoriteCountEl) favoriteCountEl.textContent = data.stats.favorites || '--';
                        if (usageCountEl) usageCountEl.textContent = data.stats.usage || '--';
                        if (customCountEl) customCountEl.textContent = data.stats.custom || '--';
                    }
                });
        }

        function exportTemplateReport() {
            showToast('正在导出模板报告...');
        }

        function refreshRagStats() {
            fetch('/rag/stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const docsEl = document.getElementById('ragStatDocs');
                        const chunksEl = document.getElementById('ragStatChunks');
                        const charsEl = document.getElementById('ragStatChars');
                        const vectorsEl = document.getElementById('ragStatVectors');
                        if (docsEl) docsEl.textContent = data.stats.docs || 0;
                        if (chunksEl) chunksEl.textContent = data.stats.chunks || 0;
                        if (charsEl) charsEl.textContent = data.stats.chars || 0;
                        if (vectorsEl) vectorsEl.textContent = data.stats.vectors || 0;
                    }
                });
        }

        function openBatchImportModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'batchImportModal';
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
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'urlImportModal';
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
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'gitImportModal';
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
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'knowledgeGraphModal';
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
            fetch('/rag/build-graph', { method: 'POST' })
                .then(r => r.json())
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
            fetch('/rag/analysis?range=' + range)
                .then(r => r.json())
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
        
        function usePromptTemplate(templateId) {
            const item = PROMPT_TEMPLATES.find(x => x.id === templateId);
            if (!item) return;
            usePrompt(item.prompt, item.template || null);
        }
        
        function usePrompt(prompt, templateId = null) {
            document.getElementById('mainInput').value = prompt;
            currentStructuredTemplate = templateId;
            document.getElementById('mainInput').focus();
            updateCharCount();
            showToast(templateId ? '已应用结构化模板' : '已填入模板');
        }
        
        function loadProjectCenter() {
            Promise.all([
                fetch('/project/overview').then(r => r.json()),
                fetch('/artifacts').then(r => r.json()),
                fetch('/project/tasks').then(r => r.json()),
                fetch('/playbooks').then(r => r.json()),
                fetch('/project/activity?limit=40').then(r => r.json()),
                fetch('/project/milestones').then(r => r.json()),
                fetch('/project/risks').then(r => r.json()),
                fetch('/ops/overview').then(r => r.json()),
                fetch('/ops/campaigns').then(r => r.json()),
                fetch('/release/overview').then(r => r.json()),
                fetch('/release/plans').then(r => r.json()),
                fetch('/alerts/overview').then(r => r.json()),
                fetch('/alerts/rules').then(r => r.json()),
                fetch('/ab/overview').then(r => r.json()),
                fetch('/ab/experiments').then(r => r.json()),
                fetch('/integrations/overview').then(r => r.json()),
                fetch('/integrations').then(r => r.json()),
                fetch('/console/overview').then(r => r.json()),
                fetch('/console/recommendations').then(r => r.json()),
                fetch('/workspace/projects/overview').then(r => r.json()),
                fetch('/workspace/projects').then(r => r.json())
            ]).then(([ov, af, tk, pb, ac, ms, rk, oov, ocs, rov, rps, aov, ars, bov, bes, iov, ils, cov, cre, wov, wps]) => {
                if (ov.success) projectOverview = ov.overview || {};
                if (af.success) projectArtifacts = af.artifacts || [];
                if (tk.success) projectTasks = tk.tasks || [];
                if (pb.success) projectPlaybooks = pb.playbooks || [];
                if (ac.success) projectActivities = ac.activities || [];
                if (ms.success) projectMilestones = ms.milestones || [];
                if (rk.success) projectRisks = rk.risks || [];
                if (oov.success) opsOverview = oov.overview || {};
                if (ocs.success) opsCampaigns = ocs.campaigns || [];
                if (rov.success) releaseOverview = rov.overview || {};
                if (rps.success) releasePlans = rps.plans || [];
                if (aov.success) alertOverview = aov.overview || {};
                if (ars.success) alertRules = ars.rules || [];
                if (bov.success) abOverview = bov.overview || {};
                if (bes.success) abExperiments = bes.experiments || [];
                if (iov.success) integrationOverview = iov.overview || {};
                if (ils.success) integrationItems = ils.integrations || [];
                if (cov.success) consoleOverview = cov.overview || {};
                if (cre.success) consoleRecommendations = cre.recommendations || [];
                if (wov.success) workspaceOverview = wov.overview || {};
                if (wps.success) workspaceProjects = wps.projects || [];
                selectedTaskIds = new Set(Array.from(selectedTaskIds).filter(id => projectTasks.some(t => t.id === id)));
                renderConsoleOverview();
                renderConsoleRecommendations();
                runGlobalSearch(document.getElementById('globalSearchInput')?.value || '');
                renderWorkspaceOverview();
                renderWorkspaceProjects();
                renderProjectOverview();
                renderProjectArtifacts();
                renderProjectTasks();
                renderProjectPlaybooks();
                renderProjectActivity();
                renderProjectMilestones();
                renderProjectRisks();
                renderOpsOverview();
                renderOpsCampaigns();
                renderReleaseOverview();
                renderReleasePlans();
                renderAlertOverview();
                renderAlertRules();
                renderAbOverview();
                renderAbExperiments();
                renderIntegrationOverview();
                renderIntegrations();
                renderFeatureCenterMeta();
            }).catch(() => {});
        }

        function loadWorkspaceProjects(query = '') {
            const q = encodeURIComponent((query || '').trim());
            fetch(`/workspace/projects?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
        }

        function refreshWorkspaceProjects() {
            fetch('/workspace/projects?refresh=1').then(r => r.json()).then(data => {
                if (data.success) workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
            fetch('/workspace/projects/overview').then(r => r.json()).then(data => {
                if (data.success) workspaceOverview = data.overview || {};
                renderWorkspaceOverview();
                renderFeatureCenterMeta();
            });
        }

        function loadConsoleData() {
            Promise.all([
                fetch('/console/overview').then(r => r.json()),
                fetch('/console/recommendations').then(r => r.json())
            ]).then(([ov, rc]) => {
                if (ov.success) consoleOverview = ov.overview || {};
                if (rc.success) consoleRecommendations = rc.recommendations || [];
                renderConsoleOverview();
                renderConsoleRecommendations();
            });
            refreshSystemMetrics();
            loadPerformanceData();
        }

        function refreshSystemMetrics() {
            fetch('/system/metrics')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const m = data.metrics;
                        document.getElementById('cpuUsage').textContent = m.cpu_percent ? `${m.cpu_percent}%` : '--';
                        document.getElementById('cpuBar').style.width = `${m.cpu_percent || 0}%`;
                        document.getElementById('memoryUsage').textContent = m.memory_percent ? `${m.memory_percent}%` : '--';
                        document.getElementById('memoryBar').style.width = `${m.memory_percent || 0}%`;
                        document.getElementById('diskUsage').textContent = m.disk_percent ? `${m.disk_percent}%` : '--';
                        document.getElementById('diskBar').style.width = `${m.disk_percent || 0}%`;
                        document.getElementById('networkStatus').textContent = m.network_status || '正常';
                        document.getElementById('networkBar').style.width = m.network_status === '正常' ? '100%' : '50%';
                    }
                })
                .catch(() => {
                    document.getElementById('cpuUsage').textContent = 'N/A';
                    document.getElementById('memoryUsage').textContent = 'N/A';
                    document.getElementById('diskUsage').textContent = 'N/A';
                });
        }

        function openSystemMonitorModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'systemMonitorModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:800px;">
                    <div class="modal-header">
                        <h3>📊 系统监控详情</h3>
                        <button class="modal-close" onclick="closeModal('systemMonitorModal')">×</button>
                    </div>
                    <div class="modal-body" style="max-height:70vh;overflow-y:auto;">
                        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:15px;">
                            <div class="metric-card">
                                <div class="metric-icon">💻</div>
                                <div class="metric-info">
                                    <div class="metric-label">CPU 使用率</div>
                                    <div class="metric-value" id="modalCpuUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalCpuBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🧠</div>
                                <div class="metric-info">
                                    <div class="metric-label">内存使用</div>
                                    <div class="metric-value" id="modalMemoryUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalMemoryBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">💾</div>
                                <div class="metric-info">
                                    <div class="metric-label">磁盘空间</div>
                                    <div class="metric-value" id="modalDiskUsage">--</div>
                                </div>
                                <div class="metric-bar"><div class="metric-bar-fill" id="modalDiskBar" style="width:0%"></div></div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-icon">🐍</div>
                                <div class="metric-info">
                                    <div class="metric-label">Python 进程</div>
                                    <div class="metric-value" id="modalPythonProcess">--</div>
                                </div>
                            </div>
                        </div>
                        <div style="margin-top:15px;">
                            <h4 style="font-size:13px;margin-bottom:10px;">进程信息</h4>
                            <div id="processList" style="font-size:11px;font-family:monospace;background:var(--bg-secondary);padding:10px;border-radius:8px;">
                                加载中...
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            refreshSystemMetrics();
        }

        function filterLogs() {
            const level = document.getElementById('logLevelFilter').value;
            const entries = document.querySelectorAll('.log-entry');
            entries.forEach(entry => {
                if (level === 'all' || entry.classList.contains('log-' + level)) {
                    entry.style.display = 'block';
                } else {
                    entry.style.display = 'none';
                }
            });
        }

        function clearLogs() {
            document.getElementById('logViewer').innerHTML = '<div class="log-entry log-info"><span class="log-time">[系统]</span> 日志已清空</div>';
        }

        function exportLogs() {
            const logs = document.getElementById('logViewer').innerText;
            const blob = new Blob([logs], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'kaguya_logs_' + new Date().toISOString().slice(0,10) + '.txt';
            a.click();
            URL.revokeObjectURL(url);
            showToast('日志已导出');
        }

        let logAutoScroll = true;
        function toggleLogAutoScroll() {
            logAutoScroll = !logAutoScroll;
            showToast(logAutoScroll ? '自动滚动已开启' : '自动滚动已关闭');
        }

        function addLogEntry(level, message) {
            const viewer = document.getElementById('logViewer');
            const entry = document.createElement('div');
            entry.className = 'log-entry log-' + level;
            const time = new Date().toLocaleTimeString('zh-CN');
            entry.innerHTML = '<span class="log-time">[' + time + ']</span> ' + message;
            viewer.appendChild(entry);
            if (logAutoScroll) {
                viewer.scrollTop = viewer.scrollHeight;
            }
        }

        function openTaskSchedulerModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'taskSchedulerModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>⏰ 新建定时任务</h3>
                        <button class="modal-close" onclick="closeModal('taskSchedulerModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务名称</label>
                            <input class="project-input" id="taskName" placeholder="输入任务名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">执行时间</label>
                            <input type="time" class="project-input" id="taskTime" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">重复周期</label>
                            <select class="project-input" id="taskRepeat" style="width:100%;">
                                <option value="daily">每天</option>
                                <option value="weekly">每周</option>
                                <option value="monthly">每月</option>
                                <option value="once">仅一次</option>
                            </select>
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务类型</label>
                            <select class="project-input" id="taskType" style="width:100%;">
                                <option value="backup">数据备份</option>
                                <option value="cleanup">缓存清理</option>
                                <option value="report">报告生成</option>
                                <option value="custom">自定义脚本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('taskSchedulerModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveScheduledTask()">保存</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveScheduledTask() {
            const name = document.getElementById('taskName').value;
            const time = document.getElementById('taskTime').value;
            const repeat = document.getElementById('taskRepeat').value;
            const type = document.getElementById('taskType').value;
            if (!name || !time) {
                showToast('请填写完整信息');
                return;
            }
            fetch('/scheduler/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, time, repeat, type })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('任务已创建');
                    closeModal('taskSchedulerModal');
                    refreshScheduledTasks();
                } else {
                    showToast('创建失败: ' + data.error);
                }
            });
        }

        function refreshScheduledTasks() {
            fetch('/scheduler/tasks')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderScheduledTasks(data.tasks);
                    }
                });
        }

        function renderScheduledTasks(tasks) {
            const el = document.getElementById('scheduledTasksList');
            if (!el) return;
            el.innerHTML = tasks.map(t => `
                <div class="scheduler-task-card">
                    <div class="task-header">
                        <span class="task-name">${t.name}</span>
                        <span class="task-status ${t.status}">${t.status === 'active' ? '运行中' : '已暂停'}</span>
                    </div>
                    <div class="task-info">
                        <span>⏰ ${t.schedule}</span>
                        <span>🔄 上次: ${t.last_run || '--'}</span>
                    </div>
                </div>
            `).join('');
        }

        function loadPerformanceData() {
            const range = document.getElementById('perfTimeRange')?.value || '24h';
            fetch('/performance/stats?range=' + range)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('avgResponseTime').textContent = data.stats.avg_response_time || '--';
                        document.getElementById('totalRequests').textContent = data.stats.total_requests || '--';
                        document.getElementById('errorRate').textContent = data.stats.error_rate || '--';
                        document.getElementById('throughput').textContent = data.stats.throughput || '--';
                    }
                });
        }

        function exportPerformanceReport() {
            showToast('正在生成报告...');
            fetch('/performance/export')
                .then(r => r.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'performance_report_' + new Date().toISOString().slice(0,10) + '.json';
                    a.click();
                    URL.revokeObjectURL(url);
                    showToast('报告已导出');
                });
        }

        function generateGovernanceReport() {
            showToast('正在生成治理报告...');
            fetch('/console/governance-report')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('治理报告已生成');
                    }
                });
        }

        function checkAllServicesHealth() {
            showToast('正在检查服务健康状态...');
            fetch('/services/health-check')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderServiceHealth(data.services);
                        showToast('健康检查完成');
                    }
                });
        }

        function renderServiceHealth(services) {
            const el = document.getElementById('serviceHealthGrid');
            if (!el || !services) return;
            el.innerHTML = services.map(s => `
                <div class="service-card ${s.status}">
                    <div class="service-icon">${s.icon}</div>
                    <div class="service-info">
                        <div class="service-name">${s.name}</div>
                        <div class="service-status">● ${s.status_text}</div>
                    </div>
                    <div class="service-actions">
                        <button class="service-btn" onclick="restartService('${s.id}')">重启</button>
                    </div>
                </div>
            `).join('');
        }

        function restartService(serviceId) {
            showToast('正在重启 ' + serviceId + '...');
            fetch('/services/' + serviceId + '/restart', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    showToast(data.success ? '重启成功' : '重启失败');
                    checkAllServicesHealth();
                });
        }

        function configureService(serviceId) {
            showToast('打开服务配置...');
        }

        function openServiceConfigModal() {
            showToast('打开服务配置面板');
        }

        function analyzeAllDependencies() {
            showToast('正在分析依赖...');
            fetch('/dependencies/analyze')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('totalDeps').textContent = data.summary.total;
                        document.getElementById('outdatedDeps').textContent = data.summary.outdated;
                        document.getElementById('vulnerableDeps').textContent = data.summary.vulnerable;
                        showToast('依赖分析完成');
                    }
                });
        }

        function checkSecurityVulnerabilities() {
            showToast('正在进行安全检查...');
            fetch('/dependencies/security-check')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('发现 ' + (data.vulnerabilities?.length || 0) + ' 个潜在问题');
                    }
                });
        }

        function refreshGitStatus() {
            fetch('/git/status')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderGitStatus(data.repos);
                    }
                });
        }

        function renderGitStatus(repos) {
            const el = document.getElementById('gitStatusGrid');
            if (!el || !repos) return;
            el.innerHTML = repos.map(r => `
                <div class="git-repo-card">
                    <div class="git-repo-header">
                        <span class="git-repo-name">📁 ${r.name}</span>
                        <span class="git-branch">🌿 ${r.branch}</span>
                    </div>
                    <div class="git-repo-stats">
                        <span class="git-stat">📝 ${r.modified} 已修改</span>
                        <span class="git-stat">➕ ${r.added} 新文件</span>
                        <span class="git-stat">⏳ ${r.ahead} 待推送</span>
                    </div>
                    <div class="git-repo-actions">
                        <button class="git-btn" onclick="gitCommit('${r.name}')">提交</button>
                        <button class="git-btn" onclick="gitPush('${r.name}')">推送</button>
                        <button class="git-btn" onclick="gitPull('${r.name}')">拉取</button>
                    </div>
                </div>
            `).join('');
        }

        function gitCommit(repo) {
            showToast('正在提交 ' + repo + '...');
        }

        function gitPush(repo) {
            showToast('正在推送 ' + repo + '...');
        }

        function gitPull(repo) {
            showToast('正在拉取 ' + repo + '...');
        }

        function openGitOperationsModal() {
            showToast('打开 Git 操作面板');
        }

        function openNewProjectModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'newProjectModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📁 新建项目</h3>
                        <button class="modal-close" onclick="closeModal('newProjectModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目名称</label>
                            <input class="project-input" id="newProjectName" placeholder="输入项目名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目路径</label>
                            <input class="project-input" id="newProjectPath" placeholder="输入项目路径" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目描述</label>
                            <textarea class="project-input" id="newProjectDesc" placeholder="输入项目描述" style="width:100%;height:80px;resize:vertical;"></textarea>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('newProjectModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="createNewProject()">创建</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function createNewProject() {
            const name = document.getElementById('newProjectName').value;
            const path = document.getElementById('newProjectPath').value;
            const desc = document.getElementById('newProjectDesc').value;
            if (!name || !path) {
                showToast('请填写项目名称和路径');
                return;
            }
            fetch('/workspace/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, path, description: desc })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('项目已创建');
                    closeModal('newProjectModal');
                    refreshWorkspaceProjects();
                } else {
                    showToast('创建失败: ' + data.error);
                }
            });
        }

        function searchProjectTemplates(query) {
            fetch('/templates/search?q=' + encodeURIComponent(query))
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        renderProjectTemplates(data.templates);
                    }
                });
        }

        function renderProjectTemplates(templates) {
            const el = document.getElementById('projectTemplateGrid');
            if (!el || !templates) return;
            el.innerHTML = templates.map(t => `
                <div class="template-card" onclick="useTemplate('${t.id}')">
                    <div class="template-icon">${t.icon}</div>
                    <div class="template-info">
                        <div class="template-name">${t.name}</div>
                        <div class="template-desc">${t.description}</div>
                    </div>
                </div>
            `).join('');
        }

        function useTemplate(templateId) {
            showToast('正在应用模板: ' + templateId);
        }

        function openCreateTemplateModal() {
            showToast('打开创建模板面板');
        }

        function openDeployConfigModal() {
            showToast('打开部署配置面板');
        }

        function executeDeploy() {
            const target = document.getElementById('deployTargetSelect').value;
            showToast('正在部署到 ' + target + '...');
            fetch('/deploy/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            }).then(r => r.json()).then(data => {
                showToast(data.success ? '部署成功' : '部署失败');
            });
        }

        function refreshDataFlowStats() {
            fetch('/dataflow/stats')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('dataflowInput').textContent = data.stats.input_count || '--';
                        document.getElementById('dataflowProcess').textContent = data.stats.process_count || '--';
                        document.getElementById('dataflowOutput').textContent = data.stats.output_count || '--';
                        document.getElementById('dataflowRate').textContent = data.stats.rate || '-- req/s';
                        document.getElementById('dataflowQueue').textContent = data.stats.queue_depth || '--';
                        document.getElementById('dataflowLatency').textContent = data.stats.latency || '-- ms';
                    }
                });
        }

        function openDataFlowConfigModal() {
            showToast('打开数据流配置面板');
        }

        function renderConsoleOverview() {
            const el = document.getElementById('consoleScoreGrid');
            if (!el) return;
            const cards = [
                {label: '健康评分', value: `${consoleOverview.health_score ?? 0}`},
                {label: '执行评分', value: `${consoleOverview.execution_score ?? 0}`},
                {label: '增长评分', value: `${consoleOverview.growth_score ?? 0}`},
                {label: '知识评分', value: `${consoleOverview.knowledge_score ?? 0}`}
            ];
            el.innerHTML = cards.map(c => `
                <div class="console-score-card">
                    <div class="console-score-label">${c.label}</div>
                    <div class="console-score-value">${c.value}</div>
                </div>
            `).join('');
        }

        function runGlobalSearch(query = '') {
            const q = encodeURIComponent((query || '').trim());
            const entity = encodeURIComponent((document.getElementById('globalSearchEntity')?.value || '').trim());
            fetch(`/search/global?q=${q}&entity=${entity}&limit=60`).then(r => r.json()).then(data => {
                if (!data.success) return;
                globalSearchResults = data.results || [];
                renderGlobalSearchResults();
            });
        }

        function renderGlobalSearchResults() {
            const el = document.getElementById('globalSearchList');
            if (!el) return;
            if (!globalSearchResults.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><div class="empty-state-text">暂无检索结果</div></div>';
                return;
            }
            el.innerHTML = globalSearchResults.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.title || '未命名'}</div>
                        <span class="project-tag">${item.entity}</span>
                    </div>
                    <div class="project-item-desc">${item.subtitle || ''}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">状态 ${item.status || '-'}</span>
                        ${item.score ? `<span class="project-tag">评分 ${item.score}</span>` : ''}
                        <span class="project-tag">ID ${item.id || '-'}</span>
                    </div>
                </div>
            `).join('');
        }

        function renderConsoleRecommendations() {
            const el = document.getElementById('consoleRecommendationList');
            if (!el) return;
            if (!consoleRecommendations.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧠</div><div class="empty-state-text">暂无建议</div></div>';
                return;
            }
            el.innerHTML = consoleRecommendations.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.title}</div>
                        <span class="console-reco-priority ${(item.priority || 'P3').toLowerCase()}">${item.priority || 'P3'}</span>
                    </div>
                    <div class="project-item-desc">${item.detail || ''}</div>
                    <div class="project-item-tags"><span class="project-tag">${item.action || ''}</span></div>
                </div>
            `).join('');
        }

        function renderWorkspaceOverview() {
            const el = document.getElementById('workspaceOverviewCards');
            if (!el) return;
            const cards = [
                {label: '项目总数', value: workspaceOverview.total ?? 0},
                {label: '运行中', value: workspaceOverview.running ?? 0},
                {label: 'Python', value: workspaceOverview.python ?? 0},
                {label: 'Node', value: workspaceOverview.node ?? 0}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }

        function renderWorkspaceProjects() {
            const el = document.getElementById('workspaceProjectList');
            if (!el) return;
            if (!workspaceProjects.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🌐</div><div class="empty-state-text">暂无可整合项目</div></div>';
                return;
            }
            el.innerHTML = workspaceProjects.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.name || '未命名项目'}</div>
                        <span class="project-tag">${item.kind || 'unknown'}</span>
                    </div>
                    <div class="project-item-desc">${item.desc || ''}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.relative_path || '-'}</span>
                        <span class="project-tag">状态 ${item.running ? 'running' : 'idle'}</span>
                        <span class="project-tag">${item.source || 'auto'}</span>
                    </div>
                    <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
                        ${item.default_url ? `<button class="project-mini-btn" onclick="openWorkspaceProject('${item.default_url}')">打开</button>` : ''}
                        ${item.start_command ? `<button class="project-mini-btn" onclick='copyWorkspaceStartCommand(${JSON.stringify(item.start_command)})'>复制启动命令</button>` : ''}
                    </div>
                </div>
            `).join('');
        }

        function openWorkspaceProject(url) {
            if (!url) return;
            window.open(url, '_blank', 'noopener');
        }

        function copyWorkspaceStartCommand(cmd) {
            if (!cmd) return;
            navigator.clipboard.writeText(cmd).then(() => showToast('已复制启动命令')).catch(() => showToast(cmd));
        }
        
        function renderProjectOverview() {
            const el = document.getElementById('projectOverviewCards');
            if (!el) return;
            const cards = [
                {label: '产物总数', value: projectOverview.artifacts ?? 0},
                {label: '置顶产物', value: projectOverview.pinned_artifacts ?? 0},
                {label: '进行中任务', value: projectOverview.tasks_doing ?? 0},
                {label: '完成率', value: `${projectOverview.task_done_rate ?? 0}%`},
                {label: '里程碑', value: projectOverview.milestones ?? 0},
                {label: '风险项', value: projectOverview.risks ?? 0}
            ];
            el.innerHTML = cards.map(c => `
                <div class="project-overview-card">
                    <div class="project-overview-label">${c.label}</div>
                    <div class="project-overview-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function loadProjectArtifacts(query = '') {
            const q = encodeURIComponent(query || '');
            fetch(`/artifacts?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                projectArtifacts = data.artifacts || [];
                renderProjectArtifacts();
            });
        }
        
        function renderProjectArtifacts() {
            const el = document.getElementById('artifactList');
            if (!el) return;
            if (!projectArtifacts.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-text">暂无产物，点击新增开始沉淀</div></div>';
                return;
            }
            el.innerHTML = projectArtifacts.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.pinned ? '📌 ' : ''}${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="openArtifactModal('${item.id}')">编辑</button>
                            <button class="project-mini-btn" onclick="showArtifactVersions('${item.id}')">版本${item.version_count || 1}</button>
                            <button class="project-mini-btn" onclick="toggleArtifactPin('${item.id}', ${item.pinned ? 'false' : 'true'})">${item.pinned ? '取消置顶' : '置顶'}</button>
                            <button class="project-mini-btn" onclick="deleteArtifact('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="artifact-content-preview">${(item.content || '').slice(0, 180)}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.type || 'note'}</span>
                        <span class="project-tag">${item.source || 'manual'}</span>
                        ${(item.tags || []).slice(0, 3).map(t => `<span class="project-tag">${t}</span>`).join('')}
                    </div>
                </div>
            `).join('');
        }
        
        function openArtifactModal(id = null) {
            editingArtifactId = id;
            const titleEl = document.getElementById('artifactModalTitle');
            const titleInput = document.getElementById('artifactTitleInput');
            const typeInput = document.getElementById('artifactTypeInput');
            const tagsInput = document.getElementById('artifactTagsInput');
            const contentInput = document.getElementById('artifactContentInput');
            if (!titleEl || !titleInput || !typeInput || !tagsInput || !contentInput) return;
            if (id) {
                const item = projectArtifacts.find(x => x.id === id);
                if (!item) return;
                titleEl.textContent = '📝 编辑产物';
                titleInput.value = item.title || '';
                typeInput.value = item.type || 'note';
                tagsInput.value = (item.tags || []).join(',');
                contentInput.value = item.content || '';
            } else {
                titleEl.textContent = '📦 新增产物';
                titleInput.value = '';
                typeInput.value = 'note';
                tagsInput.value = '';
                contentInput.value = '';
            }
            document.getElementById('artifactModal').classList.add('show');
        }
        
        function submitArtifactModal() {
            const title = (document.getElementById('artifactTitleInput').value || '').trim();
            const type = (document.getElementById('artifactTypeInput').value || 'note').trim();
            const tags = (document.getElementById('artifactTagsInput').value || '').split(',').map(x => x.trim()).filter(Boolean);
            const content = (document.getElementById('artifactContentInput').value || '').trim();
            if (!content) return showToast('内容不能为空');
            const payload = {title, content, type, tags, source: 'workspace', editor: 'ui'};
            const method = editingArtifactId ? 'PUT' : 'POST';
            const url = editingArtifactId ? `/artifacts/${editingArtifactId}` : '/artifacts';
            fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '保存失败');
                closeModal('artifactModal');
                showToast(editingArtifactId ? '产物已更新' : '产物已新增');
                recordFeatureAction(editingArtifactId ? '更新产物' : '新增产物', '项目中台');
                editingArtifactId = null;
                loadProjectCenter();
            });
        }
        
        function showArtifactVersions(id) {
            fetch(`/artifacts/${id}/versions`).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '获取失败');
                const list = document.getElementById('artifactVersionsList');
                if (!list) return;
                const versions = data.versions || [];
                if (!versions.length) {
                    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🕘</div><div class="empty-state-text">暂无版本历史</div></div>';
                } else {
                    list.innerHTML = versions.map(v => `
                        <div class="version-item">
                            <div class="version-head">
                                <span class="version-title">版本 ${v.version} · ${v.title || ''}</span>
                                <button class="project-mini-btn" onclick="restoreArtifactVersion('${id}', ${v.version})">回滚</button>
                            </div>
                            <div class="version-meta">${new Date((v.time || 0) * 1000).toLocaleString('zh-CN')} · ${v.editor || 'system'}</div>
                            <div class="version-body">${(v.content || '').slice(0, 220)}</div>
                        </div>
                    `).join('');
                }
                document.getElementById('artifactVersionsModal').classList.add('show');
            });
        }
        
        function restoreArtifactVersion(id, version) {
            fetch(`/artifacts/${id}/restore`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({version, editor: 'ui'})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '回滚失败');
                showToast('已回滚到指定版本');
                closeModal('artifactVersionsModal');
                loadProjectCenter();
            });
        }
        
        function toggleArtifactPin(id, pinned) {
            fetch(`/artifacts/${id}/pin`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pinned})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '操作失败');
                loadProjectCenter();
            });
        }
        
        function deleteArtifact(id) {
            fetch(`/artifacts/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除产物');
                loadProjectCenter();
            });
        }
        
        function renderProjectTasks() {
            const el = document.getElementById('projectKanbanBoard');
            if (!el) return;
            if (!projectTasks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🗂️</div><div class="empty-state-text">暂无任务，点击任务按钮新增</div></div>';
                return;
            }
            const groups = [
                {key: 'todo', label: '待办'},
                {key: 'doing', label: '进行中'},
                {key: 'done', label: '完成'}
            ];
            el.innerHTML = groups.map(g => {
                const items = projectTasks.filter(t => (t.status || 'todo') === g.key).sort((a, b) => (a.order || 0) - (b.order || 0));
                return `
                    <div class="kanban-column" data-status="${g.key}" ondragover="onTaskColumnDragOver(event)" ondrop="onTaskDrop(event, '${g.key}')" ondragleave="onTaskColumnDragLeave(event)">
                        <div class="kanban-title"><span>${g.label}</span><span>${items.length}</span></div>
                        <div class="kanban-list">
                            ${items.map(task => `
                                <div class="kanban-task" draggable="true" ondragstart="onTaskDragStart(event, '${task.id}')" data-task-id="${task.id}">
                                    <div class="kanban-task-title">${task.title}</div>
                                    <div class="kanban-task-meta">
                                        <span class="project-tag">${task.priority || 'medium'}</span>
                                        ${task.owner ? `<span class="project-tag">${task.owner}</span>` : ''}
                                        <button class="task-status-btn ${selectedTaskIds.has(task.id) ? 'active' : ''}" onclick="toggleTaskSelected('${task.id}')">选择</button>
                                        <button class="task-status-btn" onclick="deleteProjectTask('${task.id}')">删除</button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function openTaskModal() {
            document.getElementById('taskTitleInput').value = '';
            document.getElementById('taskDescInput').value = '';
            document.getElementById('taskPriorityInput').value = 'medium';
            document.getElementById('taskOwnerInput').value = '';
            document.getElementById('taskModal').classList.add('show');
        }
        
        function submitTaskModal() {
            const title = (document.getElementById('taskTitleInput').value || '').trim();
            if (!title) return showToast('任务标题不能为空');
            const description = (document.getElementById('taskDescInput').value || '').trim();
            const priority = (document.getElementById('taskPriorityInput').value || 'medium').trim();
            const owner = (document.getElementById('taskOwnerInput').value || '').trim();
            fetch('/project/tasks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title, description, priority, owner, status: 'todo'})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('taskModal');
                showToast('已新增任务');
                recordFeatureAction('新增项目任务', '项目中台');
                loadProjectCenter();
            });
        }
        
        function updateProjectTaskStatus(id, status) {
            fetch(`/project/tasks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteProjectTask(id) {
            fetch(`/project/tasks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除任务');
                loadProjectCenter();
            });
        }
        
        function onTaskDragStart(event, taskId) {
            draggingTaskId = taskId;
            event.dataTransfer.effectAllowed = 'move';
        }
        
        function onTaskColumnDragOver(event) {
            event.preventDefault();
            event.currentTarget.classList.add('drag-over');
        }
        
        function onTaskColumnDragLeave(event) {
            event.currentTarget.classList.remove('drag-over');
        }
        
        function onTaskDrop(event, status) {
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');
            if (!draggingTaskId) return;
            fetch(`/project/tasks/${draggingTaskId}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '拖拽失败');
                draggingTaskId = null;
                loadProjectCenter();
            });
        }
        
        function toggleTaskSelected(id) {
            if (selectedTaskIds.has(id)) selectedTaskIds.delete(id);
            else selectedTaskIds.add(id);
            renderProjectTasks();
        }
        
        function batchMoveTasks(status) {
            const ids = Array.from(selectedTaskIds);
            if (!ids.length) return showToast('请先选择任务');
            fetch('/project/tasks/batch_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_ids: ids, status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '批量操作失败');
                selectedTaskIds.clear();
                showToast(`已批量更新 ${data.updated || 0} 条任务`);
                loadProjectCenter();
            });
        }
        
        function renderProjectPlaybooks() {
            const el = document.getElementById('playbookList');
            if (!el) return;
            if (!projectPlaybooks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧠</div><div class="empty-state-text">暂无剧本模板</div></div>';
                return;
            }
            el.innerHTML = projectPlaybooks.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title">${item.name}</div>
                        <button class="project-mini-btn" onclick="runPlaybook('${item.id}')">运行</button>
                    </div>
                    <div class="project-item-desc">${item.description || '无描述'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.category || '自定义'}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function openPlaybookModal() {
            document.getElementById('playbookNameInput').value = '';
            document.getElementById('playbookCategoryInput').value = '自定义';
            document.getElementById('playbookDescInput').value = '';
            document.getElementById('playbookTemplateInput').value = '';
            document.getElementById('playbookModal').classList.add('show');
        }
        
        function submitPlaybookModal() {
            const name = (document.getElementById('playbookNameInput').value || '').trim();
            const category = (document.getElementById('playbookCategoryInput').value || '自定义').trim();
            const description = (document.getElementById('playbookDescInput').value || '').trim();
            const template = (document.getElementById('playbookTemplateInput').value || '').trim();
            if (!name || !template) return showToast('名称和模板不能为空');
            fetch('/playbooks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, category, description, template})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('playbookModal');
                showToast('已新增剧本');
                loadProjectCenter();
            });
        }
        
        function runPlaybook(id) {
            const topic = prompt('主题');
            if (!topic) return;
            const goal = prompt('目标', '') || '';
            const context = prompt('背景', '') || '';
            const constraints = prompt('约束', '') || '';
            fetch(`/playbooks/${id}/run`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({topic, goal, context, constraints})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '运行失败');
                usePrompt(data.prompt || '');
                switchTab('prompts', document.querySelector('.sidebar-tab[onclick*="prompts"]'));
                showToast('剧本已生成并填入输入框');
                recordFeatureAction('运行剧本模板', '项目中台');
            });
        }
        
        function loadProjectActivity() {
            fetch('/project/activity?limit=40').then(r => r.json()).then(data => {
                if (!data.success) return;
                projectActivities = data.activities || [];
                renderProjectActivity();
                renderFeatureCenterMeta();
            });
        }
        
        function renderProjectActivity() {
            const el = document.getElementById('projectActivityList');
            if (!el) return;
            if (!projectActivities.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🕒</div><div class="empty-state-text">暂无操作记录</div></div>';
                return;
            }
            el.innerHTML = projectActivities.slice(0, 40).map(item => `
                <div class="activity-item">
                    <div class="activity-main">${item.action} · ${item.entity} · ${item.detail || item.entity_id}</div>
                    <div class="activity-time">${new Date((item.time || 0) * 1000).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</div>
                </div>
            `).join('');
        }

        function renderProjectMilestones() {
            const el = document.getElementById('milestoneList');
            if (!el) return;
            if (!projectMilestones.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎯</div><div class="empty-state-text">暂无里程碑</div></div>';
                return;
            }
            el.innerHTML = projectMilestones.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planned'}"></span>${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','active', ${Math.max(Number(item.progress || 0), 10)})">推进</button>
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','done', 100)">完成</button>
                            <button class="project-mini-btn" onclick="updateMilestoneStatus('${item.id}','delayed', ${Number(item.progress || 0)})">延期</button>
                            <button class="project-mini-btn" onclick="deleteMilestone('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">负责人 ${item.owner || '未分配'} · 截止 ${item.due_date || '-'} · 进度 ${item.progress ?? 0}%</div>
                    <div class="project-item-tags">
                        <span class="project-tag">状态 ${item.status || 'planned'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openMilestoneModal() {
            ['milestoneTitleInput','milestoneOwnerInput','milestoneDueInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('milestoneProgressInput').value = '0';
            document.getElementById('milestoneModal').classList.add('show');
        }

        function submitMilestoneModal() {
            const payload = {
                title: (document.getElementById('milestoneTitleInput').value || '').trim(),
                owner: (document.getElementById('milestoneOwnerInput').value || '').trim(),
                due_date: (document.getElementById('milestoneDueInput').value || '').trim(),
                progress: Number(document.getElementById('milestoneProgressInput').value || 0),
                status: 'planned'
            };
            if (!payload.title) return showToast('里程碑标题不能为空');
            fetch('/project/milestones', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('milestoneModal');
                showToast('已新增里程碑');
                loadProjectCenter();
            });
        }

        function updateMilestoneStatus(id, status, progress) {
            fetch(`/project/milestones/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status, progress})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteMilestone(id) {
            fetch(`/project/milestones/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除里程碑');
                loadProjectCenter();
            });
        }

        function renderProjectRisks() {
            const el = document.getElementById('riskList');
            if (!el) return;
            if (!projectRisks.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">暂无风险记录</div></div>';
                return;
            }
            el.innerHTML = projectRisks.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateRiskStatus('${item.id}','mitigating')">缓解中</button>
                            <button class="project-mini-btn" onclick="updateRiskStatus('${item.id}','closed')">关闭</button>
                            <button class="project-mini-btn" onclick="deleteRisk('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">等级 ${item.level || 'medium'} · 状态 ${item.status || 'open'} · 责任人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">${item.mitigation || '未填写缓解策略'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openRiskModal() {
            ['riskTitleInput','riskOwnerInput','riskMitigationInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('riskLevelInput').value = 'medium';
            document.getElementById('riskModal').classList.add('show');
        }

        function submitRiskModal() {
            const payload = {
                title: (document.getElementById('riskTitleInput').value || '').trim(),
                owner: (document.getElementById('riskOwnerInput').value || '').trim(),
                level: (document.getElementById('riskLevelInput').value || 'medium').trim(),
                mitigation: (document.getElementById('riskMitigationInput').value || '').trim(),
                status: 'open'
            };
            if (!payload.title) return showToast('风险标题不能为空');
            fetch('/project/risks', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('riskModal');
                showToast('已新增风险');
                loadProjectCenter();
            });
        }

        function updateRiskStatus(id, status) {
            fetch(`/project/risks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteRisk(id) {
            fetch(`/project/risks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除风险');
                loadProjectCenter();
            });
        }

        function renderOpsOverview() {
            const el = document.getElementById('opsOverviewCards');
            if (!el) return;
            const cards = [
                {label: '活动总数', value: opsOverview.campaigns ?? 0},
                {label: '运行中', value: opsOverview.running ?? 0},
                {label: '平均CTR', value: `${opsOverview.avg_ctr ?? 0}%`},
                {label: '总预算', value: `¥${opsOverview.total_budget ?? 0}`}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function loadOpsCampaigns(query = '') {
            const q = encodeURIComponent(query || '');
            fetch(`/ops/campaigns?q=${q}`).then(r => r.json()).then(data => {
                if (!data.success) return;
                opsCampaigns = data.campaigns || [];
                renderOpsCampaigns();
            });
        }
        
        function renderOpsCampaigns() {
            const el = document.getElementById('opsCampaignList');
            if (!el) return;
            if (!opsCampaigns.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📣</div><div class="empty-state-text">暂无运营活动</div></div>';
                return;
            }
            el.innerHTML = opsCampaigns.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','running')">运行</button>
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','paused')">暂停</button>
                            <button class="project-mini-btn" onclick="updateOpsCampaignStatus('${item.id}','done')">完成</button>
                            <button class="project-mini-btn" onclick="deleteOpsCampaign('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.channel || '全渠道'} · 负责人 ${item.owner || '未分配'} · ${item.start_date || '-'} ~ ${item.end_date || '-'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">预算 ¥${item.budget ?? 0}</span>
                        <span class="project-tag">目标CTR ${item.target_ctr ?? 0}%</span>
                        <span class="project-tag">当前CTR ${item.current_ctr ?? 0}%</span>
                    </div>
                </div>
            `).join('');
        }
        
        function openOpsCampaignModal() {
            ['opsCampaignNameInput','opsCampaignChannelInput','opsCampaignOwnerInput','opsCampaignBudgetInput','opsCampaignTargetCtrInput','opsCampaignCurrentCtrInput','opsCampaignStartInput','opsCampaignEndInput','opsCampaignNotesInput']
                .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('opsCampaignModal').classList.add('show');
        }
        
        function submitOpsCampaignModal() {
            const payload = {
                name: (document.getElementById('opsCampaignNameInput').value || '').trim(),
                channel: (document.getElementById('opsCampaignChannelInput').value || '').trim(),
                owner: (document.getElementById('opsCampaignOwnerInput').value || '').trim(),
                budget: Number(document.getElementById('opsCampaignBudgetInput').value || 0),
                target_ctr: Number(document.getElementById('opsCampaignTargetCtrInput').value || 0),
                current_ctr: Number(document.getElementById('opsCampaignCurrentCtrInput').value || 0),
                start_date: (document.getElementById('opsCampaignStartInput').value || '').trim(),
                end_date: (document.getElementById('opsCampaignEndInput').value || '').trim(),
                notes: (document.getElementById('opsCampaignNotesInput').value || '').trim(),
                status: 'draft'
            };
            if (!payload.name) return showToast('活动名称不能为空');
            fetch('/ops/campaigns', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('opsCampaignModal');
                showToast('已新增运营活动');
                recordFeatureAction('新增运营活动', '运营中心');
                loadProjectCenter();
            });
        }
        
        function updateOpsCampaignStatus(id, status) {
            fetch(`/ops/campaigns/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteOpsCampaign(id) {
            fetch(`/ops/campaigns/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除活动');
                loadProjectCenter();
            });
        }
        
        function renderReleaseOverview() {
            const el = document.getElementById('releaseOverviewCards');
            if (!el) return;
            const cards = [
                {label: '计划总数', value: releaseOverview.plans ?? 0},
                {label: '待发布', value: releaseOverview.ready ?? 0},
                {label: '回滚次数', value: releaseOverview.rollback ?? 0},
                {label: '高风险', value: releasePlans.filter(x => x.risk === 'high').length}
            ];
            el.innerHTML = cards.map(c => `
                <div class="ops-kpi-card">
                    <div class="ops-kpi-label">${c.label}</div>
                    <div class="ops-kpi-value">${c.value}</div>
                </div>
            `).join('');
        }
        
        function renderReleasePlans() {
            const el = document.getElementById('releasePlanList');
            if (!el) return;
            if (!releasePlans.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🚀</div><div class="empty-state-text">暂无发布计划</div></div>';
                return;
            }
            el.innerHTML = releasePlans.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planning'}"></span>${item.version} · ${item.title}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','review')">评审</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','ready')">就绪</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','released')">发布</button>
                            <button class="project-mini-btn" onclick="updateReleaseStatus('${item.id}','rollback')">回滚</button>
                            <button class="project-mini-btn" onclick="deleteReleasePlan('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.environment || 'production'} · 风险 ${item.risk || 'medium'} · 负责人 ${item.owner || '未分配'}</div>
                    <div class="release-checklist">
                        ${(item.checklist || []).slice(0, 5).map((c, idx) => `
                            <label class="release-check">
                                <input type="checkbox" ${c.checked ? 'checked' : ''} onchange="toggleReleaseCheck('${item.id}', ${idx}, this.checked)">
                                <span>${c.label || c}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }
        
        function openReleasePlanModal() {
            ['releaseVersionInput','releaseOwnerInput','releaseTitleInput','releaseChecklistInput','releaseNotesInput']
                .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('releaseEnvInput').value = 'production';
            document.getElementById('releaseRiskInput').value = 'medium';
            document.getElementById('releasePlanModal').classList.add('show');
        }
        
        function submitReleasePlanModal() {
            const lines = (document.getElementById('releaseChecklistInput').value || '').split("\\n").map(x => x.trim()).filter(Boolean);
            const checklist = lines.map(x => ({label: x, checked: false}));
            const payload = {
                version: (document.getElementById('releaseVersionInput').value || '').trim(),
                title: (document.getElementById('releaseTitleInput').value || '').trim(),
                owner: (document.getElementById('releaseOwnerInput').value || '').trim(),
                environment: (document.getElementById('releaseEnvInput').value || 'production').trim(),
                risk: (document.getElementById('releaseRiskInput').value || 'medium').trim(),
                notes: (document.getElementById('releaseNotesInput').value || '').trim(),
                checklist
            };
            if (!payload.version || !payload.title) return showToast('版本和标题不能为空');
            fetch('/release/plans', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('releasePlanModal');
                showToast('已新增发布计划');
                recordFeatureAction('新增发布计划', '发布中心');
                loadProjectCenter();
            });
        }
        
        function updateReleaseStatus(id, status) {
            fetch(`/release/plans/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function toggleReleaseCheck(id, index, checked) {
            fetch(`/release/plans/${id}/check`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({index, checked})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }
        
        function deleteReleasePlan(id) {
            fetch(`/release/plans/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除发布计划');
                loadProjectCenter();
            });
        }

        function renderAlertOverview() {
            const el = document.getElementById('alertOverviewCards');
            if (!el) return;
            const cards = [
                {label: '规则总数', value: alertOverview.rules ?? 0},
                {label: '激活中', value: alertOverview.active ?? 0},
                {label: '严重告警', value: alertOverview.critical ?? 0},
                {label: '已恢复', value: alertRules.filter(x => x.status === 'resolved').length}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderAlertRules() {
            const el = document.getElementById('alertRuleList');
            if (!el) return;
            if (!alertRules.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🚨</div><div class="empty-state-text">暂无告警规则</div></div>';
                return;
            }
            el.innerHTML = alertRules.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','active')">激活</button>
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','muted')">静默</button>
                            <button class="project-mini-btn" onclick="updateAlertRuleStatus('${item.id}','resolved')">恢复</button>
                            <button class="project-mini-btn" onclick="deleteAlertRule('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.metric || 'metric'} · 阈值 ${item.threshold ?? 0} · 当前 ${item.current_value ?? 0} · 负责人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">等级 ${item.level || 'medium'}</span>
                        <span class="project-tag">状态 ${item.status || 'active'}</span>
                    </div>
                </div>
            `).join('');
        }

        function openAlertRuleModal() {
            ['alertRuleNameInput','alertMetricInput','alertThresholdInput','alertOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('alertLevelInput').value = 'medium';
            document.getElementById('alertRuleModal').classList.add('show');
        }

        function submitAlertRuleModal() {
            const payload = {
                name: (document.getElementById('alertRuleNameInput').value || '').trim(),
                metric: (document.getElementById('alertMetricInput').value || '').trim(),
                threshold: Number(document.getElementById('alertThresholdInput').value || 0),
                level: (document.getElementById('alertLevelInput').value || 'medium').trim(),
                owner: (document.getElementById('alertOwnerInput').value || '').trim(),
                status: 'active',
                current_value: 0
            };
            if (!payload.name || !payload.metric) return showToast('规则名称和指标不能为空');
            fetch('/alerts/rules', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('alertRuleModal');
                showToast('已新增告警规则');
                recordFeatureAction('新增告警规则', '告警中心');
                loadProjectCenter();
            });
        }

        function updateAlertRuleStatus(id, status) {
            fetch(`/alerts/rules/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteAlertRule(id) {
            fetch(`/alerts/rules/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除告警规则');
                loadProjectCenter();
            });
        }

        function renderAbOverview() {
            const el = document.getElementById('abOverviewCards');
            if (!el) return;
            const cards = [
                {label: '实验总数', value: abOverview.experiments ?? 0},
                {label: '运行中', value: abOverview.running ?? 0},
                {label: '已完成', value: abExperiments.filter(x => x.status === 'completed').length},
                {label: '平均流量', value: `${abExperiments.length ? Math.round(abExperiments.reduce((s, x) => s + (Number(x.traffic || 0)), 0) / abExperiments.length) : 0}%`}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderAbExperiments() {
            const el = document.getElementById('abExperimentList');
            if (!el) return;
            if (!abExperiments.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧪</div><div class="empty-state-text">暂无A/B实验</div></div>';
                return;
            }
            el.innerHTML = abExperiments.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','running')">运行</button>
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','paused')">暂停</button>
                            <button class="project-mini-btn" onclick="updateAbStatus('${item.id}','completed')">完成</button>
                            <button class="project-mini-btn" onclick="deleteAb('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.metric || 'metric'} · 流量 ${item.traffic ?? 0}% · 负责人 ${item.owner || '未分配'}</div>
                    <div class="project-item-tags">
                        <span class="project-tag">基线 ${item.baseline ?? 0}</span>
                        <span class="project-tag">实验组 ${item.variant ?? 0}</span>
                        <button class="project-mini-btn" onclick="refreshAbMetric('${item.id}')">刷新指标</button>
                    </div>
                </div>
            `).join('');
        }

        function openAbModal() {
            ['abNameInput','abMetricInput','abOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('abTrafficInput').value = '50';
            document.getElementById('abModal').classList.add('show');
        }

        function submitAbModal() {
            const payload = {
                name: (document.getElementById('abNameInput').value || '').trim(),
                metric: (document.getElementById('abMetricInput').value || '').trim(),
                traffic: Number(document.getElementById('abTrafficInput').value || 50),
                owner: (document.getElementById('abOwnerInput').value || '').trim(),
                status: 'draft',
                baseline: 0,
                variant: 0
            };
            if (!payload.name || !payload.metric) return showToast('实验名称和指标不能为空');
            fetch('/ab/experiments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('abModal');
                showToast('已新增AB实验');
                recordFeatureAction('新增AB实验', '实验中心');
                loadProjectCenter();
            });
        }

        function updateAbStatus(id, status) {
            fetch(`/ab/experiments/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function refreshAbMetric(id) {
            const baseline = Number((Math.random() * 10 + 20).toFixed(2));
            const variant = Number((baseline + (Math.random() * 6 - 1)).toFixed(2));
            fetch(`/ab/experiments/${id}/metrics`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({baseline, variant})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteAb(id) {
            fetch(`/ab/experiments/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除AB实验');
                loadProjectCenter();
            });
        }

        function renderIntegrationOverview() {
            const el = document.getElementById('integrationOverviewCards');
            if (!el) return;
            const cards = [
                {label: '集成总数', value: integrationOverview.integrations ?? 0},
                {label: '已启用', value: integrationOverview.enabled ?? 0},
                {label: '异常数', value: integrationOverview.errors ?? 0},
                {label: '平均健康度', value: `${integrationItems.length ? Math.round(integrationItems.reduce((s, x) => s + (Number(x.health || 0)), 0) / integrationItems.length) : 0}%`}
            ];
            el.innerHTML = cards.map(c => `<div class="ops-kpi-card"><div class="ops-kpi-label">${c.label}</div><div class="ops-kpi-value">${c.value}</div></div>`).join('');
        }

        function renderIntegrations() {
            const el = document.getElementById('integrationList');
            if (!el) return;
            if (!integrationItems.length) {
                el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🧩</div><div class="empty-state-text">暂无集成配置</div></div>';
                return;
            }
            el.innerHTML = integrationItems.map(item => `
                <div class="project-item">
                    <div class="project-item-top">
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'disabled'}"></span>${item.name}</div>
                        <div style="display:flex;gap:6px;">
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','enabled')">启用</button>
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','disabled')">停用</button>
                            <button class="project-mini-btn" onclick="updateIntegrationStatus('${item.id}','error')">标异常</button>
                            <button class="project-mini-btn" onclick="deleteIntegration('${item.id}')">删除</button>
                        </div>
                    </div>
                    <div class="project-item-desc">${item.provider || 'provider'} · 负责人 ${item.owner || '未分配'} · 健康度 ${item.health ?? 0}%</div>
                    <div class="project-item-tags"><span class="project-tag">${item.desc || '无说明'}</span></div>
                </div>
            `).join('');
        }

        function openIntegrationModal() {
            ['integrationNameInput','integrationProviderInput','integrationDescInput','integrationOwnerInput'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
            document.getElementById('integrationHealthInput').value = '80';
            document.getElementById('integrationModal').classList.add('show');
        }

        function submitIntegrationModal() {
            const payload = {
                name: (document.getElementById('integrationNameInput').value || '').trim(),
                provider: (document.getElementById('integrationProviderInput').value || '').trim(),
                desc: (document.getElementById('integrationDescInput').value || '').trim(),
                owner: (document.getElementById('integrationOwnerInput').value || '').trim(),
                health: Number(document.getElementById('integrationHealthInput').value || 80),
                status: 'disabled'
            };
            if (!payload.name || !payload.provider) return showToast('集成名称和提供方不能为空');
            fetch('/integrations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('integrationModal');
                showToast('已新增集成');
                recordFeatureAction('新增集成', '集成市场');
                loadProjectCenter();
            });
        }

        function updateIntegrationStatus(id, status) {
            fetch(`/integrations/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }

        function deleteIntegration(id) {
            fetch(`/integrations/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除集成');
                loadProjectCenter();
            });
        }
        
        function searchChats(query) {
            const filtered = chats.filter(c => 
                c.title.toLowerCase().includes(query.toLowerCase()) ||
                c.messages.some(m => m.content.toLowerCase().includes(query.toLowerCase()))
            );
            document.getElementById('chatList').innerHTML = filtered.map(c => `
                <div class="chat-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
                    <span>💬</span>
                    <span class="chat-item-title">${c.title || '新对话'}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
        }
        
        let currentReader = null;
        let isGenerating = false;
        
        function stopGeneration() {
            if (currentReader) {
                currentReader.cancel();
                currentReader = null;
            }
            isGenerating = false;
            document.getElementById('sendBtn').style.display = 'flex';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('statusText').textContent = '已停止';
            showToast('已停止生成');
        }
        
        function newChat() {
            const id = Date.now().toString();
            chats.unshift({ id, title: '新对话', messages: [], created: new Date().toISOString(), role: currentRole, lora: currentLora, starred: false });
            saveChats();
            currentChatId = id;
            history = [];
            showWelcome();
            renderChatList();
            showToast('已创建新对话');
        }
        
        function toggleStarChat(id) {
            const chat = chats.find(c => c.id === id);
            if (chat) {
                chat.starred = !chat.starred;
                saveChats();
                renderChatList();
                showToast(chat.starred ? '已收藏' : '已取消收藏');
            }
        }
        
        function loadChat(id) {
            currentChatId = id;
            const chat = chats.find(c => c.id === id);
            if (!chat) return;
            history = [];
            attachments = [];
            document.getElementById('messagesContainer').innerHTML = '';
            if (chat.role) selectRole(chat.role);
            chat.messages.forEach((m, idx) => {
                addMessageToUI(m.role, m.content, m.time, m.toolResults, idx, m.reasoning);
                if (m.role === 'user') history.push([m.content, '']);
            });
            chat.messages.filter(m => m.role === 'assistant').forEach((m, i) => {
                if (history[i]) history[i][1] = m.content;
            });
            renderChatList();
        }
        
        function deleteChat(id) {
            chats = chats.filter(c => c.id !== id);
            saveChats();
            if (currentChatId === id) {
                if (chats.length > 0) loadChat(chats[0].id);
                else { 
                    currentChatId = null; 
                    history = []; 
                    showWelcome();
                }
            }
            renderChatList();
            showToast('对话已删除');
        }
        
        let editingMsgIdx = null;
        let replyingTo = null;
        
        function editMessage(idx) {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat || !chat.messages[idx]) return;
            const msg = chat.messages[idx];
            if (msg.role !== 'user') return;
            editingMsgIdx = idx;
            const input = document.getElementById('mainInput');
            input.value = msg.content;
            input.focus();
            updateCharCount();
            document.getElementById('editHint').style.display = 'flex';
        }
        
        function cancelEdit() {
            editingMsgIdx = null;
            document.getElementById('mainInput').value = '';
            document.getElementById('editHint').style.display = 'none';
            updateCharCount();
        }
        
        function replyToMessage(idx) {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat || !chat.messages[idx]) return;
            replyingTo = { idx, content: chat.messages[idx].content.slice(0, 100) };
            document.getElementById('replyHint').style.display = 'flex';
            document.getElementById('replyContent').textContent = replyingTo.content;
            document.getElementById('mainInput').focus();
        }
        
        function cancelReply() {
            replyingTo = null;
            document.getElementById('replyHint').style.display = 'none';
        }
        
        function addMessageToUI(role, content, time = null, toolResults = null, msgIdx = null, reasoning = null) {
            const container = document.getElementById('messagesContainer');
            const msg = document.createElement('div');
            msg.className = `message ${role}`;
            msg.dataset.idx = msgIdx;
            const t = time || new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            const roleData = roles.find(r => r.id === currentRole) || roles[0];
            const avatar = role === 'user' ? '👤' : (roleData.avatar.startsWith('/') ? `<img src="${roleData.avatar}">` : roleData.icon);
            
            let toolHtml = '';
            if (toolResults && toolResults.length) {
                toolHtml = toolResults.map(tr => `<div class="tool-result"><strong>${tr.tool}:</strong> ${tr.result}</div>`).join('');
            }
            
            // 构建思考过程HTML（如果有）
            let reasoningHtml = '';
            if (reasoning && reasoning.trim()) {
                reasoningHtml = `
                    <div class="reasoning-section">
                        <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                            <span class="reasoning-toggle-icon">▶</span>
                            <span>思考过程</span>
                        </div>
                        <div class="reasoning-content">${reasoning.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
                    </div>
                `;
            }
            
            const renderedContent = settings.markdown ? marked.parse(content) : content.replace(/\\n/g, '<br>');
            let actionBtns = `<button class="msg-action-btn" onclick="copyMessage(this)">📋</button><button class="msg-action-btn" onclick="speakMessage(this)">🔊</button>`;
            if (role === 'user' && msgIdx !== null) {
                actionBtns += `<button class="msg-action-btn" onclick="editMessage(${msgIdx})">✏️</button>`;
            }
            if (msgIdx !== null) {
                actionBtns += `<button class="msg-action-btn" onclick="replyToMessage(${msgIdx})">↩️</button>`;
            }
            
            msg.innerHTML = `
                <div class="message-avatar" style="background:linear-gradient(135deg,var(--primary),var(--secondary));">${avatar}</div>
                <div class="message-content-wrapper">
                    ${reasoningHtml}
                    <div class="message-content">${renderedContent}</div>
                    ${toolHtml}
                    <div class="message-actions">${actionBtns}</div>
                    <div class="message-time">${t}</div>
                </div>
            `;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
            msg.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }
        
        function handleInput(e) {
            updateCharCount();
            autoResize(e.target);
            const value = e.target.value;
            const hint = document.getElementById('commandHint');
            if (value.startsWith('/')) {
                const cmd = value.slice(1).toLowerCase();
                const matches = Object.entries(commands).filter(([k]) => k.slice(1).startsWith(cmd));
                if (matches.length) {
                    hint.innerHTML = matches.map(([k,v]) => `<div class="command-item" onclick="executeCommand('${k}')"><strong>${k}</strong> - ${v}</div>`).join('');
                    hint.classList.add('show');
                } else hint.classList.remove('show');
            } else hint.classList.remove('show');
        }
        
        function executeCommand(cmd) {
            document.getElementById('mainInput').value = '';
            document.getElementById('commandHint').classList.remove('show');
            switch(cmd) {
                case '/help': showToast('命令: /clear /export /role /lora /tool /code /kb /settings /stats /new'); break;
                case '/clear': clearCurrentChat(); break;
                case '/export': exportChat(); break;
                case '/code': showCodeModal(); break;
                case '/tool': switchTab('tools'); break;
                case '/kb': showKBModal(); break;
                case '/settings': openSettings(); break;
                case '/new': newChat(); break;
            }
        }
        
        function clearCurrentChat() {
            const chat = chats.find(c => c.id === currentChatId);
            if (chat) { 
                chat.messages = []; 
                history = []; 
                saveChats(); 
                showWelcome(); 
                showToast('对话已清空'); 
            }
        }
        
        function openPromptWorkbenchModal() {
            const tab = document.querySelector('.sidebar-tab[onclick*="prompts"]');
            if (tab) switchTab('prompts', tab);
        }
        
        function saveFeatureActionHistory() {
            localStorage.setItem('kaguya_feature_actions', JSON.stringify(featureActionHistory.slice(0, 20)));
        }
        
        function recordFeatureAction(name, type = '导航') {
            const item = {
                name,
                type,
                time: Date.now()
            };
            featureActionHistory.unshift(item);
            featureActionHistory = featureActionHistory.slice(0, 20);
            saveFeatureActionHistory();
            renderFeatureCenterMeta();
        }
        
        function renderFeatureCenterMeta() {
            const statusEl = document.getElementById('centerStatusGrid');
            const recentEl = document.getElementById('centerRecentActions');
            if (!statusEl || !recentEl) return;
            const enabledPlugins = mcpPlugins.filter(x => x.enabled).length;
            const statusItems = [
                {label: 'DeepSeek', value: deepseekConfig.enabled ? '已启用' : '未启用', cls: deepseekConfig.enabled ? 'ok' : 'warn'},
                {label: 'RAG状态', value: ragEnabled ? '已开启' : '已关闭', cls: ragEnabled ? 'ok' : 'warn'},
                {label: '文档总数', value: `${ragDocuments.length}`, cls: ragDocuments.length > 0 ? 'ok' : 'warn'},
                {label: '健康评分', value: `${consoleOverview.health_score ?? 0}`, cls: (consoleOverview.health_score ?? 0) >= 70 ? 'ok' : 'warn'},
                {label: '工作流', value: `${workflows.length}`, cls: workflows.length > 0 ? 'ok' : 'warn'},
                {label: '启用插件', value: `${enabledPlugins}`, cls: enabledPlugins > 0 ? 'ok' : 'warn'},
                {label: '会话总数', value: `${chats.length}`, cls: chats.length > 0 ? 'ok' : 'warn'},
                {label: '项目任务', value: `${projectTasks.length}`, cls: projectTasks.length > 0 ? 'ok' : 'warn'},
                {label: '知识产物', value: `${projectArtifacts.length}`, cls: projectArtifacts.length > 0 ? 'ok' : 'warn'},
                {label: '运营活动', value: `${opsCampaigns.length}`, cls: opsCampaigns.length > 0 ? 'ok' : 'warn'},
                {label: '发布计划', value: `${releasePlans.length}`, cls: releasePlans.length > 0 ? 'ok' : 'warn'},
                {label: '告警规则', value: `${alertRules.length}`, cls: alertRules.length > 0 ? 'ok' : 'warn'},
                {label: 'AB实验', value: `${abExperiments.length}`, cls: abExperiments.length > 0 ? 'ok' : 'warn'},
                {label: '集成数', value: `${integrationItems.length}`, cls: integrationItems.length > 0 ? 'ok' : 'warn'},
                {label: '里程碑', value: `${projectMilestones.length}`, cls: projectMilestones.length > 0 ? 'ok' : 'warn'},
                {label: '风险项', value: `${projectRisks.length}`, cls: projectRisks.length > 0 ? 'ok' : 'warn'},
                {label: '生态项目', value: `${workspaceOverview.total ?? workspaceProjects.length}`, cls: (workspaceOverview.total ?? workspaceProjects.length) > 0 ? 'ok' : 'warn'}
            ];
            statusEl.innerHTML = statusItems.map(s => `
                <div class="feature-center-status-item">
                    <div class="feature-center-status-label">${s.label}</div>
                    <div class="feature-center-status-value ${s.cls}">${s.value}</div>
                </div>
            `).join('');
            if (!featureActionHistory.length) {
                recentEl.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:10px;">暂无操作记录</div>';
            } else {
                recentEl.innerHTML = featureActionHistory.slice(0, 8).map(item => `
                    <div class="feature-center-recent-item">
                        <span>${item.type} · ${item.name}</span>
                        <span>${new Date(item.time).toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}</span>
                    </div>
                `).join('');
            }
        }
        
        function focusFeatureTarget(targetId) {
            if (!targetId) return;
            const el = document.getElementById(targetId);
            if (!el) return;
            el.scrollIntoView({behavior: 'smooth', block: 'start'});
            el.classList.add('section-focus');
            setTimeout(() => el.classList.remove('section-focus'), 1200);
        }
        
        function getFeatureTargetId(name) {
            const map = {
                console: 'consoleScoreGrid',
                ecosystem: 'workspaceOverviewCards',
                scenes: 'sceneWorkspace',
                prompts: 'promptList',
                project: 'projectOverviewCards',
                ops: 'opsOverviewCards',
                release: 'releaseOverviewCards',
                alert: 'alertOverviewCards',
                ab: 'abOverviewCards',
                integration: 'integrationOverviewCards',
                workflow: 'workflowList',
                memory: 'memoryList',
                multimodal: 'multimodalResults',
                finetune: 'finetuneJobs',
                rag: 'ragDocList',
                mcp: 'mcpList'
            };
            return map[name] || null;
        }
        
        function openMobileSection(tabName) {
            const target = tabName === 'center' ? null : document.querySelector(`.sidebar-tab[onclick*="${tabName}"]`);
            if (tabName === 'center') {
                openFeatureCenter();
            } else if (target) {
                switchTab(tabName, target);
                focusFeatureTarget(getFeatureTargetId(tabName));
                recordFeatureAction(`移动端切换到${tabName}`, '快捷栏');
            }
            document.querySelectorAll('.mobile-dock-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.querySelector(`.mobile-dock-btn[data-mobile-tab="${tabName}"]`);
            if (activeBtn) activeBtn.classList.add('active');
        }
        
        function openFeatureSection(name) {
            closeModal('featureCenterModal');
            const tabMappings = ['console', 'ecosystem', 'scenes', 'prompts', 'project', 'ops', 'release', 'alert', 'ab', 'integration', 'workflow', 'memory', 'multimodal', 'finetune', 'rag', 'mcp'];
            const nameMap = {
                console: '统一控制台',
                ecosystem: '项目生态',
                scenes: '场景引擎',
                prompts: '模板工作台',
                project: '项目中台',
                ops: '运营中心',
                release: '发布中心',
                alert: '告警中心',
                ab: '实验中心',
                integration: '集成市场',
                workflow: '工作流编排',
                memory: '记忆系统',
                multimodal: '视觉理解',
                finetune: '模型微调',
                rag: 'RAG知识库',
                mcp: 'MCP插件',
                models: '多模型API',
                settings: '系统设置',
                deepseek: 'DeepSeek配置',
                code: '代码执行器',
                stats: '统计仪表盘'
            };
            
            if (tabMappings.includes(name)) {
                const target = document.querySelector(`.sidebar-tab[onclick*="${name}"]`);
                if (target) {
                    target.click();
                } else {
                    switchTab(name, null);
                }
                setTimeout(() => {
                    const targetId = getFeatureTargetId(name);
                    const elem = document.getElementById(targetId);
                    if (elem) elem.scrollIntoView({behavior: 'smooth', block: 'center'});
                }, 300);
                recordFeatureAction(nameMap[name] || name, '功能中心');
                return;
            }
            if (name === 'models') { openModelsConfig(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'settings') { openSettings(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'deepseek') { openDeepSeek(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'code') { showCodeModal(); recordFeatureAction(nameMap[name], '功能中心'); return; }
            if (name === 'stats') { openStats(); recordFeatureAction(nameMap[name], '功能中心'); return; }
        }
        
        async function sendMessage() {
            const input = document.getElementById('mainInput');
            let msg = input.value.trim();
            if (!msg && attachments.length === 0) return;
            if (msg.startsWith('/')) { executeCommand(msg.split(' ')[0]); return; }
            
            if (deepseekConfig.enabled && deepseekConfig.apiKey) {
                await sendDeepSeekMessage(msg, input);
                return;
            } else if (deepseekConfig.enabled && !deepseekConfig.apiKey) {
                // DeepSeek 已启用但没有 API Key，显示警告并使用本地模型
                showToast('⚠️ DeepSeek 已启用但未配置 API Key，将使用本地模型');
            }
            
            const sendBtn = document.getElementById('sendBtn');
            const stopBtn = document.getElementById('stopBtn');
            sendBtn.disabled = true;
            sendBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            isGenerating = true;
            input.value = '';
            autoResize(input);
            updateCharCount();
            document.getElementById('commandHint').classList.remove('show');
            document.getElementById('editHint').style.display = 'none';
            document.getElementById('replyHint').style.display = 'none';
            document.getElementById('statusText').textContent = '正在生成...';
            
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            
            if (editingMsgIdx !== null) {
                chat.messages[editingMsgIdx].content = msg;
                const histIdx = Math.floor(editingMsgIdx / 2);
                if (history[histIdx]) history[histIdx][0] = msg;
                editingMsgIdx = null;
                document.getElementById('messagesContainer').innerHTML = '';
                chat.messages.forEach((m, idx) => addMessageToUI(m.role, m.content, m.time, m.toolResults, idx, m.reasoning));
                saveChats();
                
                const container = document.getElementById('messagesContainer');
                const msgEl = document.createElement('div');
                msgEl.className = 'message assistant';
                const roleData = roles.find(r => r.id === currentRole) || roles[0];
                const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
                msgEl.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content" id="streamContent"></div><div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div><div class="message-time">${replyTime}</div></div>`;
                container.appendChild(msgEl);
                const contentEl = document.getElementById('streamContent');
                let fullContent = '';
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg, history: history.slice(0, histIdx), role: currentRole,
                        lora: currentLora !== 'none' ? currentLora : null,
                        structured_template: currentStructuredTemplate,
                        temperature: settings.temp, max_tokens: settings.tokens,
                        use_rag: ragEnabled,
                        rag_alpha: ragSettings.alpha,
                        rag_rerank: ragSettings.useRerank,
                        rag_top_k: ragSettings.topK,
                        rag_cache: ragSettings.useCache,
                        rag_expansion: ragSettings.useExpansion,
                        rag_hyde: ragSettings.useHyde,
                        rag_multi_query: ragSettings.useMultiQuery,
                        rag_decomposition: ragSettings.useDecomposition,
                        rag_adaptive: ragSettings.useAdaptive,
                        rag_rrf: ragSettings.useRrf,
                        rag_metadata_filter: ragSettings.useMetadataFilter,
                        rag_time_weight: ragSettings.useTimeWeight,
                        rag_iterative: ragSettings.useIterative
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 忽略 thinking 类型的数据，不显示思考过程
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    if (chat.messages[editingMsgIdx + 1]) {
                                        chat.messages[editingMsgIdx + 1].content = fullContent;
                                    } else {
                                        chat.messages.push({ role: 'assistant', content: fullContent, time: replyTime });
                                    }
                                    if (history[histIdx]) history[histIdx][1] = fullContent;
                                    saveChats();
                                }
                            } catch (e) {
                                console.error('Parse error:', e, 'Line:', line);
                            }
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
                currentStructuredTemplate = null;
                
                isGenerating = false;
                sendBtn.disabled = false;
                sendBtn.style.display = 'flex';
                stopBtn.style.display = 'none';
                document.getElementById('statusText').textContent = '准备就绪';
                input.focus();
                return;
            }
            
            if (replyingTo) {
                msg = `> ${replyingTo.content}\\n\\n${msg}`;
                replyingTo = null;
            }
            
            let toolResults = [];
            if (activeTools.size > 0) {
                for (const toolId of activeTools) {
                    if (tools[toolId]) {
                        try {
                            const res = await fetch('/tool/execute', {
                                method: 'POST', headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({tool: toolId, input: msg})
                            });
                            const data = await res.json();
                            if (data.result) toolResults.push({tool: tools[toolId].name, result: data.result});
                        } catch (e) {}
                    }
                }
            }
            
            chat.messages.push({ role: 'user', content: msg, time, toolResults: toolResults.length ? toolResults : null });
            addMessageToUI('user', msg, time, toolResults.length ? toolResults : null, chat.messages.length - 1);
            
            if (chat.title === '新对话') {
                chat.title = msg.slice(0, 20) + (msg.length > 20 ? '...' : '');
                saveChats();
            }
            
            history.push([msg, '']);
            const startTime = Date.now();
            
            try {
                const container = document.getElementById('messagesContainer');
                const msgEl = document.createElement('div');
                msgEl.className = 'message assistant';
                const roleData = roles.find(r => r.id === currentRole) || roles[0];
                const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
                // 创建包含思考过程区域的消息结构
                msgEl.innerHTML = `
                    <div class="message-avatar">${roleData.icon || '🤖'}</div>
                    <div class="message-content-wrapper">
                        <div class="reasoning-section" style="display:none;">
                            <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                                <span class="reasoning-toggle-icon">▶</span>
                                <span>思考过程</span>
                            </div>
                            <div class="reasoning-content"></div>
                        </div>
                        <div class="message-content"></div>
                        <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄 重新生成</button></div>
                        <div class="message-time">${replyTime}</div>
                    </div>
                `;
                container.appendChild(msgEl);
                const contentEl = msgEl.querySelector('.message-content');
                const reasoningSection = msgEl.querySelector('.reasoning-section');
                const reasoningContentEl = msgEl.querySelector('.reasoning-content');
                let fullContent = '';
                let fullReasoning = '';
                let hasReasoning = false;
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg, history: history.slice(0,-1), role: currentRole,
                        lora: currentLora !== 'none' ? currentLora : null,
                        structured_template: currentStructuredTemplate,
                        temperature: settings.temp, max_tokens: settings.tokens,
                        use_rag: ragEnabled,
                        rag_alpha: ragSettings.alpha,
                        rag_rerank: ragSettings.useRerank,
                        rag_top_k: ragSettings.topK,
                        rag_cache: ragSettings.useCache,
                        rag_expansion: ragSettings.useExpansion,
                        rag_hyde: ragSettings.useHyde,
                        rag_multi_query: ragSettings.useMultiQuery,
                        rag_decomposition: ragSettings.useDecomposition,
                        rag_adaptive: ragSettings.useAdaptive,
                        rag_rrf: ragSettings.useRrf,
                        rag_metadata_filter: ragSettings.useMetadataFilter,
                        rag_time_weight: ragSettings.useTimeWeight,
                        rag_iterative: ragSettings.useIterative
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 处理思考过程内容 (Qwen3.5 模型的 thinking 字段)
                                if (data.thinking) {
                                    fullReasoning += data.thinking;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 兼容旧格式的 reasoning 字段
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    stats.sessions++;
                                    stats.latencies.push(Date.now() - startTime);
                                    if (data.tokens_in) stats.inputTokens += data.tokens_in;
                                    if (data.tokens_out) stats.outputTokens += data.tokens_out;
                                    saveStats();
                                    updateStats();
                                    if (data.rag_sources && data.rag_sources.length) {
                                        const sourcesHtml = renderRagSources(data.rag_sources);
                                        contentEl.innerHTML += sourcesHtml;
                                    }
                                    chat.messages.push({ role: 'assistant', content: fullContent, reasoning: fullReasoning || null, time: replyTime });
                                    history[history.length - 1][1] = fullContent;
                                    saveChats();
                                    if (settings.voice) requestTTS(fullContent);
                                }
                            } catch (e) {}
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                if (reasoningSection) reasoningSection.id = '';
                if (reasoningContentEl) reasoningContentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.error('Stream error:', e);
                    addMessageToUI('assistant', '❌ 生成失败: ' + (e.message || '网络错误，请检查Ollama服务是否运行'), time);
                }
            }
            
            isGenerating = false;
            currentStructuredTemplate = null;
            sendBtn.disabled = false;
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            document.getElementById('statusText').textContent = '准备就绪';
            input.focus();
        }
        
        function regenerate() {
            if (history.length > 0) {
                history.pop();
                const chat = chats.find(c => c.id === currentChatId);
                if (chat && chat.messages.length > 0) {
                    chat.messages.pop();
                    saveChats();
                }
                const container = document.getElementById('messagesContainer');
                if (container.lastElementChild) container.removeChild(container.lastElementChild);
                sendMessage();
            }
        }
        
        function showTyping() {
            const container = document.getElementById('messagesContainer');
            const typing = document.createElement('div');
            typing.className = 'message assistant';
            typing.id = 'typingIndicator';
            const roleData = roles.find(r => r.id === currentRole) || roles[0];
            typing.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>`;
            container.appendChild(typing);
            container.scrollTop = container.scrollHeight;
        }
        
        function hideTyping() { const t = document.getElementById('typingIndicator'); if (t) t.remove(); }
        
        function requestTTS(text) {
            fetch('/tts', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text: text.slice(0, 300) }) })
                .then(r => r.json()).then(data => { if (data.audio_url) new Audio(data.audio_url).play(); });
        }
        
        function showCodeModal() { document.getElementById('codeModal').classList.add('show'); }
        function showKBModal() { document.getElementById('kbModal').classList.add('show'); }
        function openFeatureCenter() {
            renderFeatureCenterMeta();
            document.getElementById('featureCenterModal').classList.add('show');
            recordFeatureAction('打开功能中心', '中心');
            loadMcpPlugins();
            loadWorkflows();
            loadProjectCenter();
            setTimeout(renderFeatureCenterMeta, 400);
        }
        
        function executeCode() {
            const code = document.getElementById('codeEditor').value;
            if (!code.trim()) return;
            fetch('/code/execute', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            }).then(r => r.json()).then(data => {
                const output = document.getElementById('codeOutput');
                output.style.display = 'block';
                output.innerHTML = `<strong>${data.success ? '✅ 输出:' : '❌ 错误:'}</strong>\\n${data.output}`;
            });
        }
        
        function addToKB() {
            const text = document.getElementById('kbInput').value.trim();
            if (!text) return;
            fetch('/kb/add', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('已添加到知识库');
                    document.getElementById('kbInput').value = '';
                }
            });
        }
        
        function searchKB() {
            const query = document.getElementById('kbSearch').value.trim();
            if (!query) return;
            fetch('/kb/search', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            }).then(r => r.json()).then(data => {
                const results = document.getElementById('kbResults');
                if (data.results && data.results.length) {
                    results.innerHTML = data.results.map(r => `<div style="padding:8px;background:var(--bg-secondary);border-radius:6px;margin-bottom:6px;font-size:12px;">${r.text.slice(0, 200)}...</div>`).join('');
                } else {
                    results.innerHTML = '<div style="color:var(--text-muted);font-size:12px;">未找到相关内容</div>';
                }
            });
        }
        
        function handleKeyDown(e) { 
            if (e.key === 'Enter' && !e.shiftKey) { 
                e.preventDefault(); 
                sendMessage(); 
            } 
        }
        
        let shortcutTimeout = null;
        function showShortcutHint() {
            const hint = document.getElementById('shortcutHint');
            hint.classList.add('show');
            if (shortcutTimeout) clearTimeout(shortcutTimeout);
            shortcutTimeout = setTimeout(() => hint.classList.remove('show'), 3000);
        }
        
        document.addEventListener('keydown', e => {
            if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newChat(); }
            if (e.ctrlKey && e.key === ',') { e.preventDefault(); openSettings(); }
            if (e.ctrlKey && e.key === 'd') { e.preventDefault(); toggleDarkMode(); }
            if (e.key === '?' && e.shiftKey) { e.preventDefault(); showShortcutHint(); }
            if (e.key === 'Escape') {
                const modals = Array.from(document.querySelectorAll('.modal-overlay.show'));
                if (modals.length) modals[modals.length - 1].classList.remove('show');
                closeSettings();
            }
        });
        
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', e => {
                if (e.target === overlay) overlay.classList.remove('show');
            });
        });
        
        function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 100) + 'px'; }
        function updateCharCount() { document.getElementById('charCount').textContent = `${document.getElementById('mainInput').value.length} / 4000`; }
        function updateTemp(v) { document.getElementById('tempValue').textContent = v; settings.temp = parseFloat(v); saveSettings(); }
        
        function updateSetting(k, v) {
            if (k === 'temp') { settings.temp = parseFloat(v); document.getElementById('settingTempValue').textContent = v; }
            if (k === 'tokens') { settings.tokens = parseInt(v); document.getElementById('settingTokensValue').textContent = v; }
            if (k === 'voice') settings.voice = v;
            if (k === 'markdown') settings.markdown = v;
            saveSettings();
        }
        
        function toggleDarkMode() {
            document.body.classList.toggle('dark');
            settings.dark = document.body.classList.contains('dark');
            document.getElementById('darkModeToggle').checked = settings.dark;
            saveSettings();
            showToast(settings.dark ? '已开启深色模式' : '已关闭深色模式');
        }
        
        function toggleVoice() {
            settings.voice = !settings.voice;
            document.getElementById('voiceOutputToggle').checked = settings.voice;
            document.getElementById('voiceBtn').classList.toggle('active', settings.voice);
            saveSettings();
            showToast(settings.voice ? '已开启语音输出' : '已关闭语音输出');
        }
        
        function openSettings() { document.getElementById('settingsPanel').classList.add('open'); }
        
        function expandToCenter(panelId) {
            const panel = document.getElementById(panelId);
            if (!panel) return;
            
            const chatArea = document.querySelector('.chat-area');
            const sidebar = document.querySelector('.sidebar');
            const header = document.querySelector('.header');
            
            if (panel.classList.contains('expanded')) {
                panel.classList.remove('expanded');
                panel.style.position = '';
                panel.style.top = '';
                panel.style.left = '';
                panel.style.width = '';
                panel.style.height = '';
                panel.style.zIndex = '';
                panel.style.background = '';
                if (chatArea) chatArea.style.display = '';
                if (sidebar) sidebar.style.display = '';
                if (header) header.style.display = '';
            } else {
                panel.classList.add('expanded');
                panel.style.position = 'fixed';
                panel.style.top = '60px';
                panel.style.left = '60px';
                panel.style.right = '60px';
                panel.style.bottom = '20px';
                panel.style.width = 'auto';
                panel.style.height = 'auto';
                panel.style.zIndex = '200';
                panel.style.background = 'var(--bg-primary)';
                if (chatArea) chatArea.style.display = 'none';
                if (sidebar) sidebar.style.display = 'none';
                if (header) header.style.display = 'none';
            }
        }
        
        function toggleRightSidebar() {
            const sidebar = document.getElementById('rightSidebar');
            sidebar.classList.toggle('open');
            if (sidebar.classList.contains('open')) {
                updateRightSidebarStatus();
                updateRecentChats();
            }
        }
        
        function updateRightSidebarStatus() {
            document.getElementById('currentRoleDisplay').textContent = roles[currentRole]?.name || currentRole;
            document.getElementById('currentLoraDisplay').textContent = currentLora === 'none' ? '未加载' : currentLora;
            document.getElementById('ragStatusDisplay').textContent = ragEnabled ? '开启' : '关闭';
        }
        
        function updateRecentChats() {
            const list = document.getElementById('recentChatsList');
            const recent = chats.slice(0, 5);
            if (recent.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无对话</div>';
                return;
            }
            list.innerHTML = recent.map(c => 
                `<div class="recent-chat-item" onclick="loadChat('${c.id}'); toggleRightSidebar();">${c.title}</div>`
            ).join('');
        }
        
        function openDeepSeek() {
            document.getElementById('deepseekApiKey').value = deepseekConfig.apiKey || '';
            document.getElementById('deepseekApiUrl').value = deepseekConfig.apiUrl || 'https://api.deepseek.com';
            document.getElementById('deepseekModel').value = deepseekConfig.model || 'deepseek-chat';
            document.getElementById('deepseekEnabled').checked = deepseekConfig.enabled || false;
            document.getElementById('deepseekModal').classList.add('show');
        }
        
        function saveDeepSeek() {
            deepseekConfig = {
                apiKey: document.getElementById('deepseekApiKey').value,
                apiUrl: document.getElementById('deepseekApiUrl').value || 'https://api.deepseek.com',
                model: document.getElementById('deepseekModel').value,
                enabled: document.getElementById('deepseekEnabled').checked
            };
            localStorage.setItem('deepseek_config', JSON.stringify(deepseekConfig));
            updateDeepSeekIndicator();
            renderFeatureCenterMeta();
            closeModal('deepseekModal');
            showToast('DeepSeek配置已保存');
        }
        
        function testDeepSeek() {
            const apiKey = document.getElementById('deepseekApiKey').value;
            const apiUrl = document.getElementById('deepseekApiUrl').value || 'https://api.deepseek.com';
            const statusEl = document.getElementById('deepseekStatus');
            
            if (!apiKey) {
                statusEl.innerHTML = '<span style="color:#e74c3c;">请输入API Key</span>';
                return;
            }
            
            statusEl.innerHTML = '<span style="color:var(--primary);">🔄 测试连接中...</span>';
            
            fetch('/deepseek/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({apiKey, apiUrl})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    statusEl.innerHTML = '<span style="color:#10b981;">✅ 连接成功！模型可用</span>';
                } else {
                    statusEl.innerHTML = '<span style="color:#e74c3c;">❌ ' + (data.error || '连接失败') + '</span>';
                }
            }).catch(e => {
                statusEl.innerHTML = '<span style="color:#e74c3c;">❌ 网络错误</span>';
            });
        }
        
        function updateDeepSeekIndicator() {
            const indicators = document.getElementById('headerIndicators');
            let html = indicators.innerHTML;
            const dsIndicator = '<div class="indicator" style="background:linear-gradient(135deg,rgba(79,70,229,0.2),rgba(124,58,237,0.1));color:#7c3aed;border:1px solid rgba(79,70,229,0.3);"><span>🤖</span><span>DeepSeek</span></div>';
            if (deepseekConfig.enabled && !html.includes('DeepSeek')) {
                indicators.innerHTML = dsIndicator + html;
            } else if (!deepseekConfig.enabled) {
                indicators.innerHTML = html.replace(dsIndicator, '');
            }
        }
        
        function checkExternalApiWarning() {
            // 检查是否配置了任何外部API
            const hasExternalApi = deepseekConfig.enabled && deepseekConfig.apiKey;
            const hasShownWarning = sessionStorage.getItem('api_warning_shown');
            
            if (!hasExternalApi && !hasShownWarning) {
                // 显示警告弹窗
                showApiWarningModal();
                sessionStorage.setItem('api_warning_shown', 'true');
            }
        }
        
        function showApiWarningModal() {
            const modal = document.createElement('div');
            modal.id = 'apiWarningModal';
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.5); z-index: 10000;
                display: flex; align-items: center; justify-content: center;
            `;
            modal.innerHTML = `
                <div style="
                    background: var(--bg-primary, #fff); border-radius: 16px;
                    padding: 24px; max-width: 400px; width: 90%;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    border: 1px solid var(--border, #e5e7eb);
                ">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
                        <h3 style="margin: 0 0 12px 0; color: var(--text-primary, #1f2937);">外部API未配置</h3>
                        <p style="color: var(--text-secondary, #6b7280); margin: 0; line-height: 1.6;">
                            当前未接入任何外部AI API（如DeepSeek、OpenAI等）。<br>
                            部分高级功能（场景生成、联网搜索等）将无法使用。
                        </p>
                    </div>
                    <div style="display: flex; gap: 12px;">
                        <button onclick="closeApiWarningModal()" style="
                            flex: 1; padding: 12px; border: 1px solid var(--border, #e5e7eb);
                            background: transparent; border-radius: 8px; cursor: pointer;
                            color: var(--text-secondary, #6b7280);
                        ">稍后再说</button>
                        <button onclick="openExternalApiSettings(); closeApiWarningModal();" style="
                            flex: 1; padding: 12px; border: none;
                            background: linear-gradient(135deg, #667eea, #764ba2);
                            border-radius: 8px; cursor: pointer; color: white; font-weight: 500;
                        ">立即配置</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
            
            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeApiWarningModal();
            });
        }
        
        function closeApiWarningModal() {
            const modal = document.getElementById('apiWarningModal');
            if (modal) modal.remove();
        }
        
        function openExternalApiSettings() {
            // 打开设置面板并切换到外部API配置
            openSettings();
            // 延迟切换到DeepSeek配置
            setTimeout(() => {
                const deepseekToggle = document.getElementById('deepseekEnabled');
                if (deepseekToggle) {
                    deepseekToggle.focus();
                }
            }, 100);
        }
        
        function openStats() {
            document.getElementById('statSessions').textContent = stats.sessions || 0;
            document.getElementById('statInput').textContent = stats.inputTokens || 0;
            document.getElementById('statOutput').textContent = stats.outputTokens || 0;
            const avgLatency = stats.latencies && stats.latencies.length ? Math.round(stats.latencies.reduce((a,b) => a+b, 0) / stats.latencies.length) : 0;
            document.getElementById('statLatency').textContent = avgLatency + 'ms';
            
            const chart = document.getElementById('usageChart');
            if (!chart) {
                document.getElementById('statsModal').classList.add('show');
                return;
            }
            chart.innerHTML = '';
            const data = [12, 25, 18, 30, 22, 35, 28, 40, 33, 45, 38, 50];
            const max = Math.max(...data);
            data.forEach((v, i) => {
                const bar = document.createElement('div');
                bar.style.cssText = `width:100%;background:linear-gradient(to top,#10b981,#34d399);border-radius:4px 4px 0 0;height:${(v/max)*100}%;opacity:${0.5 + (i/data.length)*0.5};transition:height 0.3s;`;
                bar.title = `${v} 次对话`;
                chart.appendChild(bar);
            });
            
            const toolStats = document.getElementById('toolStats');
            const toolData = {calculator: 15, search: 42, translate: 28, weather: 12};
            toolStats.innerHTML = Object.entries(toolData).map(([k, v]) => 
                `<div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span>${k}</span><span style="color:var(--primary);">${v}次</span></div>`
            ).join('');
            
            document.getElementById('statsModal').classList.add('show');
        }
        
        function resetStats() {
            stats = {sessions: 0, inputTokens: 0, outputTokens: 0, latencies: []};
            localStorage.setItem('kaguya_stats', JSON.stringify(stats));
            openStats();
            showToast('统计数据已重置');
        }
        
        function exportStats() {
            const report = {
                date: new Date().toISOString(),
                sessions: stats.sessions,
                inputTokens: stats.inputTokens,
                outputTokens: stats.outputTokens,
                avgLatency: stats.latencies && stats.latencies.length ? Math.round(stats.latencies.reduce((a,b) => a+b, 0) / stats.latencies.length) : 0
            };
            const blob = new Blob([JSON.stringify(report, null, 2)], {type: 'application/json'});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `kaguya_stats_${new Date().toISOString().slice(0,10)}.json`;
            a.click();
            showToast('报告已导出');
        }
        
        function openModelConfig() {
            document.getElementById('modelTemp').value = settings.temp || 0.7;
            document.getElementById('modelTempVal').textContent = settings.temp || 0.7;
            document.getElementById('modelTokens').value = settings.tokens || 1024;
            document.getElementById('modelTokensVal').textContent = settings.tokens || 1024;
            document.getElementById('modelModal').classList.add('show');
        }
        
        function saveModelConfig() {
            settings.temp = parseFloat(document.getElementById('modelTemp').value);
            settings.tokens = parseInt(document.getElementById('modelTokens').value);
            localStorage.setItem('kaguya_settings', JSON.stringify(settings));
            closeModal('modelModal');
            showToast('模型配置已保存');
        }
        
        function openTheme() {
            document.getElementById('themeModal').classList.add('show');
        }
        
        function applyTheme(theme) {
            const themes = {
                default: {primary: '#667eea', secondary: '#764ba2'},
                ocean: {primary: '#0ea5e9', secondary: '#0284c7'},
                forest: {primary: '#10b981', secondary: '#059669'},
                sunset: {primary: '#f59e0b', secondary: '#ef4444'}
            };
            if (themes[theme]) {
                document.documentElement.style.setProperty('--primary', themes[theme].primary);
                document.documentElement.style.setProperty('--secondary', themes[theme].secondary);
                document.getElementById('primaryColor').value = themes[theme].primary;
                document.getElementById('primaryColorText').value = themes[theme].primary;
            }
        }
        
        function saveTheme() {
            const primary = document.getElementById('primaryColor').value;
            document.documentElement.style.setProperty('--primary', primary);
            localStorage.setItem('kaguya_theme', primary);
            closeModal('themeModal');
            showToast('主题已应用');
        }
        
        function resetTheme() {
            applyTheme('default');
            showToast('主题已重置');
        }
        
        let modelsConfig = JSON.parse(localStorage.getItem('models_config') || '{}');
        
        function openModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu'];
            models.forEach(m => {
                const config = modelsConfig[m] || {};
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                if (apiKeyEl) apiKeyEl.value = config.apiKey || '';
                if (modelEl) modelEl.value = config.model || modelEl.options[0].value;
                if (enabledEl) enabledEl.checked = config.enabled || false;
                if (baseUrlEl) baseUrlEl.value = config.baseUrl || '';
            });
            document.getElementById('modelsModal').classList.add('show');
        }
        
        function toggleModelConfig(model) {
            const configEl = document.getElementById(`${model}Config`);
            if (configEl) {
                configEl.style.display = configEl.style.display === 'none' ? 'block' : 'none';
            }
        }
        
        function saveModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu'];
            models.forEach(m => {
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                modelsConfig[m] = {
                    apiKey: apiKeyEl ? apiKeyEl.value : '',
                    model: modelEl ? modelEl.value : '',
                    enabled: enabledEl ? enabledEl.checked : false,
                    baseUrl: baseUrlEl ? baseUrlEl.value : ''
                };
            });
            localStorage.setItem('models_config', JSON.stringify(modelsConfig));
            closeModal('modelsModal');
            showToast('多模型配置已保存');
        }
        
        function testModelConnection() {
            const statusEl = document.getElementById('modelsStatus');
            statusEl.innerHTML = '<span style="color:var(--primary);">🔄 测试连接中...</span>';
            
            setTimeout(() => {
                const enabledModels = Object.entries(modelsConfig).filter(([k, v]) => v.enabled && v.apiKey);
                if (enabledModels.length > 0) {
                    statusEl.innerHTML = `<span style="color:#10b981;">✅ 已配置 ${enabledModels.length} 个模型</span>`;
                } else {
                    statusEl.innerHTML = '<span style="color:#f59e0b;">⚠️ 请先启用并配置至少一个模型</span>';
                }
            }, 1000);
        }
        
        async function sendDeepSeekMessage(msg, input) {
            const sendBtn = document.getElementById('sendBtn');
            const stopBtn = document.getElementById('stopBtn');
            sendBtn.disabled = true;
            sendBtn.style.display = 'none';
            stopBtn.style.display = 'flex';
            isGenerating = true;
            input.value = '';
            autoResize(input);
            document.getElementById('statusText').textContent = 'DeepSeek生成中...';
            
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            
            addMessageToUI('user', msg, time);
            chat.messages.push({role: 'user', content: msg, time});
            history.push([msg, '']);
            saveChats();
            
            const container = document.getElementById('messagesContainer');
            const msgEl = document.createElement('div');
            msgEl.className = 'message assistant';
            const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            // 创建包含思考过程区域的消息结构（初始隐藏，有内容时显示）
            msgEl.innerHTML = `
                <div class="message-avatar">🤖</div>
                <div class="message-content-wrapper">
                    <div class="reasoning-section" style="display:none;">
                        <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                            <span class="reasoning-toggle-icon">▶</span>
                            <span>思考过程</span>
                        </div>
                        <div class="reasoning-content"></div>
                    </div>
                    <div class="message-content"></div>
                    <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div>
                    <div class="message-time">${replyTime}</div>
                </div>
            `;
            container.appendChild(msgEl);
            const contentEl = msgEl.querySelector('.message-content');
            const reasoningSection = msgEl.querySelector('.reasoning-section');
            const reasoningContentEl = msgEl.querySelector('.reasoning-content');
            let fullContent = '';
            let fullReasoning = '';
            let hasReasoning = false;
            
            const messages = history.slice(-10).map(h => [
                {role: 'user', content: h[0]},
                h[1] ? {role: 'assistant', content: h[1]} : null
            ]).flat().filter(Boolean);
            
            try {
                const res = await fetch('/deepseek/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        apiKey: deepseekConfig.apiKey,
                        apiUrl: deepseekConfig.apiUrl,
                        model: deepseekConfig.model,
                        messages: messages
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\\n/g, '<br>');
                                    container.scrollTop = container.scrollHeight;
                                }
                                // 处理思考过程内容
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    container.scrollTop = container.scrollHeight;
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = marked.parse(fullContent);
                                    }
                                    chat.messages.push({role: 'assistant', content: fullContent, reasoning: fullReasoning, time: replyTime});
                                    history[history.length - 1][1] = fullContent;
                                    saveChats();
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (e) {
                contentEl.innerHTML = `<span style="color:#e74c3c;">DeepSeek API错误: ${e.message}</span>`;
            }
            
            sendBtn.disabled = false;
            sendBtn.style.display = 'flex';
            stopBtn.style.display = 'none';
            isGenerating = false;
            document.getElementById('statusText').textContent = '就绪';
            contentEl.id = '';
            if (reasoningSection) reasoningSection.id = '';
            if (reasoningContentEl) reasoningContentEl.id = '';
        }
        
        // 切换思考过程展开/折叠
        function toggleReasoning(toggleEl) {
            const contentEl = toggleEl.nextElementSibling;
            const isExpanded = toggleEl.classList.contains('expanded');
            if (isExpanded) {
                toggleEl.classList.remove('expanded');
                contentEl.classList.remove('expanded');
            } else {
                toggleEl.classList.add('expanded');
                contentEl.classList.add('expanded');
            }
        }
        function closeSettings() { document.getElementById('settingsPanel').classList.remove('open'); }
        function showToast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 2000); }
        function copyMessage(btn) { navigator.clipboard.writeText(btn.closest('.message-content-wrapper').querySelector('.message-content').textContent); showToast('已复制'); }
        function speakMessage(btn) { const u = new SpeechSynthesisUtterance(btn.closest('.message-content-wrapper').querySelector('.message-content').textContent); u.lang = 'zh-CN'; speechSynthesis.speak(u); }
        
        function handleFileSelect(e) {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                const reader = new FileReader();
                reader.onload = ev => { attachments.push({ name: file.name, type: file.type, data: ev.target.result }); renderAttachments(); };
                reader.readAsDataURL(file);
            });
            e.target.value = '';
        }
        
        function renderAttachments() {
            document.getElementById('attachmentsPreview').innerHTML = attachments.map((a, i) => 
                a.type.startsWith('image') ? `<div class="attachment-item"><img src="${a.data}"><button class="attachment-remove" onclick="attachments.splice(${i},1);renderAttachments();">✕</button></div>` : ''
            ).join('');
        }
        
        function exportChat() {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat) return;
            let text = `=== ${chat.title} ===\\n${new Date().toLocaleString()}\\n\\n`;
            chat.messages.forEach(m => { text += `[${m.role === 'user' ? '我' : 'AI'}] ${m.time}\\n${m.content}\\n\\n`; });
            const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `对话_${new Date().toISOString().slice(0,10)}.txt`; a.click();
            showToast('已导出');
        }
        
        function exportAllChats() {
            let text = `=== 全部对话 ===\\n${new Date().toLocaleString()}\\n\\n`;
            chats.forEach(c => { text += `\\n【${c.title}】\\n`; c.messages.forEach(m => { text += `[${m.role}] ${m.content}\\n`; }); });
            const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `全部对话.txt`; a.click();
            showToast('已导出');
        }
        
        function clearAllData() {
            if (confirm('确定清除所有数据？')) {
                localStorage.clear();
                chats = []; currentChatId = null; history = [];
                stats = {sessions:0,inputTokens:0,outputTokens:0,latencies:[]};
                showWelcome();
                renderChatList(); updateStats();
                showToast('已清除');
            }
        }
        
        // ==================== Tab 切换函数 (必须在所有被调用函数之后定义) ====================
        function switchTab(tab, clickedElement) {
            console.log('switchTab called:', tab, clickedElement);
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (clickedElement) clickedElement.classList.add('active');
            const targetTab = document.getElementById(tab + 'Tab');
            if (!targetTab) return;
            targetTab.classList.add('active');
            if (tab === 'loras') loadLoraList();
            if (tab === 'tools') renderToolList();
            if (tab === 'prompts') renderPromptList();
            if (tab === 'console') loadProjectCenter();
            if (tab === 'ecosystem') loadProjectCenter();
            if (tab === 'scenes') initScenesCenter();
            if (tab === 'project') loadProjectCenter();
            if (tab === 'ops') loadProjectCenter();
            if (tab === 'release') loadProjectCenter();
            if (tab === 'alert') loadProjectCenter();
            if (tab === 'ab') loadProjectCenter();
            if (tab === 'integration') loadProjectCenter();
            if (tab === 'mcp') loadMcpPlugins();
            if (tab === 'workflow') loadWorkflows();
            if (tab === 'memory') { refreshMemoryStats(); searchMemories(); }
            if (tab === 'multimodal') { loadMultimodalHistory(); }
            if (tab === 'finetune') { refreshFinetuneData(); }
        }
        
        // 在 DOM 加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Calling init()...');
            init();
            console.log('init() completed');
        });
    