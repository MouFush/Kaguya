        const isElectron = typeof window !== 'undefined' && typeof window.kaguyaDesktop !== 'undefined';
        const isDesktopMode = isElectron || (typeof window !== 'undefined' && window.location && window.location.search && window.location.search.includes('desktop=1'));
        window.onerror = function(msg, url, line, col, error) {
            console.error('JS ERROR:', {message: msg, url: url, line: line, column: col, stack: error ? error.stack : 'no stack'});
            var pre = document.createElement('pre');
            pre.style.cssText = 'position:fixed;top:0;left:0;right:0;background:red;color:white;z-index:999999;padding:10px;font-size:12px;';
            pre.textContent = 'ERROR: ' + msg + ' at line ' + line + ':' + col + ' in ' + url;
            document.body.appendChild(pre);
            return false;
        };
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
        const KAGUYA_APP_DATA = window.KAGUYA_APP_DATA || {};
        const roles = KAGUYA_APP_DATA.roles || [];
        const loras = KAGUYA_APP_DATA.loras || [];
        const tools = KAGUYA_APP_DATA.tools || {};
        const commands = KAGUYA_APP_DATA.commands || {};
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
        let currentSceneCategory = 'all';
        let sceneHistoryList = [];
        let projectMilestones = [];
        let projectRisks = [];
        let editingArtifactId = null;
        let draggingTaskId = null;
        let selectedTaskIds = new Set();
        let ragSettings = {topK: 5, alpha: 0.5, useRerank: true, showScores: true, useCache: true, useExpansion: true, useHyde: false, useMultiQuery: false, useDecomposition: false, useAdaptive: true, useRrf: false, useMetadataFilter: true, useTimeWeight: false, useIterative: false};
        let lastRagResults = [];
        try {
            const legacyDeepSeekConfig = JSON.parse(localStorage.getItem('deepseek_config') || '{}');
            if (!localStorage.getItem('api_providers_migrated') && Object.keys(legacyDeepSeekConfig).length > 0) {
                const migrated = {};
                if (legacyDeepSeekConfig.apiKey || legacyDeepSeekConfig.apiUrl || legacyDeepSeekConfig.model) {
                    migrated.deepseek = {
                        enabled: Boolean(legacyDeepSeekConfig.apiKey),
                        apiKey: '',
                        apiUrl: legacyDeepSeekConfig.apiUrl || 'https://api.deepseek.com',
                        model: legacyDeepSeekConfig.model || 'deepseek-chat',
                        hasSavedKey: false,
                        masked_api_key: legacyDeepSeekConfig.apiKey ? 'legacy-key-not-migrated' : ''
                    };
                }
                localStorage.setItem('api_providers', JSON.stringify(migrated));
                localStorage.setItem('api_providers_migrated', '1');
            }
            localStorage.removeItem('deepseek_config');
        } catch(e) {}
        
        
        const _domCache = new Map();
        function $(id) { if (!_domCache.has(id)) _domCache.set(id, document.getElementById(id)); return _domCache.get(id); }
        function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
        function escapeHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
        function createModal(idOrOpts, title, bodyHtml, opts = {}) {
            let id, modalTitle, modalBody, modalOpts, footerHtml = '';
            if (typeof idOrOpts === 'object' && idOrOpts !== null) {
                id = 'modal_' + Date.now();
                modalTitle = idOrOpts.title || '';
                modalBody = idOrOpts.body || '';
                if (idOrOpts.actions && idOrOpts.actions.length) {
                    footerHtml = '<div class="modal-footer" style="display:flex;gap:8px;justify-content:flex-end;padding:12px 16px;border-top:1px solid var(--border);">' +
                        idOrOpts.actions.map((a, i) => '<button class="project-mini-btn" data-action="' + i + '" style="' + (a.primary ? 'background:var(--primary);color:#fff;border-color:var(--primary);' : '') + '">' + escapeHtml(a.text) + '</button>').join('') + '</div>';
                }
                modalOpts = {};
            } else {
                id = idOrOpts;
                modalTitle = title;
                modalBody = bodyHtml;
                modalOpts = opts;
            }
            const existing = document.getElementById(id);
            if (existing) existing.remove();
            const overlay = document.createElement('div');
            overlay.id = id;
            overlay.className = 'modal-overlay';
            overlay.innerHTML = `<div class="modal-content" style="max-width:${modalOpts.maxWidth || '600px'}"><div class="modal-header"><h3>${escapeHtml(modalTitle)}</h3><button class="modal-close" onclick="closeModal('${id}')">&times;</button></div><div class="modal-body">${modalBody}</div>${modalOpts.footer || footerHtml}</div>`;
            document.body.appendChild(overlay);
            if (typeof idOrOpts === 'object' && idOrOpts.actions) {
                overlay.querySelectorAll('[data-action]').forEach(btn => {
                    const idx = parseInt(btn.getAttribute('data-action'));
                    const action = idOrOpts.actions[idx];
                    if (action && action.onClick) btn.addEventListener('click', action.onClick);
                    else if (action && !action.primary) btn.addEventListener('click', () => closeModal(id));
                });
            }
            requestAnimationFrame(() => overlay.classList.add('show'));
            return overlay;
        }
        const WORKBENCH_TEMPLATES = KAGUYA_APP_DATA.workbenchTemplates || [];

        const _loadedTabs = new Set(['chats']);
        function ensureTabLoaded(tabId) {
            if (_loadedTabs.has(tabId)) return;
            _loadedTabs.add(tabId);
            const loaders = {
                'knowledge': () => loadRagDocuments(),
                'loras': () => loadLoraList(),
                'tools': () => { renderToolList(); },
                'roles': () => renderRoleList(),
                'scenes': () => initScenesCenter(),
                'memory': () => { refreshMemoryStats(); searchMemories(); },
                'finetune': () => { loadFinetuneDatasets(); loadFinetuneJobs(); },
                'mcp': () => loadMcpPlugins(),
                'workflow': () => loadWorkflows(),
                'console': () => loadProjectCenter(),
                'ecosystem': () => loadProjectCenter(),
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

        function generateDeviceId(){let stored=localStorage.getItem('kaguya_device_id');if(stored)return stored;const nav=window.navigator;const scr=window.screen;const raw=[nav.userAgent,nav.language,scr.width+'x'+scr.height,scr.colorDepth,new Date().getTimezoneOffset(),nav.hardwareConcurrency||0,nav.platform||''].join('|');let hash=0;for(let i=0;i<raw.length;i++){const c=raw.charCodeAt(i);hash=((hash<<5)-hash)+c;hash|=0;}const id='dev_'+Math.abs(hash).toString(36)+'_'+Date.now().toString(36);localStorage.setItem('kaguya_device_id',id);return id;}

        function init() {
            try {
                if (settings.dark) document.body.classList.add('dark');
                const darkModeToggle = $('darkModeToggle');
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
                const kbSearchEl = $('kbSearch');
                if (kbSearchEl) kbSearchEl.addEventListener('input', searchKB);
                renderChatList();
                updateStats();
                updateApiIndicator();
                hydrateSavedApiConfig()
                    .catch(function(e) { console.warn('Saved API config hydration failed:', e); })
                    .finally(function() { checkExternalApiWarning(); });
                if (chats.length > 0) loadChat(chats[0].id);
                else showWelcome();
                document.querySelector('.sidebar-tabs')?.addEventListener('click', e => {
                    const tab = e.target.closest('.sidebar-tab');
                    if (tab && tab.dataset.tab) switchTab(tab.dataset.tab, tab);
                });
                // Mark app as ready after initialization
                setTimeout(()=>{window.kaguyaAppReady=true;}, 3000);
            } catch (e) {
                console.error('Init error:', e);
            }
        }

function showWelcome() {
            const container = $('messagesContainer');
            container.innerHTML = `
                <div class="welcome-container">
                    <img src="/welcome-img" class="welcome-avatar">
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
            loadSceneHistory();
        }

        function filterSceneByCategory(cat) {
            currentSceneCategory = cat;
            document.querySelectorAll('.scene-cat-btn').forEach(b => b.classList.remove('active'));
            const activeBtn = document.querySelector(`.scene-cat-btn[data-cat="${cat}"]`);
            if (activeBtn) activeBtn.classList.add('active');
            renderSceneNav();
        }

        function renderSceneNav() {
            const el = document.getElementById('sceneNav');
            if (!el) return;
            let ids = Object.keys(SCENE_UI_CONFIG);
            if (currentSceneCategory !== 'all') {
                ids = ids.filter(id => SCENE_UI_CONFIG[id].category === currentSceneCategory);
            }
            let catHtml = '<div class="scene-cat-bar">';
            for (const [catId, catInfo] of Object.entries(SCENE_CATEGORIES)) {
                catHtml += `<button class="scene-cat-btn ${catId === currentSceneCategory ? 'active' : ''}" data-cat="${catId}" onclick="filterSceneByCategory('${catId}')">${catInfo.icon} ${catInfo.label}</button>`;
            }
            catHtml += '</div>';
            let navHtml = ids.map(id => {
                const item = SCENE_UI_CONFIG[id];
                return `<div class="scene-nav-item ${id === currentSceneId ? 'active' : ''}" onclick="renderSceneWorkspace('${id}')"><div class="scene-nav-title">${item.icon} ${escapeHtml(item.title)}</div><div class="scene-nav-desc">${item.desc}</div></div>`;
            }).join('');
            el.innerHTML = catHtml + navHtml;
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
            let fieldsHtml = item.fields.map(f => {
                const inputTag = f.type === 'textarea'
                    ? `<textarea id="sceneField_${f.key}" rows="${f.rows || 2}" placeholder="${f.placeholder || ''}"></textarea>`
                    : `<input id="sceneField_${f.key}" placeholder="${f.placeholder || ''}">`;
                return `<div class="scene-form-field ${f.full ? 'full' : ''}"><label>${f.required ? '<span style="color:var(--primary)">*</span> ' : ''}${f.label}</label>${inputTag}</div>`;
            }).join('');
            el.innerHTML = `
                <div class="scene-form-title"><span>${item.icon}</span><span>${escapeHtml(item.title)}子界面</span></div>
                <div class="scene-form-desc">${item.desc} (External API required)</div>
                <div class="scene-form-grid">${fieldsHtml}</div>
                <div class="scene-actions">
                    <button class="scene-generate-btn" id="sceneGenerateBtn" onclick="generateSceneContent('${sceneId}')">⚡ 一键生成</button>
                    <button class="project-mini-btn" onclick="fillScenePreset('${sceneId}')">📋 填入示例</button>
                    <button class="project-mini-btn" onclick="clearSceneForm('${sceneId}')">🗑️ 清空表单</button>
                    <button class="project-mini-btn" onclick="copySceneOutput()">📋 复制结果</button>
                    <button class="project-mini-btn" onclick="sendSceneToChat()">💬 发送到聊天</button>
                    <button class="project-mini-btn" onclick="toggleSceneHistory()">📜 历史记录</button>
                </div>
                <div class="scene-output" id="sceneOutput">点击「一键生成」后，这里会返回外界API生成结果。</div>
                <div class="scene-history-panel" id="sceneHistoryPanel" style="display:none;"></div>
            `;
        }

        function fillScenePreset(sceneId) {
            const item = SCENE_UI_CONFIG[sceneId];
            if (!item || !item.preset) { showToast('该场景暂无示例数据'); return; }
            item.fields.forEach(f => {
                const el = document.getElementById('sceneField_' + f.key);
                if (el) el.value = item.preset[f.key] || '';
            });
            showToast('已填入示例数据');
        }

        function clearSceneForm(sceneId) {
            const item = SCENE_UI_CONFIG[sceneId];
            if (!item) return;
            item.fields.forEach(f => {
                const el = document.getElementById('sceneField_' + f.key);
                if (el) el.value = '';
            });
            const outputEl = document.getElementById('sceneOutput');
            if (outputEl) outputEl.textContent = '点击「一键生成」后，这里会返回外界API生成结果。';
            showToast('表单已清空');
        }

        function generateSceneContent(sceneId) {
            const provider = syncSceneConfigFromInputs();
            const item = SCENE_UI_CONFIG[sceneId];
            if (!item) return;
            const fields = {};
            let hasRequired = false;
            item.fields.forEach(f => {
                const el = document.getElementById('sceneField_' + f.key);
                const val = el ? el.value.trim() : '';
                fields[f.key] = val;
                if (f.required && !val) hasRequired = true;
            });
            if (hasRequired) { showToast('Please fill in required fields (marked with *)'); return; }
            const outputEl = document.getElementById('sceneOutput');
            const btn = document.getElementById('sceneGenerateBtn');
            if (btn) btn.disabled = true;
            if (outputEl) outputEl.innerHTML = '<div class="scene-loading">⏳ 外界API正在生成中，请稍候...</div>';
            if (!window.KaguyaAPI) {
                if (outputEl) outputEl.textContent = '生成失败：API client unavailable';
                if (btn) btn.disabled = false;
                return;
            }
            window.KaguyaAPI.json('/external/config', {active_provider: provider, providers: externalApiConfig.providers || {}, device_id: generateDeviceId()}).then((configData) => {
                if (configData && configData.success === false) throw new Error(configData.message || configData.error || '配置保存失败');
                window.KaguyaAPI.json('/scenes/generate', {scene_id: sceneId, provider, fields, device_id: generateDeviceId()}).then(data => {
                    if (!data.success) {
                        if (outputEl) outputEl.textContent = `生成失败：${data.message || data.error || '未知错误'}`;
                        if (btn) btn.disabled = false;
                        return;
                    }
                    if (outputEl) outputEl.innerHTML = renderSceneMarkdown(data.content || '');
                    if (btn) btn.disabled = false;
                    loadSceneHistory();
                }).catch(() => {
                    if (outputEl) outputEl.textContent = '生成失败：网络异常';
                    if (btn) btn.disabled = false;
                });
            }).catch((error) => {
                if (outputEl) outputEl.textContent = '生成失败：' + (error.message || '配置保存失败');
                if (btn) btn.disabled = false;
            });
        }

        function renderSceneMarkdown(text) {
            if (!text) return '';
            let html = escapeHtml(text);
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            html = html.replace(/^### (.+)$/gm, '<h4 class="scene-md-h">$1</h4>');
            html = html.replace(/^## (.+)$/gm, '<h3 class="scene-md-h">$1</h3>');
            html = html.replace(/^# (.+)$/gm, '<h2 class="scene-md-h">$1</h2>');
            html = html.replace(/^(\d+)\.\s/gm, '<span class="scene-md-num">$1.</span> ');
            html = html.replace(/^[-*]\s/gm, '<span class="scene-md-bullet">&bull;</span> ');
            html = html.replace(/\n\n/g, '</p><p>');
            html = html.replace(/\n/g, '<br>');
            html = '<p>' + html + '</p>';
            return html;
        }

        function copySceneOutput() {
            const el = document.getElementById('sceneOutput');
            if (!el) return;
            const text = el.textContent || '';
            if (!text.trim() || text.includes('点击')) return;
            navigator.clipboard.writeText(text).then(() => showToast('已复制场景结果'));
        }

        function sendSceneToChat() {
            const el = document.getElementById('sceneOutput');
            if (!el) return;
            const text = el.textContent || '';
            if (!text.trim() || text.includes('点击')) { showToast('请先生成场景结果'); return; }
            const item = SCENE_UI_CONFIG[currentSceneId];
            const chatInput = document.getElementById('mainInput');
            if (chatInput) {
                chatInput.value = `【${item ? item.title : '场景'}生成结果】${String.fromCharCode(10)}${String.fromCharCode(10)}${text}`;
                chatInput.focus();
            }
            const chatTab = document.querySelector('.sidebar-tab[data-tab="chat"]');
            if (chatTab) switchTab('chat', chatTab);
            showToast('已发送到聊天输入框');
        }

        function loadSceneHistory() {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.get('/scenes/history?scene_id=' + encodeURIComponent(currentSceneId)).then(data => {
                if (data.success) {
                    sceneHistoryList = data.history || [];
                    renderSceneHistoryPanel();
                }
            });
        }

        function toggleSceneHistory() {
            const panel = document.getElementById('sceneHistoryPanel');
            if (!panel) return;
            if (panel.style.display === 'none') {
                loadSceneHistory();
                panel.style.display = 'block';
            } else {
                panel.style.display = 'none';
            }
        }

        function renderSceneHistoryPanel() {
            const panel = document.getElementById('sceneHistoryPanel');
            if (!panel) return;
            if (!sceneHistoryList.length) {
                panel.innerHTML = '<div class="scene-history-empty">暂无历史记录</div>';
                return;
            }
            let html = '<div class="scene-history-header"><span>📜 生成历史</span><button class="project-mini-btn" onclick="clearSceneHistory()">清空</button></div>';
            sceneHistoryList.slice().reverse().forEach(h => {
                const item = SCENE_UI_CONFIG[h.scene_id];
                const title = item ? item.title : h.scene_id;
                const preview = (h.content || '').substring(0, 80).replace(/\n/g, ' ');
                html += `<div class="scene-history-item" onclick="loadSceneHistoryItem('${h.id}')">
                    <div class="scene-history-meta">${item ? item.icon : '📄'} ${escapeHtml(title)} · ${h.timestamp || ''} · ${h.model || ''}</div>
                    <div class="scene-history-preview">${escapeHtml(preview)}...</div>
                </div>`;
            });
            panel.innerHTML = html;
        }

        function loadSceneHistoryItem(id) {
            const item = sceneHistoryList.find(h => h.id === id);
            if (!item) return;
            const outputEl = document.getElementById('sceneOutput');
            if (outputEl) outputEl.innerHTML = renderSceneMarkdown(item.content || '');
            if (item.scene_id !== currentSceneId) {
                renderSceneWorkspace(item.scene_id);
                const outputEl2 = document.getElementById('sceneOutput');
                if (outputEl2) outputEl2.innerHTML = renderSceneMarkdown(item.content || '');
            }
            showToast('已加载历史记录');
        }

        function clearSceneHistory() {
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.del('/scenes/history').then(data => {
                if (data.success) {
                    sceneHistoryList = [];
                    renderSceneHistoryPanel();
                    showToast('历史记录已清空');
                } else {
                    showToast('清空失败: ' + (data.message || data.error || '未知错误'), 'error');
                }
            });
        }

        function handleSceneProviderChange(provider) {
            if (!provider) return;
            externalApiConfig.active_provider = provider;
            const cfg = (externalApiConfig.providers && externalApiConfig.providers[provider]) ? externalApiConfig.providers[provider] : {api_url: '', api_key: '', model: ''};
            const urlEl = $('sceneApiUrlInput');
            const keyEl = $('sceneApiKeyInput');
            const modelEl = $('sceneModelInput');
            if (urlEl) urlEl.value = cfg.api_url || '';
            if (keyEl) keyEl.value = cfg.api_key || '';
            if (modelEl) modelEl.value = cfg.model || '';
        }

        function syncSceneConfigFromInputs() {
            const provider = $('sceneProviderSelect')?.value || 'deepseek';
            const api_url = ($('sceneApiUrlInput')?.value || '').trim();
            const api_key = ($('sceneApiKeyInput')?.value || '').trim();
            const model = ($('sceneModelInput')?.value || '').trim();
            if (!externalApiConfig.providers) externalApiConfig.providers = {};
            externalApiConfig.active_provider = provider;
            externalApiConfig.providers[provider] = {api_url, api_key, model};
            return provider;
        }

        function loadExternalApiConfig() {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.get('/external/config?device_id='+encodeURIComponent(generateDeviceId())).then(data => {
                if (!data.success) return;
                externalApiConfig = {active_provider: data.active_provider || 'deepseek', providers: data.providers || {}};
                const selectEl = $('sceneProviderSelect');
                if (selectEl) selectEl.value = externalApiConfig.active_provider || 'deepseek';
                handleSceneProviderChange(selectEl?.value || 'deepseek');
                const statusEl = document.getElementById('sceneApiStatus');
                if (statusEl) statusEl.textContent = `已加载Provider: ${externalApiConfig.active_provider || 'deepseek'}`;
            });
        }

        function saveExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            if (!window.KaguyaAPI) {
                if (statusEl) statusEl.textContent = '保存失败: API client unavailable';
                return;
            }
            window.KaguyaAPI.json('/external/config', {active_provider: provider, providers: externalApiConfig.providers || {}, device_id: generateDeviceId()}).then(data => {
                if (!data.success) {
                    if (statusEl) statusEl.textContent = `保存失败: ${data.message || data.error || '未知错误'}`;
                    return;
                }
                if (statusEl) statusEl.textContent = `保存成功，当前Provider: ${provider}`;
                showToast('外界API配置已保存');
            }).catch(() => {
                if (statusEl) statusEl.textContent = '保存失败: 网络异常';
            });
        }

        function testExternalApiConfig() {
            const provider = syncSceneConfigFromInputs();
            const statusEl = document.getElementById('sceneApiStatus');
            const did = generateDeviceId();
            if (!window.KaguyaAPI) {
                if (statusEl) statusEl.textContent = '连通失败: API client unavailable';
                return;
            }
            window.KaguyaAPI.json('/external/config', {active_provider: provider, providers: externalApiConfig.providers || {}, device_id: did}).then((configData) => {
                if (configData && configData.success === false) throw new Error(configData.message || configData.error || '配置保存失败');
                window.KaguyaAPI.json('/external/test', {provider, device_id: did}).then(data => {
                    if (!data.success) {
                        if (statusEl) statusEl.textContent = `连通失败: ${data.message || data.error || '未知错误'}`;
                        return;
                    }
                    if (statusEl) statusEl.textContent = `连通成功: ${data.provider} / ${data.message || ''}`;
                    showToast('外界API连通成功');
                });
            }).catch((error) => {
                if (statusEl) statusEl.textContent = '连通失败: ' + (error.message || '网络异常');
            });
        }


        function openSceneFromQuickAction(sceneId) {
            const target = document.querySelector(`.sidebar-tab[onclick*="scenes"]`);
            if (target) switchTab('scenes', target);
            renderSceneWorkspace(sceneId);
            showToast(`已切换到${SCENE_UI_CONFIG[sceneId]?.title || '场景'}子界面`);
        }

        function quickAction(type) {
            const sceneIds = Object.keys(SCENE_UI_CONFIG);
            if (sceneIds.includes(type)) {
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
            const input = $('mainInput');
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
                    $('mainInput').value = t;
                    updateCharCount();
                };
                recognition.onend = () => {
                    isRecording = false;
                    document.getElementById('voiceInputBtn').classList.remove('active');
                };
            }
        }
        
        function toggleVoiceInput() {
            if (!recognition) initSpeechRecognition();
            if (!recognition) { showToast('浏览器不支持语音输入'); return; }
            if (isRecording) { recognition.stop(); return; }
            isRecording = true;
            document.getElementById('voiceInputBtn').classList.add('active');
            recognition.start();
        }
        
        function saveSettings() { debouncedSaveLS('kaguya_settings', settings); }
        function saveStats() { debouncedSaveLS('kaguya_stats', stats); }
        function saveChats() { localStorage.setItem('kaguya_chats', JSON.stringify(chats)); renderChatList(); }
        
        function showLoraHelp() {
            document.getElementById('loraHelpModal').classList.add('show');
        }
        
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
                    <span class="chat-item-title">${escapeHtml(c.title || '新对话')}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
            document.getElementById('chatList').innerHTML = html;
        }
        
        let currentRoleCategory = 'all';

        function filterRoleCategory(cat) {
            currentRoleCategory = cat;
            document.querySelectorAll('[data-role-cat]').forEach(b => b.classList.remove('active'));
            const activeBtn = document.querySelector(`[data-role-cat="${cat}"]`);
            if (activeBtn) activeBtn.classList.add('active');
            if (document.getElementById('rolesTab')?.classList.contains('active')) renderRoleList();
        }

        function renderRoleList() {
            let filtered = roles;
            if (currentRoleCategory !== 'all') {
                filtered = roles.filter(r => (r.category || r.type || 'general') === currentRoleCategory);
            }
            const categoryLabels = {character: '🎭 角色卡', general: '🤖 通用', professional: '💼 专业', creative: '✨ 创意', companion: '💚 陪伴'};
            const categoryColors = {character: 'linear-gradient(135deg,#a855f7,#7c3aed)', general: 'linear-gradient(135deg,#667eea,#5a67d8)', professional: 'linear-gradient(135deg,#0ea5e9,#0284c7)', creative: 'linear-gradient(135deg,#ec4899,#db2777)', companion: 'linear-gradient(135deg,#10b981,#059669)'};
            let html = '';
            if (currentRoleCategory === 'all') {
                const groups = {};
                filtered.forEach(r => {
                    const cat = r.category || r.type || 'general';
                    if (!groups[cat]) groups[cat] = [];
                    groups[cat].push(r);
                });
                for (const [cat, items] of Object.entries(groups)) {
                    const label = categoryLabels[cat] || cat;
                    html += `<div class="role-group"><div class="role-group-title">${label}</div>`;
                    html += items.map(r => buildRoleItemHtml(r, categoryColors)).join('');
                    html += '</div>';
                }
            } else {
                html += filtered.map(r => buildRoleItemHtml(r, categoryColors)).join('');
            }
            const el = document.getElementById('roleList');
            if (el) el.innerHTML = html;
        }

        function buildRoleItemHtml(r, categoryColors) {
            const icon = r.icon || '🎭', color = r.color || '#667eea';
            const cat = r.category || r.type || 'general';
            const badgeBg = categoryColors[cat] || categoryColors.general;
            const badgeLabel = {character: '角色', general: '通用', professional: '专业', creative: '创意', companion: '陪伴'}[cat] || cat;
            return `<div class="role-item ${r.id === currentRole ? 'active' : ''}" onclick="selectRole('${r.id}')">
                <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${r.avatar && r.avatar.startsWith('/') ? `<img src="${r.avatar}" style="width:100%;height:100%;border-radius:8px;">` : icon}</div>
                <div class="item-info"><div class="item-name">${escapeHtml(r.name)}</div><div class="item-desc">${escapeHtml(r.description)}</div></div>
                <span class="role-type-badge" style="background:${badgeBg};">${badgeLabel}</span>
            </div>`;
        }

        function showRoleHelp() {
            showToast('选择角色风格后，AI将以该角色的语气和方式回复你');
        }
        
        function renderToolList() {
            document.getElementById('toolList').innerHTML = Object.entries(tools).map(([id, t]) => `
                <div class="tool-item ${activeTools.has(id) ? 'active' : ''}" onclick="toggleTool('${id}')">
                    <div class="item-icon" style="background:linear-gradient(135deg,#f59e0b,#d97706);">${t.icon}</div>
                    <div class="item-info"><div class="item-name">${escapeHtml(t.name)}</div><div class="item-desc">${escapeHtml(t.description)}</div></div>
                    ${activeTools.has(id) ? '<span class="item-badge" style="background:#f59e0b;">已启用</span>' : ''}
                </div>
            `).join('');
        }
        
        function loadLoraList() {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.get('/lora/list').then(data => {
                document.getElementById('loraList').innerHTML = (data.loras || []).map(l => {
                    const icon = l.icon || '🤖', color = l.color || '#10b981';
                    return `<div class="lora-item ${l.id === currentLora ? 'active' : ''}" onclick="selectLora('${l.id}')">
                        <div class="item-icon" style="background:linear-gradient(135deg,${color},${color}dd);">${icon}</div>
                        <div class="item-info"><div class="item-name">${escapeHtml(l.name)}</div><div class="item-desc">${escapeHtml(l.description)}</div></div>
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
        
        function openWebSearch() {
            var panel = document.getElementById('webSearchPanel');
            if (panel.style.display === 'none') {
                panel.style.display = '';
                document.getElementById('webSearchInput').focus();
            } else {
                panel.style.display = 'none';
            }
        }
        
        function closeWebSearch() {
            document.getElementById('webSearchPanel').style.display = 'none';
        }
        
        function quickWebSearch(query) {
            document.getElementById('webSearchInput').value = query;
            doWebSearch();
        }
        
        function doWebSearch() {
            var query = document.getElementById('webSearchInput').value.trim();
            if (!query) { showToast('请输入搜索关键词'); return; }
            
            var btn = document.getElementById('webSearchBtn');
            var resultsDiv = document.getElementById('webSearchResults');
            var previewDiv = document.getElementById('webPreviewPanel');
            
            btn.disabled = true;
            btn.textContent = '搜索中...';
            previewDiv.innerHTML = '';
            resultsDiv.innerHTML = '<div class="web-search-status">🔍 正在搜索: ' + escapeHtml(query) + '...</div>';
            
            if (!window.KaguyaAPI) {
                btn.disabled = false;
                btn.textContent = '🔍 搜索';
                resultsDiv.innerHTML = '<div class="web-search-status">API client unavailable</div>';
                return;
            }
            window.KaguyaAPI.json('/web/search', {query: query, max_results: 10}).then(function(data) {
                btn.disabled = false;
                btn.textContent = '🔍 搜索';
                
                if (data.success && data.results && data.results.length > 0) {
                    window._webSearchResults = data.results;
                    resultsDiv.innerHTML = '<div class="web-search-status">找到 ' + data.count + ' 条结果</div>' +
                        data.results.map(function(r, i) {
                            return '<div class="web-result-card" data-idx="' + i + '" onclick="previewWebPage(' + i + ')">' +
                                '<div class="web-result-title">' + escapeHtml(r.title) + '</div>' +
                                (r.snippet ? '<div class="web-result-snippet">' + escapeHtml(r.snippet) + '</div>' : '') +
                                '<div class="web-result-url">' + escapeHtml(r.url) + '</div>' +
                                '<div class="web-result-actions">' +
                                    '<button class="web-result-action-btn" onclick="event.stopPropagation();previewWebPage(' + i + ')">📖 预览</button>' +
                                    '<button class="web-result-action-btn" onclick="event.stopPropagation();sendToChat(' + i + ')">💬 发送到对话</button>' +
                                    '<button class="web-result-action-btn" onclick="event.stopPropagation();window.open(window._webSearchResults[' + i + '].url)">🔗 打开</button>' +
                                '</div>' +
                            '</div>';
                        }).join('');
                } else {
                    resultsDiv.innerHTML = '<div class="web-search-status">未找到相关结果，请尝试其他关键词</div>';
                }
            }).catch(function(err) {
                btn.disabled = false;
                btn.textContent = '🔍 搜索';
                resultsDiv.innerHTML = '<div class="web-search-status">搜索失败，请检查网络连接</div>';
            });
        }
        
        function previewWebPage(idx) {
            var r = window._webSearchResults[idx];
            if (!r) return;
            var url = r.url;
            var title = r.title;
            var previewDiv = document.getElementById('webPreviewPanel');
            previewDiv.innerHTML = '<div class="web-preview-panel"><div class="web-search-status">📖 正在加载页面内容...</div></div>';
            
            if (!window.KaguyaAPI) {
                previewDiv.innerHTML = '<div class="web-preview-panel"><div class="web-search-status">API client unavailable</div></div>';
                return;
            }
            window.KaguyaAPI.json('/web/fetch', {url: url}).then(function(data) {
                if (data.success && data.data && data.data.content) {
                    previewDiv.innerHTML = '<div class="web-preview-panel">' +
                        '<div class="web-preview-title">' + escapeHtml(data.data.title || title) + '</div>' +
                        '<div class="web-preview-url">' + escapeHtml(url) + '</div>' +
                        '<div class="web-preview-content">' + escapeHtml(data.data.content) + '</div>' +
                        '<div style="margin-top:10px;display:flex;gap:6px;">' +
                            '<button class="web-result-action-btn" onclick="sendToChat(' + idx + ')">💬 发送到对话</button>' +
                            '<button class="web-result-action-btn" onclick="window.open(window._webSearchResults[' + idx + '].url)">🔗 在浏览器中打开</button>' +
                            '<button class="web-result-action-btn" onclick="document.getElementById(String.fromCharCode(119,101,98,80,114,101,118,105,101,119,80,97,110,101,108)).innerHTML=String()">✕ 关闭预览</button>' +
                        '</div>' +
                    '</div>';
                } else {
                    previewDiv.innerHTML = '<div class="web-preview-panel"><div class="web-search-status">无法加载页面内容</div></div>';
                }
            }).catch(function() {
                previewDiv.innerHTML = '<div class="web-preview-panel"><div class="web-search-status">加载失败</div></div>';
            });
        }
        
        function sendToChat(idx) {
            var r = window._webSearchResults[idx];
            if (!r) return;
            var msg = '请帮我分析以下网页内容：' + r.title + ' ' + r.url;
            document.getElementById('messageInput').value = msg;
            closeWebSearch();
            document.getElementById('messageInput').focus();
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
                if (role.avatar && role.avatar.startsWith('/')) document.getElementById('headerAvatar').src = role.avatar;
            }
            renderRoleList();
            showToast(`已切换到 ${role ? role.name : id}`);
        }
        
        function selectLora(id) {
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/lora/load', {lora_id: id}).then(data => {
                if (data.success) {
                    currentLora = id;
                    loadLoraList();
                    updateIndicators();
                    showToast(data.message || 'LoRA已切换');
                } else showToast('加载失败: ' + (data.error || '未知错误'));
            });
        }
        
        // Learning, multimodal vision, and memory panels live in kaguya-learning-panels.js.

const PROMPT_TEMPLATES = KAGUYA_APP_DATA.promptTemplates || [];
        
        const PROMPT_FAVORITES = JSON.parse(localStorage.getItem('promptFavorites') || '[]');
        const PROMPT_USAGE = JSON.parse(localStorage.getItem('promptUsage') || '{}');
        const CUSTOM_TEMPLATES = JSON.parse(localStorage.getItem('customTemplates') || '[]');

        function savePromptFavorites() { localStorage.setItem('promptFavorites', JSON.stringify(PROMPT_FAVORITES)); }
        function savePromptUsage() { localStorage.setItem('promptUsage', JSON.stringify(PROMPT_USAGE)); }
        function saveCustomTemplates() { localStorage.setItem('customTemplates', JSON.stringify(CUSTOM_TEMPLATES)); }

        function getAllTemplates() { return [...PROMPT_TEMPLATES, ...CUSTOM_TEMPLATES]; }

        function renderPromptList() {
            const groups = {
                general: '🤖 通用助手',
                growth: '📈 增长运营',
                engineering: '⚙️ 工程治理',
                knowledge: '📚 知识研究',
                professional: '💼 专业服务',
                product: '📱 产品设计'
            };
            const allTpls = getAllTemplates();
            let filtered;
            if (promptCategory === 'favorites') {
                filtered = allTpls.filter(p => PROMPT_FAVORITES.includes(p.id));
            } else if (promptCategory === 'custom') {
                filtered = CUSTOM_TEMPLATES;
            } else {
                filtered = allTpls.filter(p => {
                    const hitCategory = promptCategory === 'all' || p.category === promptCategory;
                    const q = promptSearchKeyword.trim().toLowerCase();
                    const hitKeyword = !q || `${p.name} ${p.desc} ${p.source} ${(p.tags||[]).join(' ')} ${p.prompt}`.toLowerCase().includes(q);
                    return hitCategory && hitKeyword;
                });
            }
            const list = document.getElementById('promptList');
            const statsTotal = document.getElementById('promptStatsTotal');
            const statsFiltered = document.getElementById('promptStatsFiltered');
            if (statsTotal) statsTotal.textContent = allTpls.length + ' 个模板';
            if (statsFiltered && promptSearchKeyword) {
                statsFiltered.style.display = 'inline';
                statsFiltered.textContent = '/ 筛选: ' + filtered.length;
            } else if (statsFiltered) {
                statsFiltered.style.display = 'none';
            }
            if (!filtered.length) {
                list.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">' +
                    (promptCategory === 'favorites' ? '<div style="font-size:32px;margin-bottom:8px;">⭐</div><div>暂无收藏模板，点击卡片上的星标收藏</div>' :
                     promptCategory === 'custom' ? '<div style="font-size:32px;margin-bottom:8px;">🔧</div><div>暂无自定义模板，点击"新建"创建</div>' :
                     '<div style="font-size:32px;margin-bottom:8px;">🔍</div><div>未找到匹配模板，试试更短关键词</div>') + '</div>';
                return;
            }
            let html = '';
            if (promptCategory === 'all' || (promptCategory !== 'favorites' && promptCategory !== 'custom')) {
                Object.keys(groups).forEach(groupKey => {
                    const groupItems = filtered.filter(x => x.category === groupKey);
                    if (!groupItems.length) return;
                    html += `<div class="prompt-group-title">${groups[groupKey]} (${groupItems.length})</div>`;
                    html += `<div class="prompt-grid">${groupItems.map(p => renderPromptCard(p)).join('')}</div>`;
                });
                const uncategorized = filtered.filter(x => !groups[x.category]);
                if (uncategorized.length) {
                    html += `<div class="prompt-group-title">其他 (${uncategorized.length})</div>`;
                    html += `<div class="prompt-grid">${uncategorized.map(p => renderPromptCard(p)).join('')}</div>`;
                }
            } else {
                html += `<div class="prompt-grid">${filtered.map(p => renderPromptCard(p)).join('')}</div>`;
            }
            list.innerHTML = html;
        }

        function renderPromptCard(p) {
            const isFav = PROMPT_FAVORITES.includes(p.id);
            const isCustom = CUSTOM_TEMPLATES.some(c => c.id === p.id);
            return `<div class="prompt-card" onclick="usePromptTemplate('${p.id}')">
                <button class="prompt-fav-btn ${isFav ? 'is-fav' : ''}" onclick="event.stopPropagation();toggleFavorite('${p.id}')" title="${isFav ? '取消收藏' : '收藏'}">${isFav ? '★' : '☆'}</button>
                <div class="prompt-head">
                    <span style="font-size:18px;">${p.icon || '📝'}</span>
                    <span class="prompt-name">${escapeHtml(p.name)}</span>
                </div>
                <div class="prompt-desc">${escapeHtml(p.desc)}</div>
                <div class="prompt-meta">
                    ${(p.tags||[]).map(t => `<span class="prompt-meta-tag">${escapeHtml(t)}</span>`).join('')}
                    ${p.template ? '<span class="prompt-meta-tag cat-tag">结构化</span>' : ''}
                    ${isCustom ? '<span class="prompt-meta-tag" style="background:rgba(245,158,11,0.1);color:#f59e0b;">自定义</span>' : ''}
                    ${p.source ? `<span style="font-size:9px;color:var(--text-muted);margin-left:auto;">${escapeHtml(p.source)}</span>` : ''}
                </div>
            </div>`;
        }
        
        function setPromptSearch(value) {
            promptSearchKeyword = value || '';
            renderPromptList();
        }
        
        function setPromptCategory(category) {
            promptCategory = category;
            document.querySelectorAll('.prompt-chip').forEach(el => el.classList.remove('active'));
            const idMap = {all:'promptCatAll',general:'promptCatGeneral',growth:'promptCatGrowth',engineering:'promptCatEngineering',knowledge:'promptCatKnowledge',professional:'promptCatProfessional',product:'promptCatProduct',favorites:'promptCatFavorites',custom:'promptCatCustom'};
            const activeEl = document.getElementById(idMap[category] || 'promptCatAll');
            if (activeEl) activeEl.classList.add('active');
            renderPromptList();
        }
        
        function openPromptWorkbench() {
            const existing = document.getElementById('promptWorkbenchModal');
            if (existing) existing.remove();
            
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'promptWorkbenchModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('promptWorkbenchModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:860px;width:95%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;border-radius:16px 16px 0 0;flex-shrink:0;">
                        <h3 style="margin:0;">🧭 专业工作台</h3>
                        <button class="modal-close" onclick="closeModal('promptWorkbenchModal')" style="color:white;font-size:18px;">×</button>
                    </div>
                    <div style="flex:1;overflow:hidden;display:flex;flex-direction:column;padding:0;">
                        <div style="padding:14px 16px 0;flex-shrink:0;">
                            <div class="workbench-tabs" style="margin-bottom:12px;">
                                <button class="workbench-tab active" onclick="switchWorkbenchTab('all', this)">📋 全部</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('code', this)">💻 代码</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('doc', this)">📄 文档</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('data', this)">📊 数据</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('favorites', this)">⭐ 收藏</button>
                                <button class="workbench-tab" onclick="switchWorkbenchTab('integrations', this)">🔗 接入</button>
                            </div>
                            <input class="project-input" id="workbenchSearch" placeholder="🔍 搜索模板、场景、工具..." style="width:100%;margin-bottom:12px;" oninput="filterWorkbenchTemplates()">
                        </div>
                        <div id="workbenchContent" style="flex:1;overflow-y:auto;padding:0 16px 16px;"></div>
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
            
            const allTemplates = getAllTemplates();
            let templates;
            if (category === 'all') {
                templates = allTemplates;
            } else if (category === 'favorites') {
                templates = allTemplates.filter(t => PROMPT_FAVORITES.includes(t.id));
            } else if (category === 'code') {
                templates = allTemplates.filter(t => t.category === 'engineering' || (t.tags && t.tags.some(tag => ['代码','审查','重构','测试','API','SQL','安全'].includes(tag))));
            } else if (category === 'doc') {
                templates = allTemplates.filter(t => t.category === 'general' || (t.tags && t.tags.some(tag => ['写作','文档','翻译','邮件','报告','创作'].includes(tag))));
            } else if (category === 'data') {
                templates = allTemplates.filter(t => t.category === 'product' || (t.tags && t.tags.some(tag => ['数据','分析','A/B','实验','统计'].includes(tag))));
            } else {
                templates = allTemplates.filter(t => t.category === category);
            }
            
            const categoryColors = { general: '#667eea', growth: '#10b981', engineering: '#3b82f6', knowledge: '#f59e0b', professional: '#ec4899', product: '#8b5cf6', code: '#3b82f6', doc: '#10b981', data: '#f59e0b' };
            
            container.innerHTML = templates.map(t => {
                const catClass = t.category || 'general';
                const catColor = categoryColors[catClass] || '#667eea';
                const isFav = PROMPT_FAVORITES.includes(t.id);
                return `
                <div class="workbench-card" onclick="applyWorkbenchTemplate('${t.id}')">
                    <div class="card-icon ${catClass}">${t.icon || '📝'}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                            <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${escapeHtml(t.name)}</span>
                            ${(t.tags||[]).map(tag => `<span style="font-size:9px;padding:1px 6px;border-radius:4px;background:${catColor}15;color:${catColor};font-weight:500;">${tag}</span>`).join('')}
                        </div>
                        <div style="font-size:12px;color:var(--text-muted);line-height:1.4;">${escapeHtml(t.desc)}</div>
                    </div>
                    <button onclick="event.stopPropagation();toggleFavorite('${t.id}')" style="background:none;border:none;font-size:16px;cursor:pointer;padding:4px;opacity:${isFav ? '1' : '0.5'};transition:opacity 0.2s;color:${isFav ? '#f59e0b' : 'inherit'};" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='${isFav ? '1' : '0.5'}'">${isFav ? '★' : '☆'}</button>
                </div>
            `}).join('') || '<div style="text-align:center;color:var(--text-muted);padding:40px;">暂无模板</div>';
        }

        function renderIntegrationsPage(container) {
            const integrations = [
                { id: 'mcp', name: 'MCP 协议', icon: '🤖', desc: 'Model Context Protocol 接入，支持工具调用和资源访问', status: 'active', color: '#8b5cf6', version: 'v1.2' },
                { id: 'rag', name: '知识库接入', icon: '📚', desc: 'RAG 检索增强生成，支持多种向量数据库', status: 'active', color: '#ec4899', version: 'v2.0' },
                { id: 'api', name: 'API 接入', icon: '🔌', desc: '配置外部 API 服务接入 (OpenAI/Claude/Gemini)', status: 'available', color: '#667eea', version: 'v1.0' },
                { id: 'database', name: '数据库连接', icon: '🗄️', desc: '连接 MySQL、PostgreSQL、MongoDB 等数据库', status: 'available', color: '#10b981', version: 'v1.1' },
                { id: 'webhook', name: 'Webhook', icon: '🔗', desc: '配置 Webhook 回调地址，实现事件通知', status: 'available', color: '#f59e0b', version: 'v1.0' },
                { id: 'tools', name: '工具调用', icon: '🔧', desc: '外部工具和函数调用，扩展 AI 能力', status: 'available', color: '#06b6d4', version: 'v1.3' },
                { id: 'plugins', name: '插件系统', icon: '🧩', desc: '管理和配置插件，扩展系统功能', status: 'available', color: '#84cc16', version: 'v0.9' },
                { id: 'oauth', name: 'OAuth 认证', icon: '🔐', desc: '第三方 OAuth 登录接入', status: 'available', color: '#f43f5e', version: 'v1.0' },
            ];
            
            container.innerHTML = `
                <div style="margin-bottom:20px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                        <span style="font-size:14px;font-weight:600;color:var(--text-primary);">已启用</span>
                        <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#10b98115;color:#10b981;font-weight:500;">${integrations.filter(i => i.status === 'active').length}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'active').map(i => `
                            <div class="integration-card active" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:linear-gradient(135deg,${i.color}12,${i.color}05);border:2px solid ${i.color}40;border-radius:12px;cursor:pointer;transition:all 0.2s;position:relative;overflow:hidden;">
                                <div style="position:absolute;top:8px;right:8px;font-size:9px;padding:2px 6px;border-radius:4px;background:${i.color}20;color:${i.color};">${i.version}</div>
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;line-height:1.4;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:6px;height:6px;background:#10b981;border-radius:50%;animation:pulse 2s infinite;"></span>
                                    <span style="font-size:10px;color:#10b981;font-weight:500;">运行中</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div>
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                        <span style="font-size:14px;font-weight:600;color:var(--text-primary);">可接入的服务</span>
                        <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:var(--bg-secondary);color:var(--text-muted);font-weight:500;">${integrations.filter(i => i.status === 'available').length}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;">
                        ${integrations.filter(i => i.status === 'available').map(i => `
                            <div class="integration-card" onclick="openIntegrationDetail('${i.id}')" style="padding:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all 0.2s;position:relative;">
                                <div style="position:absolute;top:8px;right:8px;font-size:9px;padding:2px 6px;border-radius:4px;background:var(--bg-primary);color:var(--text-muted);">${i.version}</div>
                                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                                    <span style="font-size:24px;">${i.icon}</span>
                                    <span style="font-size:14px;font-weight:600;color:var(--text-primary);">${i.name}</span>
                                </div>
                                <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;line-height:1.4;">${i.desc}</div>
                                <div style="display:flex;align-items:center;gap:6px;">
                                    <span style="width:6px;height:6px;background:var(--text-muted);border-radius:50%;opacity:0.5;"></span>
                                    <span style="font-size:10px;color:var(--text-muted);">点击配置</span>
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
            const item = getAllTemplates().find(t => t.id === templateId);
            if (!item) return;
            const template = { name: item.name, icon: item.icon || '📝', prompt: item.prompt, steps: ['输入内容', 'AI分析', '生成结果', '优化建议'] };
            PROMPT_USAGE[templateId] = (PROMPT_USAGE[templateId] || 0) + 1;
            savePromptUsage();
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
            $('mainInput').value = prompt;
            showToast('正在执行任务...');
            $('sendBtn').click();
        }

        function toggleFavorite(templateId) {
            const idx = PROMPT_FAVORITES.indexOf(templateId);
            if (idx >= 0) {
                PROMPT_FAVORITES.splice(idx, 1);
                showToast('已取消收藏');
            } else {
                PROMPT_FAVORITES.push(templateId);
                showToast('已收藏');
            }
            savePromptFavorites();
            renderPromptList();
        }

        function createCustomTemplate() {
            const existing = document.getElementById('customTemplateModal');
            if (existing) existing.remove();
            const modal = document.createElement('div');
            modal.className = 'modal-overlay show';
            modal.id = 'customTemplateModal';
            modal.onclick = function(e) { if (e.target === modal) closeModal('customTemplateModal'); };
            modal.innerHTML = `
                <div class="modal" style="max-width:520px;width:92%;max-height:85vh;display:flex;flex-direction:column;">
                    <div class="modal-header" style="flex-shrink:0;">
                        <h3 style="margin:0;">🔧 新建自定义模板</h3>
                        <button class="modal-close" onclick="closeModal('customTemplateModal')">×</button>
                    </div>
                    <div style="flex:1;overflow-y:auto;padding:16px 0;">
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">模板名称 *</label>
                            <input class="project-input" id="ctName" placeholder="例如：周报生成器" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">描述</label>
                            <input class="project-input" id="ctDesc" placeholder="简短描述模板用途" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">图标 (Emoji)</label>
                            <input class="project-input" id="ctIcon" placeholder="📝" value="📝" style="width:80px;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">分类</label>
                            <select class="project-input" id="ctCategory" style="width:100%;">
                                <option value="general">通用助手</option>
                                <option value="growth">增长运营</option>
                                <option value="engineering">工程治理</option>
                                <option value="knowledge">知识研究</option>
                                <option value="professional">专业服务</option>
                                <option value="product">产品设计</option>
                            </select>
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">标签 (逗号分隔)</label>
                            <input class="project-input" id="ctTags" placeholder="例如：周报,汇报" style="width:100%;">
                        </div>
                        <div style="margin-bottom:14px;">
                            <label style="font-size:11px;display:block;margin-bottom:4px;color:var(--text-muted);">提示词模板 *</label>
                            <textarea class="project-input" id="ctPrompt" placeholder="输入提示词模板内容，使用 {变量名} 表示可替换变量" style="width:100%;height:120px;resize:vertical;"></textarea>
                        </div>
                    </div>
                    <div style="display:flex;gap:10px;justify-content:flex-end;padding-top:12px;border-top:1px solid var(--border);flex-shrink:0;">
                        <button class="project-mini-btn" onclick="closeModal('customTemplateModal')">取消</button>
                        <button class="project-mini-btn" style="background:linear-gradient(135deg,var(--primary),#764ba2);color:white;" onclick="saveCustomTemplate()">保存模板</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        function saveCustomTemplate() {
            const name = document.getElementById('ctName').value.trim();
            const desc = document.getElementById('ctDesc').value.trim();
            const icon = document.getElementById('ctIcon').value.trim() || '📝';
            const category = document.getElementById('ctCategory').value;
            const tags = document.getElementById('ctTags').value.split(',').map(t => t.trim()).filter(Boolean);
            const prompt = document.getElementById('ctPrompt').value.trim();
            if (!name || !prompt) {
                showToast('请填写模板名称和提示词');
                return;
            }
            const id = 'custom_' + Date.now();
            CUSTOM_TEMPLATES.push({id, name, desc: desc || name, icon, category, tags, prompt, source: '自定义', custom: true});
            saveCustomTemplates();
            closeModal('customTemplateModal');
            renderPromptList();
            showToast('模板已保存');
        }

        // Template analytics and knowledge workbench live in kaguya-knowledge-workbench.js.

        function usePromptTemplate(templateId) {
            const item = getAllTemplates().find(x => x.id === templateId);
            if (!item) return;
            PROMPT_USAGE[templateId] = (PROMPT_USAGE[templateId] || 0) + 1;
            savePromptUsage();
            usePrompt(item.prompt, item.template || null);
        }
        
        function usePrompt(prompt, templateId = null) {
            try {
                const mainInput = $('mainInput');
                if (mainInput) { mainInput.value = prompt; }
                currentStructuredTemplate = templateId;
                if (typeof updateCharCount === 'function') updateCharCount();
            } catch(e) { console.error('usePrompt set value error:', e); }
            try {
                const chatsTab = document.querySelector('.sidebar-tab[onclick*="chats"]');
                if (chatsTab) switchTab('chats', chatsTab);
                setTimeout(function() {
                    var mi = document.getElementById('mainInput');
                    if (mi) { mi.focus(); }
                }, 100);
            } catch(e) { console.error('usePrompt switchTab error:', e); }
            showToast(templateId ? '已应用结构化模板' : '已填入模板');
        }
        
        // Security, auth, account, and project settings panels live in kaguya-admin-panels.js.

        // Project center, console, workspace, ops, release, alert, AB, and integration panels live in kaguya-project-center.js.

        function searchChats(query) {
            const filtered = chats.filter(c => 
                c.title.toLowerCase().includes(query.toLowerCase()) ||
                c.messages.some(m => m.content.toLowerCase().includes(query.toLowerCase()))
            );
            document.getElementById('chatList').innerHTML = filtered.map(c => `
                <div class="chat-item ${c.id === currentChatId ? 'active' : ''}" onclick="loadChat('${c.id}')">
                    <span>💬</span>
                    <span class="chat-item-title">${escapeHtml(c.title || '新对话')}</span>
                    <button class="chat-item-delete" onclick="event.stopPropagation();deleteChat('${c.id}')">🗑️</button>
                </div>
            `).join('');
        }
        
        let currentReader = null;
        let isGenerating = false;
        
        async function stopGeneration() {
            if (window.KaguyaAgent && window.KaguyaState && (window.KaguyaState.agentRunning || window.KaguyaState.currentAgentRunId || window.KaguyaState.currentAgentAbortController)) {
                try {
                    const result = await window.KaguyaAgent.stop();
                    if (result && result.error && result.error !== 'missing_run_id') {
                        showToast('停止 Agent 失败: ' + (result.message || result.error), 'error');
                    } else {
                        showToast(result && result.error === 'missing_run_id' ? '当前无活动 Agent 任务' : '已停止 Agent');
                    }
                } catch (e) {
                    showToast('停止 Agent 失败: ' + (e.message || e), 'error');
                }
            }
            if (currentReader) {
                currentReader.cancel();
                currentReader = null;
            }
            isGenerating = false;
            $('sendBtn').style.display = 'flex';
            $('stopBtn').style.display = 'none';
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
            $('messagesContainer').innerHTML = '';
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
            const input = $('mainInput');
            input.value = msg.content;
            input.focus();
            updateCharCount();
            document.getElementById('editHint').style.display = 'flex';
        }
        
        function cancelEdit() {
            editingMsgIdx = null;
            $('mainInput').value = '';
            document.getElementById('editHint').style.display = 'none';
            updateCharCount();
        }
        
        function replyToMessage(idx) {
            const chat = chats.find(c => c.id === currentChatId);
            if (!chat || !chat.messages[idx]) return;
            replyingTo = { idx, content: chat.messages[idx].content.slice(0, 100) };
            document.getElementById('replyHint').style.display = 'flex';
            document.getElementById('replyContent').textContent = replyingTo.content;
            $('mainInput').focus();
        }
        
        function cancelReply() {
            replyingTo = null;
            document.getElementById('replyHint').style.display = 'none';
        }
        
        function addMessageToUI(role, content, time = null, toolResults = null, msgIdx = null, reasoning = null) {
            const container = $('messagesContainer');
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
                            <span>💭 思考过程</span>
                        </div>
                        <div class="reasoning-content">${reasoning.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
                    </div>
                `;
            }
            
            const renderedContent = settings.markdown ? safeMarkedParse(content) : content.replace(/\n/g, '<br>');
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
            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
            safeHighlight(msg);
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
            $('mainInput').value = '';
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
            const activeApi=getActiveApiConfig();
            const apiLabel=activeApi?API_PROVIDERS[activeApi.provider]?.name||activeApi.provider:'未配置';
            const statusItems = [
                {label: 'AI 模型', value: activeApi?apiLabel+'已启用':'未配置', cls: activeApi?'ok':'warn'},
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
                        <span>${item.type} · ${escapeHtml(item.name)}</span>
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
            const tabMappings = ['console', 'ecosystem', 'scenes', 'prompts', 'project', 'workflow', 'memory', 'mcp', 'tools', 'knowledge', 'roles'];
            const nameMap = {
                console: '统一控制台',
                ecosystem: '项目生态',
                scenes: '场景引擎',
                prompts: '模板工作台',
                project: '项目中台',
                workflow: '工作流编排',
                memory: '记忆系统',
                mcp: 'MCP插件',
                tools: '工具箱',
                knowledge: '知识中心',
                models: '多模型API',
                settings: '系统设置',
                deepseek: 'DeepSeek配置',
                code: '代码执行器',
                stats: '统计仪表盘'
            };
            
            var actualTab = name;
            var subTab = null;
            if (['ops', 'release', 'alert', 'ab', 'integration'].includes(name)) { actualTab = 'project'; subTab = name; }
            if (name === 'multimodal') { actualTab = 'tools'; subTab = 'vision'; }
            if (['finetune', 'rag'].includes(name)) { actualTab = 'knowledge'; subTab = name; }
            if (name === 'roles') { actualTab = 'roles'; subTab = null; }
            
            if (tabMappings.includes(actualTab)) {
                const target = document.querySelector(`.sidebar-tab[onclick*="${actualTab}"]`);
                if (target) {
                    target.click();
                } else {
                    switchTab(actualTab, null);
                }
                if (subTab) {
                    setTimeout(function() {
                        if (actualTab === 'project') switchProjectSub(subTab, document.querySelector('#projectTab .memory-filter-btn[onclick*="' + subTab + '"]'));
                        if (actualTab === 'tools') switchToolsSub(subTab, document.querySelector('#toolsTab .memory-filter-btn[onclick*="' + subTab + '"]'));
                        if (actualTab === 'knowledge') switchKnowledgeSub(subTab, document.querySelector('#knowledgeTab .memory-filter-btn[onclick*="' + subTab + '"]'));
                    }, 200);
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
            const input = $('mainInput');
            let msg = input.value.trim();
            if (!msg && attachments.length === 0) return;
            if (msg.startsWith('/')) { executeCommand(msg.split(' ')[0]); return; }
            
            if (agentModeEnabled) {
                input.value = '';
                autoResize(input);
                updateCharCount();
                isGenerating = true;
                document.getElementById('sendBtn').disabled = true;
                document.getElementById('sendBtn').style.display = 'none';
                document.getElementById('stopBtn').style.display = 'flex';
                document.getElementById('statusText').textContent = 'Agent thinking...';
                await sendAgentMessage(msg);
                return;
            }
            
            const extApi=getActiveApiConfig();
            
            const sendBtn = $('sendBtn');
            const stopBtn = $('stopBtn');
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
                $('messagesContainer').innerHTML = '';
                chat.messages.forEach((m, idx) => addMessageToUI(m.role, m.content, m.time, m.toolResults, idx, m.reasoning));
                saveChats();
                
                const container = $('messagesContainer');
                const msgEl = document.createElement('div');
                msgEl.className = 'message assistant';
                const roleData = roles.find(r => r.id === currentRole) || roles[0];
                const replyTime = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
                msgEl.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content" id="streamContent"></div><div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div><div class="message-time">${replyTime}</div></div>`;
                container.appendChild(msgEl);
                const contentEl = document.getElementById('streamContent');
                let fullContent = '';
                
                if (!window.KaguyaStream) throw new Error('stream_helper_unavailable');
                await window.KaguyaStream.postSSE('/stream', {
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
                        rag_iterative: ragSettings.useIterative,
                        device_id: generateDeviceId(),
                        external_api: extApi
                    }, {
                    onReader: function(reader) { currentReader = reader; },
                    shouldStop: function() { return !currentReader; },
                    onFrame: function(data) {
                        if (data.content) {
                            fullContent += data.content;
                            contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
                            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                        }
                        if (data.done) {
                            if (settings.markdown) {
                                contentEl.innerHTML = safeMarkedParse(fullContent);
                            }
                            if (chat.messages[editingMsgIdx + 1]) {
                                chat.messages[editingMsgIdx + 1].content = fullContent;
                            } else {
                                chat.messages.push({ role: 'assistant', content: fullContent, time: replyTime });
                            }
                            if (history[histIdx]) history[histIdx][1] = fullContent;
                            saveChats();
                        }
                    },
                    onParseError: function(error, line) {
                        console.error('Parse error:', error, 'Line:', line);
                    }
                });
                currentReader = null;
                contentEl.id = '';
                safeHighlight(contentEl);
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
                msg = `> ${replyingTo.content}\n\n${msg}`;
                replyingTo = null;
            }
            
            let toolResults = [];
            if (activeTools.size > 0) {
                for (const toolId of activeTools) {
                    if (tools[toolId]) {
                        try {
                            if (!window.KaguyaAPI) throw new Error('api_client_unavailable');
                            const data = await window.KaguyaAPI.json('/tool/execute', {tool: toolId, input: msg});
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
                const container = $('messagesContainer');
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
                
                if (!window.KaguyaStream) throw new Error('stream_helper_unavailable');
                await window.KaguyaStream.postSSE('/stream', {
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
                        rag_iterative: ragSettings.useIterative,
                        device_id: generateDeviceId(),
                        external_api: extApi
                    }, {
                    onReader: function(reader) { currentReader = reader; },
                    shouldStop: function() { return !currentReader; },
                    onFrame: function(data) {
                        if (data.content) {
                            fullContent += data.content;
                            contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
                            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                        }
                        if (data.thinking) {
                            fullReasoning += data.thinking;
                            hasReasoning = true;
                            if (reasoningSection) reasoningSection.style.display = 'block';
                            if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                        }
                        if (data.reasoning) {
                            fullReasoning += data.reasoning;
                            hasReasoning = true;
                            if (reasoningSection) reasoningSection.style.display = 'block';
                            if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                        }
                        if (data.done) {
                            if (settings.markdown) {
                                contentEl.innerHTML = safeMarkedParse(fullContent);
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
                    }
                });
                currentReader = null;
                contentEl.id = '';
                if (reasoningSection) reasoningSection.id = '';
                if (reasoningContentEl) reasoningContentEl.id = '';
                safeHighlight(contentEl);
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
                const container = $('messagesContainer');
                if (container.lastElementChild) container.removeChild(container.lastElementChild);
                sendMessage();
            }
        }
        
        function requestTTS(text) {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.json('/tts', { text: text.slice(0, 300) })
                .then(data => { if (data.audio_url) new Audio(data.audio_url).play(); });
        }
        
        function showCodeModal() { document.getElementById('codeModal').classList.add('show'); }
        function showKBModal() { document.getElementById('kbModal').classList.add('show'); }
        async function openAccountCenter(){
            const modal=document.createElement('div');
            modal.id='accountCenterModal';
            modal.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:100000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);';
            modal.innerHTML=`<div style="background:var(--card-bg,#1e1e2e);border:1px solid var(--border);border-radius:20px;padding:28px;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
                    <h3 style="color:var(--text-primary);font-size:18px;font-weight:700;">👥 账户管理中心</h3>
                    <button onclick="document.getElementById('accountCenterModal').remove()" style="background:none;border:none;color:var(--text-muted);font-size:18px;cursor:pointer;">✕</button>
                </div>
                <div id="accountListContainer" style="display:flex;flex-direction:column;gap:10px;">
                    <div style="text-align:center;padding:20px;color:var(--text-muted);">加载中...</div>
                </div>
            </div>`;
            document.body.appendChild(modal);
            modal.onclick=(e)=>{if(e.target===modal)modal.remove();};
            try{
                if (!window.KaguyaAPI) throw new Error('api_client_unavailable');
                const d=await window.KaguyaAPI.get('/agent/accounts');
                const container=document.getElementById('accountListContainer');
                if(!d.accounts||!d.accounts.length){
                    container.innerHTML='<div style="text-align:center;padding:20px;color:var(--text-muted);">暂无注册账户</div>';
                    return;
                }
                container.innerHTML=d.accounts.map(a=>{
                    const created=new Date(a.created*1000).toLocaleString('zh-CN');
                    const lastSeen=new Date(a.last_seen*1000).toLocaleString('zh-CN');
                    const ips=(a.ip_addresses||[]).join(', ')||'未知';
                    const imported=(a.imported_paths||[]).length;
                    return `<div style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:12px;padding:14px;">
                        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                            <div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#6c5ce7,#22d3ee);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;color:#fff;">${(a.name||'U').charAt(0).toUpperCase()}</div>
                            <div style="flex:1;">
                                <div style="font-size:13px;font-weight:700;color:var(--text-primary);">${escapeHtml(a.name||a.id)}</div>
                                <div style="font-size:10px;color:var(--text-muted);">ID: ${a.id.substring(0,12)}...</div>
                            </div>
                        </div>
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:11px;color:var(--text-secondary);">
                            <div>📅 注册: ${created}</div>
                            <div>🕐 最近: ${lastSeen}</div>
                            <div>🌐 IP: ${ips.substring(0,30)}${ips.length>30?'...':''}</div>
                            <div>📂 导入: ${imported}个路径</div>
                        </div>
                    </div>`;
                }).join('');
            }catch(e){
                const container=document.getElementById('accountListContainer');
                if(container)container.innerHTML='<div style="text-align:center;padding:20px;color:#e74c3c;">加载失败: '+e.message+'</div>';
            }
        }

        async function openFeatureCenter() {
            const ok=await checkAdvancedApi();
            if(!ok)return;
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
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/code/execute', {code}).then(data => {
                const output = document.getElementById('codeOutput');
                output.style.display = 'block';
                output.innerHTML = `<strong>${data.success ? '✅ 输出:' : '❌ 错误:'}</strong>\n${data.output}`;
            });
        }
        
        function addToKB() {
            const text = document.getElementById('kbInput').value.trim();
            if (!text) return;
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/kb/add', {text}).then(data => {
                if (data.success) {
                    showToast('已添加到知识库');
                    document.getElementById('kbInput').value = '';
                }
            });
        }
        
        function searchKB() {
            const query = $('kbSearch').value.trim();
            if (!query) return;
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/kb/search', {query}).then(data => {
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
        function updateCharCount() { document.getElementById('charCount').textContent = `${$('mainInput').value.length} / 4000`; }
        function updateTemp(v) { document.getElementById('tempValue').textContent = v; settings.temp = parseFloat(v); saveSettings(); }
        
        function updateSetting(k, v) {
            if (k === 'temp') { settings.temp = parseFloat(v); $('settingTempValue').textContent = v; }
            if (k === 'tokens') { settings.tokens = parseInt(v); $('settingTokensValue').textContent = v; }
            if (k === 'voice') settings.voice = v;
            if (k === 'markdown') settings.markdown = v;
            saveSettings();
        }
        
        function toggleDarkMode() {
            document.body.classList.toggle('dark');
            settings.dark = document.body.classList.contains('dark');
            $('darkModeToggle').checked = settings.dark;
            saveSettings();
            showToast(settings.dark ? '已开启深色模式' : '已关闭深色模式');
        }
        
        function toggleVoice() {
            settings.voice = !settings.voice;
            $('voiceOutputToggle').checked = settings.voice;
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
        
        function openApiHub(){
            const existing=document.getElementById('apiHubModal');
            if(existing)existing.remove();
            const m=document.createElement('div');
            m.id='apiHubModal';
            m.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);z-index:100000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);';
            m.innerHTML=`<div style="background:var(--card-bg,#1e1e2e);border:1px solid var(--border);border-radius:20px;padding:24px;max-width:680px;width:92%;max-height:85vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;"><h3 style="color:var(--text-primary);font-size:16px;font-weight:700;background:linear-gradient(135deg,#6c5ce7,#22d3ee,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AI 模型中心</h3><button onclick="document.getElementById('apiHubModal').remove()" style="background:none;border:none;color:var(--text-muted);font-size:18px;cursor:pointer;">✕</button></div><div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:14px;" id="apiHubTabs"></div><div id="apiHubContent"></div><div id="apiHubStatus" style="margin-top:12px;font-size:11px;"></div></div>`;
            document.body.appendChild(m);
            m.onclick=(e)=>{if(e.target===m)m.remove();};
            const tabs=Object.keys(API_PROVIDERS);
            const tabsEl=document.getElementById('apiHubTabs');
            tabs.forEach(pv=>{
                const p=API_PROVIDERS[pv];
                const btn=document.createElement('button');
                btn.className='api-tab';
                btn.dataset.pv=pv;
                btn.textContent=p.name;
                btn.style.cssText='padding:5px 14px;border:1px solid var(--border);border-radius:8px;font-size:12px;cursor:pointer;background:transparent;color:var(--text-secondary);transition:var(--transition);white-space:nowrap;overflow:visible;text-overflow:clip;';
                btn.onclick=()=>switchApiProvider(pv);
                tabsEl.appendChild(btn);
            });
            switchApiProvider(_currentApiProvider||'deepseek');
        }

        let _currentApiProvider=localStorage.getItem('active_api_provider')||'deepseek';

        function getApiProviders(){try{return JSON.parse(localStorage.getItem('api_providers')||'{}');}catch(e){return{};}}
        function sanitizeApiProvidersForStorage(cfg){
          var clean={};
          Object.keys(cfg||{}).forEach(function(k){
            var c=cfg[k]||{};
            clean[k]=Object.assign({},c,{
              apiKey:(c.apiKey&&String(c.apiKey).includes('****'))?c.apiKey:'',
              hasSavedKey:!!(c.hasSavedKey||c.masked_api_key||c.maskedApiKey),
              masked_api_key:c.masked_api_key||c.maskedApiKey||((c.apiKey&&String(c.apiKey).includes('****'))?c.apiKey:'')
            });
          });
          return clean;
        }
        function chooseActiveApiProvider(cfg){
          var selected=localStorage.getItem('active_api_provider')||_currentApiProvider||'deepseek';
          if(API_PROVIDERS[selected]&&cfg[selected]&&cfg[selected].enabled&&(cfg[selected].apiKey||cfg[selected].hasSavedKey))return selected;
          for(const pv of Object.keys(API_PROVIDERS)){
            const c=cfg[pv];
            if(c&&c.enabled&&(c.apiKey||c.hasSavedKey))return pv;
          }
          return API_PROVIDERS[selected]?selected:'deepseek';
        }
        async function saveApiProviders(cfg, preferredProvider){
          localStorage.setItem('api_providers',JSON.stringify(sanitizeApiProvidersForStorage(cfg)));
          var preferredCfg=preferredProvider&&cfg[preferredProvider]?cfg[preferredProvider]:null;
          var activeProvider=(preferredCfg&&preferredCfg.enabled&&(preferredCfg.apiKey||preferredCfg.hasSavedKey))?preferredProvider:chooseActiveApiProvider(cfg);
          _currentApiProvider=activeProvider;
          localStorage.setItem('active_api_provider',activeProvider);
          var backendCfg={active_provider:activeProvider,providers:{},device_id:generateDeviceId()};
          Object.keys(cfg).forEach(function(k){
            var c=cfg[k];
            backendCfg.providers[k]={api_url:c.apiUrl||'',api_key:c.apiKey||'',model:c.model||''};
          });
          if(!window.KaguyaAPI) throw new Error('api_client_unavailable');
          window.KaguyaAPI.json('/external/config', backendCfg).catch(function(){});
          var bindProvider=(preferredCfg&&preferredCfg.apiKey)?preferredProvider:activeProvider;
          var activeCfg=cfg[bindProvider]||{};
          if(activeCfg.apiKey){
            var bindPayload={device_id:generateDeviceId(),provider:bindProvider,apiKey:activeCfg.apiKey,apiUrl:activeCfg.apiUrl||API_PROVIDERS[bindProvider].url,model:activeCfg.model||API_PROVIDERS[bindProvider].models[0].id};
            var bindData = await window.KaguyaAPI.bindDeviceConfig(bindPayload);
            if(bindData&&bindData.success){
              activeCfg.hasSavedKey=true;
              activeCfg.masked_api_key=bindData.masked_api_key||bindData.api_key||bindData.apiKey||'';
              activeCfg.apiKey='';
              cfg[bindProvider]=activeCfg;
              localStorage.setItem('api_providers',JSON.stringify(sanitizeApiProvidersForStorage(cfg)));
            } else if(bindData&&bindData.error) {
              throw new Error(bindData.message||bindData.error);
            }
            if(window.kaguyaDesktop&&window.kaguyaDesktop.device&&window.kaguyaDesktop.device.bind){
              window.kaguyaDesktop.device.bind(bindPayload).catch(function(){});
            }
          }
        }

        function getActiveApiConfig(){
            const providers=getApiProviders();
            const pv=chooseActiveApiProvider(providers);
            const cfg=providers[pv];
            if(cfg&&cfg.enabled&&(cfg.apiKey||cfg.hasSavedKey)){
                return{provider:pv,enabled:true,apiKey:cfg.apiKey||'',hasSavedKey:!!cfg.hasSavedKey,apiUrl:cfg.apiUrl||API_PROVIDERS[pv].url,model:cfg.model||API_PROVIDERS[pv].models[0].id};
            }
            return null;
        }

        async function hydrateSavedApiConfig(){
            if(!window.KaguyaAPI||!window.KaguyaAPI.loadSavedConfig)return null;
            const data=await window.KaguyaAPI.loadSavedConfig();
            if(!data||!data.success||!data.has_config||!data.provider)return data;
            const pv=API_PROVIDERS[data.provider]?data.provider:'custom';
            if(!API_PROVIDERS[pv])return data;
            const providers=getApiProviders();
            const existing=providers[pv]||{};
            providers[pv]=Object.assign({},existing,{
                enabled:true,
                apiKey:'',
                hasSavedKey:true,
                apiUrl:data.api_url||data.apiUrl||existing.apiUrl||API_PROVIDERS[pv].url,
                model:data.model||existing.model||API_PROVIDERS[pv].models[0].id,
                masked_api_key:data.masked_api_key||existing.masked_api_key||existing.maskedApiKey||''
            });
            localStorage.setItem('api_providers',JSON.stringify(sanitizeApiProvidersForStorage(providers)));
            _currentApiProvider=pv;
            localStorage.setItem('active_api_provider',pv);
            updateApiIndicator();
            return data;
        }

        function switchApiProvider(pv){
            _currentApiProvider=pv;
            document.querySelectorAll('.api-tab').forEach(b=>{
                if(b.dataset.pv===pv){b.style.background='var(--accent,#7c6aff)';b.style.color='#fff';}
                else{b.style.background='transparent';b.style.color='var(--text-muted)';}
            });
            renderApiProviderPanel(pv);
        }

        function renderApiProviderPanel(pv){
            const p=API_PROVIDERS[pv];
            if(!p)return;
            const cfg=getApiProviders()[pv]||{};
            const content=document.getElementById('apiHubContent');
            const modelOpts=p.models.map(m=>`<option value="${m.id}"${cfg.model===m.id?' selected':''}>${m.label}</option>`).join('');
            const keyPlaceholder=cfg.hasSavedKey&&cfg.masked_api_key?('已保存: '+cfg.masked_api_key):'sk-/api-xxxxxxxx';
            content.innerHTML=`<div style="background:linear-gradient(135deg,${p.color}15,${p.color}05);border-radius:12px;padding:16px;margin-bottom:18px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:6px;">${p.icon} ${p.name}</div><div style="font-size:11px;color:var(--text-secondary);line-height:1.6;">访问 <a href="${p.docUrl}" target="_blank" style="color:${p.color};">官方平台</a> 获取 API Key</div></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">API Key</label><input type="password" id="ap_apiKey" value="${cfg.apiKey||''}" placeholder="${keyPlaceholder}" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);outline:none;transition:var(--transition);" onfocus="this.style.borderColor='${p.color}'" onblur="this.style.borderColor=''"></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">API 地址</label><input type="text" id="ap_apiUrl" value="${cfg.apiUrl||p.url}" placeholder="${p.url}" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);outline:none;"></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">模型选择</label><select id="ap_model" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">${modelOpts}</select></div><div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:var(--bg-secondary);border-radius:10px;margin-bottom:16px;"><span style="font-size:12px;font-weight:600;color:var(--text-primary);">启用 ${p.name}</span><label class="toggle"><input type="checkbox" id="ap_enabled" ${cfg.enabled?'checked':''}><span class="toggle-slider"></span></label></div><div style="display:flex;gap:8px;"><button onclick="testApiConnection('${pv}')" style="flex:1;padding:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:10px;font-size:12px;cursor:pointer;color:var(--text-secondary);font-weight:600;transition:var(--transition);" onmouseover="this.style.borderColor='${p.color}'" onmouseout="this.style.borderColor=''">❓ 测试连接</button><button onclick="saveApiProvider('${pv}')" style="flex:1;padding:10px;background:linear-gradient(135deg,${p.color},${p.color}cc);border:none;border-radius:10px;font-size:12px;cursor:pointer;color:#fff;font-weight:700;box-shadow:0 2px 10px rgba(0,0,0,0.2);">✔ 保存</button></div>`;
        }

        async function saveApiProvider(pv){
            const providers=getApiProviders();
            const existing=providers[pv]||{};
            const nextKey=(document.getElementById('ap_apiKey').value||'').trim();
            providers[pv]={
                apiKey:nextKey,
                apiUrl:(document.getElementById('ap_apiUrl').value||API_PROVIDERS[pv].url||'').trim(),
                model:(document.getElementById('ap_model').value||'').trim(),
                enabled:document.getElementById('ap_enabled').checked,
                hasSavedKey:nextKey?false:!!existing.hasSavedKey,
                masked_api_key:nextKey?'':(existing.masked_api_key||existing.maskedApiKey||'')
            };
            if(providers[pv].enabled&&(providers[pv].apiKey||providers[pv].hasSavedKey)){
                _currentApiProvider=pv;
                localStorage.setItem('active_api_provider',pv);
            }
            try{
              await saveApiProviders(providers, pv);
              updateApiIndicator();
              showToast(API_PROVIDERS[pv].name+' 配置已保存');
            }catch(e){
              showToast('保存失败: '+(e.message||e), 'error');
            }
        }

        async function testApiConnection(pv){
            const apiKey=(document.getElementById('ap_apiKey').value||'').trim();
            const apiUrl=(document.getElementById('ap_apiUrl').value||API_PROVIDERS[pv].url||'').trim();
            const modelEl=document.getElementById('ap_model');
            const model=modelEl?(modelEl.value||'').trim():(API_PROVIDERS[pv].models[0]||{}).id;
            const statusEl=document.getElementById('apiHubStatus');
            if(!apiKey){statusEl.innerHTML='<span style="color:#e74c3c;">请输入 API Key</span>';return;}
            statusEl.innerHTML='<span style="color:var(--primary);">&#x23F3; 测试连接中...</span>';
            var lastError='';
            for(var attempt=1;attempt<=2;attempt++){
              try{
                if(attempt>1)statusEl.innerHTML='<span style="color:#f59e0b;">&#x23F3; 重试 ('+attempt+'/2)...</span>';
                if(!window.KaguyaAPI) throw new Error('api_client_unavailable');
                const d=await window.KaguyaAPI.testProvider({provider:pv,apiKey:apiKey,apiUrl:apiUrl,model:model});
                if(d.success){statusEl.innerHTML='<span style="color:#10b981;">&#x2705; 连接成功! 模型: '+(d.model||'OK')+'</span>';return;}
                lastError=d.message||d.error||'连接失败';
                if((d.error&&d.error.includes('401')||d.status_code===401)&&attempt===1){
                  await new Promise(function(r2){setTimeout(r2,2000);});
                  continue;
                }
              }catch(e){
                lastError='网络错误: '+(e.message||e);
                if(attempt<2){await new Promise(function(r2){setTimeout(r2,1500);});continue;}
              }
            }
            var errMsg=lastError||'连接失败';
            var hint='';
            if(errMsg.includes('401')||errMsg.includes('auth'))hint=' <span style="font-size:10px;color:#f59e0b;">(提示: 请确认 Key 有效且未过期，或稍后重试)</span>';
            else if(errMsg.includes('400'))hint=' <span style="font-size:10px;color:#f59e0b;">(提示: 模型名称可能不正确)</span>';
            statusEl.innerHTML='<span style="color:#e74c3c;">&#x274C; '+errMsg+'</span>'+hint;
        }

        function updateApiIndicator(){
            const active=getActiveApiConfig();
            const btn=document.querySelector('.api-hub-btn');
            if(btn){
                if(active){
                    btn.title='AI模型中心 - '+API_PROVIDERS[active.provider].name;
                    document.querySelector('.api-hub-text').textContent=API_PROVIDERS[active.provider].name.substring(0,6);
                }else{
                    btn.title='AI模型中心 - 未配置';
                    document.querySelector('.api-hub-text').textContent='API';
                }
            }
        }

        function openDeepSeek(){ openApiHub(); _currentApiProvider='deepseek';switchApiProvider('deepseek'); }
        
        function checkExternalApiWarning() {
            const hasActiveApi = getActiveApiConfig() !== null;
            const hasShownWarning = sessionStorage.getItem('api_warning_shown');
            if (!hasActiveApi && !hasShownWarning) {
                showApiWarningModal('未配罎外部AI API，部分高级功能将无法使用');
                sessionStorage.setItem('api_warning_shown', 'true');
            }
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
            debouncedSaveLS('kaguya_stats', stats);
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
            $('modelTempVal').textContent = settings.temp || 0.7;
            document.getElementById('modelTokens').value = settings.tokens || 1024;
            $('modelTokensVal').textContent = settings.tokens || 1024;
            document.getElementById('modelModal').classList.add('show');
        }
        
        function saveModelConfig() {
            settings.temp = parseFloat(document.getElementById('modelTemp').value);
            settings.tokens = parseInt(document.getElementById('modelTokens').value);
            debouncedSaveLS('kaguya_settings', settings);
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
                sunset: {primary: '#f59e0b', secondary: '#ef4444'},
                starfield: {primary: '#7dd3fc', secondary: '#c084fc'},
                wallpaper: {primary: '#a78bfa', secondary: '#c084fc'}
            };
            if (theme === 'starfield') {
                enableStarfieldMode();
                disableWallpaperMode();
            } else if (theme === 'wallpaper') {
                enableWallpaperMode();
                disableStarfieldMode();
            } else {
                disableStarfieldMode();
                disableWallpaperMode();
            }
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
            disableStarfieldMode();
            disableWallpaperMode();
            applyTheme('default');
            showToast('主题已重置');
        }
        
        let modelsConfig = {};
        try {
            const legacyModelsConfig = JSON.parse(localStorage.getItem('models_config') || '{}');
            Object.keys(legacyModelsConfig || {}).forEach(function(k){
                const c=legacyModelsConfig[k]||{};
                modelsConfig[k]={model:c.model||'',enabled:!!c.enabled,baseUrl:c.baseUrl||'',hasSavedKey:!!c.apiKey,masked_api_key:c.apiKey?'legacy-key-not-migrated':''};
            });
            localStorage.removeItem('models_config');
        } catch(e) { modelsConfig = {}; }
        
        function openModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu', 'mistral', 'groq', 'xai'];
            models.forEach(m => {
                const config = modelsConfig[m] || {};
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                if (apiKeyEl) {
                    apiKeyEl.value = '';
                    apiKeyEl.placeholder = config.hasSavedKey && config.masked_api_key ? ('已保存: ' + config.masked_api_key) : 'sk-...';
                }
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
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu', 'mistral', 'groq', 'xai'];
            models.forEach(m => {
                const apiKeyEl = document.getElementById(`${m}ApiKey`);
                const modelEl = document.getElementById(`${m}Model`);
                const enabledEl = document.getElementById(`${m}Enabled`);
                const baseUrlEl = document.getElementById(`${m}BaseUrl`);
                
                const existing=modelsConfig[m]||{};
                const key=apiKeyEl ? (apiKeyEl.value||'').trim() : '';
                modelsConfig[m] = {
                    model: modelEl ? modelEl.value : '',
                    enabled: enabledEl ? enabledEl.checked : false,
                    baseUrl: baseUrlEl ? baseUrlEl.value : '',
                    hasSavedKey: key ? false : !!existing.hasSavedKey,
                    masked_api_key: key ? '' : (existing.masked_api_key || '')
                };
                if (key && window.KaguyaAPI) {
                    window.KaguyaAPI.bindDeviceConfig({provider:m,apiKey:key,apiUrl:modelsConfig[m].baseUrl,model:modelsConfig[m].model}).then(function(data){
                        if(data&&data.success){
                            modelsConfig[m].hasSavedKey=true;
                            modelsConfig[m].masked_api_key=data.masked_api_key||'';
                        }
                    }).catch(function(){});
                }
            });
            closeModal('modelsModal');
            showToast('多模型配置已保存');
        }
        
        function testModelConnection() {
            const statusEl = document.getElementById('modelsStatus');
            statusEl.innerHTML = '<span style="color:var(--primary);">🔄 测试连接中...</span>';
            
            setTimeout(() => {
                const enabledModels = Object.entries(modelsConfig).filter(([k, v]) => v.enabled && v.hasSavedKey);
                if (enabledModels.length > 0) {
                    statusEl.innerHTML = `<span style="color:#10b981;">✅ 已配置 ${enabledModels.length} 个模型</span>`;
                } else {
                    statusEl.innerHTML = '<span style="color:#f59e0b;">⚠️ 请先启用并配置至少一个模型</span>';
                }
            }, 1000);
        }
        
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
        function showToast(msg, type) { const t = document.getElementById('toast'); t.textContent = msg; t.className = 'toast show' + (type ? ' toast-' + type : ''); clearTimeout(t._timer); t._timer = setTimeout(() => t.className = 'toast', 2500); }
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
            let text = `=== ${chat.title} ===\n${new Date().toLocaleString()}\n\n`;
            chat.messages.forEach(m => { text += `[${m.role === 'user' ? '我' : 'AI'}] ${m.time}\n${escapeHtml(m.content)}\n\n`; });
            const blob = new Blob([text], {type: 'text/plain;charset=utf-8'});
            const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `对话_${new Date().toISOString().slice(0,10)}.txt`; a.click();
            showToast('已导出');
        }
        
        function exportAllChats() {
            let text = `=== 全部对话 ===\n${new Date().toLocaleString()}\n\n`;
            chats.forEach(c => { text += `\n【${c.title}】\n`; c.messages.forEach(m => { text += `[${m.role}] ${escapeHtml(m.content)}\n`; }); });
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
            ensureTabLoaded(tab);
            if (tab === 'prompts') renderPromptList();
            if (tab === 'permissions') { loadPermMode(); }

        }
        
        function switchProjectSub(sub, btnEl) {
            var subs = ['Overview', 'Config', 'Ops', 'Release', 'Alert', 'Ab', 'Integration', 'Account', 'Security'];
            subs.forEach(function(s) {
                var el = document.getElementById('projectSub' + s);
                if (el) el.style.display = 'none';
            });
            var target = document.getElementById('projectSub' + sub.charAt(0).toUpperCase() + sub.slice(1));
            if (target) target.style.display = '';
            var container = btnEl ? btnEl.parentElement : document.querySelector('#projectTab .memory-filter-btn');
            if (container) {
                (container.parentElement || container).querySelectorAll('.memory-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            }
            if (btnEl) btnEl.classList.add('active');
            else {
                var btns = document.querySelectorAll('#projectTab .memory-filter-btn');
                btns.forEach(function(b) { if (b.getAttribute('onclick') && b.getAttribute('onclick').indexOf("'" + sub + "'") !== -1) b.classList.add('active'); });
            }
            if (sub === 'ops') loadProjectCenter();
            if (sub === 'release') loadProjectCenter();
            if (sub === 'alert') loadProjectCenter();
            if (sub === 'ab') loadProjectCenter();
            if (sub === 'integration') loadProjectCenter();
            if (sub === 'security') refreshSecurityStatus();
            if (sub === 'config') loadProjectConfig();
            if (sub === 'account') loadUserProfile();
        }
        
        function switchToolsSub(sub, btnEl) {
            var subs = ['Tools', 'Vision'];
            subs.forEach(function(s) {
                var el = document.getElementById('toolsSub' + s);
                if (el) el.style.display = 'none';
            });
            var target = document.getElementById('toolsSub' + sub.charAt(0).toUpperCase() + sub.slice(1));
            if (target) target.style.display = '';
            var container = btnEl ? btnEl.parentElement : document.querySelector('#toolsTab .memory-filter-btn');
            if (container) {
                (container.parentElement || container).querySelectorAll('.memory-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            }
            if (btnEl) btnEl.classList.add('active');
            else {
                document.querySelectorAll('#toolsTab .memory-filter-btn').forEach(function(b) { if (b.getAttribute('onclick') && b.getAttribute('onclick').indexOf("'" + sub + "'") !== -1) b.classList.add('active'); });
            }
            if (sub === 'vision') loadVisionHistory();
        }
        
        function switchKnowledgeSub(sub, btnEl) {
            var subs = ['Rag', 'Finetune', 'Lora'];
            subs.forEach(function(s) {
                var el = document.getElementById('knowledgeSub' + s);
                if (el) el.style.display = 'none';
            });
            var target = document.getElementById('knowledgeSub' + sub.charAt(0).toUpperCase() + sub.slice(1));
            if (target) target.style.display = '';
            var container = btnEl ? btnEl.parentElement : document.querySelector('#knowledgeTab .memory-filter-btn');
            if (container) {
                (container.parentElement || container).querySelectorAll('.memory-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            }
            if (btnEl) btnEl.classList.add('active');
            else {
                document.querySelectorAll('#knowledgeTab .memory-filter-btn').forEach(function(b) { if (b.getAttribute('onclick') && b.getAttribute('onclick').indexOf("'" + sub + "'") !== -1) b.classList.add('active'); });
            }
            if (sub === 'rag') loadRagDocuments();
            if (sub === 'finetune') refreshFinetuneData();
            if (sub === 'lora') loadLoraList();
        }

        // Agent permission dashboard lives in kaguya-permissions-panel.js.

        // 在 DOM 加载完成后初始化
        document.addEventListener('DOMContentLoaded', () => {
            init();
            initCodeFolding();
            initSidebarResizer();
            if(isElectron){
                initElectronTerminal();
            }
        });

        async function initElectronTerminal(){
            if(!isElectron)return;
            try{
                electronTerminalSession = await window.kaguyaDesktop.terminal.create({});
                console.log('[Electron] Terminal session created:', electronTerminalSession);
                window.kaguyaDesktop.terminal.onData(function(data){
                    if(data.sessionId === electronTerminalSession){
                        termLog(data.data, data.stream === 'stderr' ? 'error' : 'success');
                    }
                });
                window.kaguyaDesktop.terminal.onExit(function(data){
                    if(data.sessionId === electronTerminalSession){
                        termLog('[Terminal exited with code ' + data.code + ']', 'info');
                        electronTerminalSession = null;
                    }
                });
                window.kaguyaDesktop.terminal.onError(function(data){
                    if(data.sessionId === electronTerminalSession){
                        termLog('[Terminal error: ' + data.error + ']', 'error');
                    }
                });
            }catch(e){
                console.error('[Electron] Failed to create terminal session:', e);
            }
        }

        function initCodeFolding() {
            setTimeout(function() {
                document.querySelectorAll('.code-block').forEach(function(block) {
                    try {
                        var lang = block.dataset.lang || '';
                        var key = 'fold_' + lang + '_' + block.dataset.lines;
                        var saved = localStorage.getItem(key);
                        if (saved === '1' && !block.classList.contains('collapsed')) {
                            block.classList.add('collapsed');
                            var foldBtn = block.querySelector('.fold-btn');
                            if (foldBtn) {
                                foldBtn.classList.add('fold-active');
                                var chevron = foldBtn.querySelector('.fold-chevron');
                                foldBtn.innerHTML = '';
                                if (chevron) { foldBtn.appendChild(chevron); chevron.textContent = '▲'; }
                                else { var c = document.createElement('span'); c.className = 'fold-chevron'; c.textContent = '▲'; foldBtn.appendChild(c); }
                                foldBtn.appendChild(document.createTextNode('展开'));
                                foldBtn.title = '展开代码';
                            }
                        }
                    } catch(e) {}
                });
            }, 300);
        }

        function initSidebarResizer() {
            var sidebar = document.querySelector('.sidebar-panel') || document.getElementById('sidebar');
            if (!sidebar) return;
            var resizer = document.createElement('div');
            resizer.className = 'sidebar-resizer';
            sidebar.style.position = 'relative';
            sidebar.appendChild(resizer);
            var isResizing = false;
            var startX = 0;
            var startWidth = 0;
            resizer.addEventListener('mousedown', function(e) {
                isResizing = true;
                startX = e.clientX;
                startWidth = sidebar.offsetWidth;
                resizer.classList.add('active');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });
            document.addEventListener('mousemove', function(e) {
                if (!isResizing) return;
                var diff = e.clientX - startX;
                var newWidth = Math.max(200, Math.min(500, startWidth + diff));
                sidebar.style.width = newWidth + 'px';
                try { localStorage.setItem('sidebar_width', newWidth); } catch(e) {}
            });
            document.addEventListener('mouseup', function() {
                if (isResizing) {
                    isResizing = false;
                    resizer.classList.remove('active');
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                }
            });
            var saved = localStorage.getItem('sidebar_width');
            if (saved) sidebar.style.width = saved + 'px';
        }

        // File analyzer panel lives in kaguya-file-analyzer-panel.js.

        setTimeout(function(){ try { if (typeof initInteractionEnhancements === 'function') initInteractionEnhancements(); } catch(e) {} }, 500);

// ========== INIT ENHANCED MODULES ==========
        function initBackendModules() {
            try { renderOpsChannelComparison(); } catch(e) {}
            try { renderOpsCalendar(); } catch(e) {}
            try { renderReleaseTimeline(); } catch(e) {}
            try { renderRollbackVersions(); } catch(e) {}
            try { renderAlertHistory(); } catch(e) {}
            try { renderNotificationChannels(); } catch(e) {}
            try { renderTrafficAllocator(); } catch(e) {}
            try { renderIntegrationMarket(); } catch(e) {}
            try { renderWebhooks(); } catch(e) {}
            try { updateConnectionTestTargets(); } catch(e) {}
        }

        setTimeout(initBackendModules, 1000);
