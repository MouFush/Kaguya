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
        window.debugPromptScroll = function() {
            var el = document.getElementById('promptList');
            var tab = document.getElementById('promptsTab');
            var sidebar = document.getElementById('sidebar');
            if (!el || !tab || !sidebar) return;
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
        let deepseekConfig = JSON.parse(localStorage.getItem('deepseek_config') || '{}');
        try {
            if (!localStorage.getItem('api_providers_migrated') && Object.keys(deepseekConfig).length > 0) {
                const migrated = {};
                if (deepseekConfig.apiKey || deepseekConfig.apiUrl || deepseekConfig.model) {
                    migrated.deepseek = {
                        enabled: Boolean(deepseekConfig.apiKey),
                        apiKey: '',
                        apiUrl: deepseekConfig.apiUrl || 'https://api.deepseek.com',
                        model: deepseekConfig.model || 'deepseek-chat',
                        hasSavedKey: false,
                        masked_api_key: deepseekConfig.apiKey ? 'legacy-key-not-migrated' : ''
                    };
                }
                localStorage.setItem('api_providers', JSON.stringify(migrated));
                localStorage.setItem('api_providers_migrated', '1');
            }
            localStorage.removeItem('deepseek_config');
        } catch(e) {}
        
        
        const _domCache = new Map();
        function $(id) { if (!_domCache.has(id)) _domCache.set(id, document.getElementById(id)); return _domCache.get(id); }
        function $clear(id) { _domCache.delete(id); }
        function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
        function throttle(fn, ms = 100) { let last = 0; return (...a) => { const now = Date.now(); if (now - last >= ms) { last = now; fn(...a); } }; }
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

        function handleStreamResponse(response, contentEl, thinkingEl, onDone) {
            let fullContent = '';
            let fullThinking = '';
            let rafId = null;
            let needsScroll = false;
            let finalized = false;

            function scheduleScroll() {
                if (!rafId) {
                    rafId = requestAnimationFrame(() => {
                        const container = $('messagesContainer');
                        if (container) container.scrollTop = container.scrollHeight;
                        rafId = null;
                    });
                }
            }

            if (!window.KaguyaStream) return Promise.reject(new Error('stream_helper_unavailable'));
            return window.KaguyaStream.readSSE(response, {
                onFrame: function(data) {
                    if (data.content) {
                        fullContent += data.content;
                        if (contentEl) {
                            contentEl.innerHTML = settings.markdown ? safeMarkedParse(fullContent) : fullContent.replace(/\n/g, '<br>');
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
                    if (needsScroll) { scheduleScroll(); needsScroll = false; }
                    if (data.done && !finalized) {
                        finalized = true;
                        if (onDone) onDone(fullContent, fullThinking);
                    }
                }
            }).then(function() {
                if (!finalized && onDone) onDone(fullContent, fullThinking);
                return {content: fullContent, thinking: fullThinking};
            });
        }

        
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

        function favoriteTemplate(templateId) {
            if (!PROMPT_FAVORITES.includes(templateId)) {
                PROMPT_FAVORITES.push(templateId);
                savePromptFavorites();
            }
            showToast('已收藏模板');
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

        function deleteCustomTemplate(templateId) {
            const idx = CUSTOM_TEMPLATES.findIndex(c => c.id === templateId);
            if (idx >= 0) {
                CUSTOM_TEMPLATES.splice(idx, 1);
                saveCustomTemplates();
                const favIdx = PROMPT_FAVORITES.indexOf(templateId);
                if (favIdx >= 0) { PROMPT_FAVORITES.splice(favIdx, 1); savePromptFavorites(); }
                renderPromptList();
                showToast('模板已删除');
            }
        }

        function openQuickSceneModal() {
            createCustomTemplate();
        }

        function saveQuickScene() {
            saveCustomTemplate();
        }

        function applyQuickScene(sceneId) {
            const item = getAllTemplates().find(t => t.id === sceneId);
            if (item && item.prompt) {
                $('mainInput').value = item.prompt;
                PROMPT_USAGE[sceneId] = (PROMPT_USAGE[sceneId] || 0) + 1;
                savePromptUsage();
                showToast('已应用场景模板');
            }
        }

        function loadTemplateAnalysis() {
            const range = document.getElementById('templateAnalysisRange')?.value || '7d';
            fetch('/templates/analysis?range=' + range)
                .then(r => r.json())
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
            fetch('/rag/stats')
                .then(r => r.json())
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

        let _projectCenterLoading = false;
        function loadProjectCenter() {
            if (_projectCenterLoading) return;
            _projectCenterLoading = true;
            fetch('/project/batch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            }).then(r => r.json()).then(res => {
                if (!res.success) return;
                const d = res.data;
                if (d.project_overview?.success) projectOverview = d.project_overview.overview || {};
                if (d.artifacts?.success) projectArtifacts = d.artifacts.artifacts || [];
                if (d.project_tasks?.success) projectTasks = d.project_tasks.tasks || [];
                if (d.playbooks?.success) projectPlaybooks = d.playbooks.playbooks || [];
                if (d.project_activity?.success) projectActivities = d.project_activity.activities || [];
                if (d.project_milestones?.success) projectMilestones = d.project_milestones.milestones || [];
                if (d.project_risks?.success) projectRisks = d.project_risks.risks || [];
                if (d.ops_overview?.success) opsOverview = d.ops_overview.overview || {};
                if (d.ops_campaigns?.success) opsCampaigns = d.ops_campaigns.campaigns || [];
                if (d.release_overview?.success) releaseOverview = d.release_overview.overview || {};
                if (d.release_plans?.success) releasePlans = d.release_plans.plans || [];
                if (d.alerts_overview?.success) alertOverview = d.alerts_overview.overview || {};
                if (d.alerts_rules?.success) alertRules = d.alerts_rules.rules || [];
                if (d.ab_overview?.success) abOverview = d.ab_overview.overview || {};
                if (d.ab_experiments?.success) abExperiments = d.ab_experiments.experiments || [];
                if (d.integrations_overview?.success) integrationOverview = d.integrations_overview.overview || {};
                if (d.integrations?.success) integrationItems = d.integrations.integrations || [];
                if (d.console_overview?.success) consoleOverview = d.console_overview.overview || {};
                if (d.console_recommendations?.success) consoleRecommendations = d.console_recommendations.recommendations || [];
                if (d.workspace_overview?.success) workspaceOverview = d.workspace_overview.overview || {};
                if (d.workspace_projects?.success) workspaceProjects = d.workspace_projects.projects || [];
                selectedTaskIds = new Set(Array.from(selectedTaskIds).filter(id => projectTasks.some(t => t.id === id)));
                renderConsoleOverview();
                renderConsoleRecommendations();
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
            }).catch(() => {}).finally(() => { _projectCenterLoading = false; });
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
                        const cpuEl=$('cpuUsage'),cpuBar=$('cpuBar'),memEl=$('memoryUsage'),memBar=$('memoryBar'),diskEl=$('diskUsage'),diskBar=$('diskBar'),netEl=$('networkStatus'),netBar=$('networkBar');
                        if(cpuEl)cpuEl.textContent=m.cpu_percent?`${m.cpu_percent}%`:'--';
                        if(cpuBar)cpuBar.style.width=`${m.cpu_percent||0}%`;
                        if(memEl)memEl.textContent=m.memory_percent?`${m.memory_percent}%`:'--';
                        if(memBar)memBar.style.width=`${m.memory_percent||0}%`;
                        if(diskEl)diskEl.textContent=m.disk_percent?`${m.disk_percent}%`:'--';
                        if(diskBar)diskBar.style.width=`${m.disk_percent||0}%`;
                        if(netEl)netEl.textContent=m.network_status||'正常';
                        if(netBar)netBar.style.width=m.network_status==='正常'?'100%':'50%'; 
                    }
                })
                .catch(() => {
                    const ce=$('cpuUsage'),me=$('memoryUsage'),de=$('diskUsage');
                    if(ce)ce.textContent='N/A';if(me)me.textContent='N/A';if(de)de.textContent='N/A';
                });
        }

        function openSystemMonitorModal() {
            const modal = createModal('systemMonitorModal', 'System Monitor', '', {maxWidth: '700px'});
            modal.querySelector('.modal-body').innerHTML =
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
            const logLevelFilter=$('logLevelFilter'); const level = logLevelFilter ? logLevelFilter.value : 'all';
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
            const logViewer=$('logViewer'); if(logViewer) logViewer.innerHTML = '<div class="log-entry log-info"><span class="log-time">[系统]</span> 日志已清空</div>';
        }

        function exportLogs() {
            const logV=$('logViewer'); const logs = logV ? logV.innerText : '';
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
            const viewer = $('logViewer');
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
            createModal('taskSchedulerModal', '⏰ 新建定时任务', `
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">任务名称</label><input class="project-input" id="taskName" placeholder="输入任务名称" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">执行时间</label><input type="time" class="project-input" id="taskTime" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">重复周期</label><select class="project-input" id="taskRepeat" style="width:100%;"><option value="daily">每天</option><option value="weekly">每周</option><option value="monthly">每月</option><option value="once">仅一次</option></select></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">任务类型</label><select class="project-input" id="taskType" style="width:100%;"><option value="backup">数据备份</option><option value="cleanup">缓存清理</option><option value="report">报告生成</option><option value="custom">自定义脚本</option></select></div>
                <div style="display:flex;gap:10px;justify-content:flex-end;"><button class="project-mini-btn" onclick="closeModal('taskSchedulerModal')">取消</button><button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveScheduledTask()">保存</button></div>
            `, {maxWidth: '500px'});
        }

        function saveScheduledTask() {
            const name = $('taskName')?.value;
            const time = $('taskTime')?.value;
            const repeat = $('taskRepeat')?.value;
            const type = $('taskType')?.value;
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
            const el = $('scheduledTasksList');
            if (!el) return;
            el.innerHTML = tasks.map(t => `
                <div class="scheduler-task-card">
                    <div class="task-header">
                        <span class="task-name">${escapeHtml(t.name)}</span>
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
                        const art=$('avgResponseTime'),tr=$('totalRequests'),er=$('errorRate'),tp=$('throughput');
                        if(art)art.textContent=data.stats.avg_response_time||'--';
                        if(tr)tr.textContent=data.stats.total_requests||'--';
                        if(er)er.textContent=data.stats.error_rate||'--';
                        if(tp)tp.textContent=data.stats.throughput||'--';
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
            const el = $('serviceHealthGrid');
            if (!el || !services) return;
            el.innerHTML = services.map(s => `
                <div class="service-card ${s.status}">
                    <div class="service-icon">${s.icon}</div>
                    <div class="service-info">
                        <div class="service-name">${escapeHtml(s.name)}</div>
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
                        const td=$('totalDeps'),od=$('outdatedDeps'),vd=$('vulnerableDeps');
                        if(td)td.textContent=data.summary.total;if(od)od.textContent=data.summary.outdated;if(vd)vd.textContent=data.summary.vulnerable;
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
            const el = $('gitStatusGrid');
            if (!el || !repos) return;
            el.innerHTML = repos.map(r => `
                <div class="git-repo-card">
                    <div class="git-repo-header">
                        <span class="git-repo-name">📁 ${escapeHtml(r.name)}</span>
                        <span class="git-branch">🌿 ${r.branch}</span>
                    </div>
                    <div class="git-repo-stats">
                        <span class="git-stat">📝 ${r.modified} 已修改</span>
                        <span class="git-stat">➕ ${r.added} 新文件</span>
                        <span class="git-stat">⏳ ${r.ahead} 待推送</span>
                    </div>
                    <div class="git-repo-actions">
                        <button class="git-btn" onclick="gitCommit('${escapeHtml(r.name)}')">提交</button>
                        <button class="git-btn" onclick="gitPush('${escapeHtml(r.name)}')">推送</button>
                        <button class="git-btn" onclick="gitPull('${escapeHtml(r.name)}')">拉取</button>
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
            createModal('newProjectModal', '📁 新建项目', `
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目名称</label><input class="project-input" id="newProjectName" placeholder="输入项目名称" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目路径</label><input class="project-input" id="newProjectPath" placeholder="输入项目路径" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目描述</label><textarea class="project-input" id="newProjectDesc" placeholder="输入项目描述" style="width:100%;height:80px;resize:vertical;"></textarea></div>
                <div style="display:flex;gap:10px;justify-content:flex-end;"><button class="project-mini-btn" onclick="closeModal('newProjectModal')">取消</button><button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="createNewProject()">创建</button></div>
            `, {maxWidth: '500px'});
        }

        function createNewProject() {
            const name = $('newProjectName')?.value;
            const path = $('newProjectPath')?.value;
            const desc = $('newProjectDesc')?.value;
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
                        <div class="template-name">${escapeHtml(t.name)}</div>
                        <div class="template-desc">${escapeHtml(t.description)}</div>
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
                        <div class="project-item-title">${escapeHtml(item.title)}</div>
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
                        <div class="project-item-title">${item.pinned ? '📌 ' : ''}${escapeHtml(item.title)}</div>
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
        
        function deleteArtifact(id) { crudDelete('/artifacts', id, () => showToast('已删除产物')); }
        
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
        
        function updateProjectTaskStatus(id, status) { crudUpdate('/project/tasks', id, {status}); }
        
        function deleteProjectTask(id) { crudDelete('/project/tasks', id, () => showToast('已删除任务')); }
        
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
                        <div class="project-item-title">${escapeHtml(item.name)}</div>
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
                    <div class="activity-main">${escapeHtml(item.action)} · ${item.entity} · ${item.detail || item.entity_id}</div>
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
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planned'}"></span>${escapeHtml(item.title)}</div>
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

        function updateMilestoneStatus(id, status, progress) { crudUpdate('/project/milestones', id, {status, progress}); }

        function deleteMilestone(id) { crudDelete('/project/milestones', id, () => showToast('已删除里程碑')); }

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
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${escapeHtml(item.title)}</div>
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

        function updateRiskStatus(id, status) { crudUpdate('/project/risks', id, {status}); }

        function deleteRisk(id) { crudDelete('/project/risks', id, () => showToast('已删除风险')); }

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
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${escapeHtml(item.name)}</div>
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
        
        function updateOpsCampaignStatus(id, status) { crudUpdate('/ops/campaigns', id, {status}); }
        
        function deleteOpsCampaign(id) { crudDelete('/ops/campaigns', id, () => showToast('已删除活动')); }
        
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
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'planning'}"></span>${escapeHtml(item.version)} · ${escapeHtml(item.title)}</div>
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
            const lines = (document.getElementById('releaseChecklistInput').value || '').split("\n").map(x => x.trim()).filter(Boolean);
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
        
        function updateReleaseStatus(id, status) { crudUpdate('/release/plans', id, {status}); }
        
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
        
        function deleteReleasePlan(id) { crudDelete('/release/plans', id, () => showToast('已删除发布计划')); }

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
                        <div class="project-item-title"><span class="status-dot-badge ${item.level || 'medium'}"></span>${escapeHtml(item.name)}</div>
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

        function updateAlertRuleStatus(id, status) { crudUpdate('/alerts/rules', id, {status}); }

        function deleteAlertRule(id) { crudDelete('/alerts/rules', id, () => showToast('已删除告警规则')); }

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
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'draft'}"></span>${escapeHtml(item.name)}</div>
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

        function updateAbStatus(id, status) { crudUpdate('/ab/experiments', id, {status}); }

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

        function deleteAb(id) { crudDelete('/ab/experiments', id, () => showToast('已删除AB实验')); }

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
                        <div class="project-item-title"><span class="status-dot-badge ${item.status || 'disabled'}"></span>${escapeHtml(item.name)}</div>
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

        function updateIntegrationStatus(id, status) { crudUpdate('/integrations', id, {status}); }

        function deleteIntegration(id) { crudDelete('/integrations', id, () => showToast('已删除集成')); }
        
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
        
        function showTyping() {
            const container = $('messagesContainer');
            const typing = document.createElement('div');
            typing.className = 'message assistant';
            typing.id = 'typingIndicator';
            const roleData = roles.find(r => r.id === currentRole) || roles[0];
            typing.innerHTML = `<div class="message-avatar">${roleData.icon || '🤖'}</div><div class="message-content-wrapper"><div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>`;
            container.appendChild(typing);
            requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
        }
        
        function hideTyping() { const t = document.getElementById('typingIndicator'); if (t) t.remove(); }
        
        function requestTTS(text) {
            fetch('/tts', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ text: text.slice(0, 300) }) })
                .then(r => r.json()).then(data => { if (data.audio_url) new Audio(data.audio_url).play(); });
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
                const r=await fetch('/agent/accounts');
                const d=await r.json();
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
            fetch('/code/execute', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code})
            }).then(r => r.json()).then(data => {
                const output = document.getElementById('codeOutput');
                output.style.display = 'block';
                output.innerHTML = `<strong>${data.success ? '✅ 输出:' : '❌ 错误:'}</strong>\n${data.output}`;
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
            const query = $('kbSearch').value.trim();
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
        async function saveApiProviders(cfg){
          localStorage.setItem('api_providers',JSON.stringify(sanitizeApiProvidersForStorage(cfg)));
          var activeProvider=chooseActiveApiProvider(cfg);
          _currentApiProvider=activeProvider;
          localStorage.setItem('active_api_provider',activeProvider);
          var backendCfg={active_provider:activeProvider,providers:{},device_id:generateDeviceId()};
          Object.keys(cfg).forEach(function(k){
            var c=cfg[k];
            backendCfg.providers[k]={api_url:c.apiUrl||'',api_key:c.apiKey||'',model:c.model||''};
          });
          if(!window.KaguyaAPI) throw new Error('api_client_unavailable');
          window.KaguyaAPI.json('/external/config', backendCfg).catch(function(){});
          var activeCfg=cfg[activeProvider]||{};
          if(activeCfg.apiKey){
            var bindPayload={device_id:generateDeviceId(),provider:activeProvider,apiKey:activeCfg.apiKey,apiUrl:activeCfg.apiUrl||API_PROVIDERS[activeProvider].url,model:activeCfg.model||API_PROVIDERS[activeProvider].models[0].id};
            var bindData = await window.KaguyaAPI.bindDeviceConfig(bindPayload);
            if(bindData&&bindData.success){
              activeCfg.hasSavedKey=true;
              activeCfg.masked_api_key=bindData.masked_api_key||bindData.api_key||bindData.apiKey||'';
              activeCfg.apiKey='';
              cfg[activeProvider]=activeCfg;
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
            if(providers[pv].enabled&&providers[pv].apiKey){
                _currentApiProvider=pv;
                localStorage.setItem('active_api_provider',pv);
            }
            try{
              await saveApiProviders(providers);
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
        function saveDeepSeek(){ saveApiProvider('deepseek'); }
        function testDeepSeek(){ testApiConnection('deepseek'); }
        
        function checkExternalApiWarning() {
            const hasActiveApi = getActiveApiConfig() !== null;
            const hasShownWarning = sessionStorage.getItem('api_warning_shown');
            if (!hasActiveApi && !hasShownWarning) {
                showApiWarningModal('未配罎外部AI API，部分高级功能将无法使用');
                sessionStorage.setItem('api_warning_shown', 'true');
            }
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
        
        async function sendDeepSeekMessage(msg, input) {
            const sendBtn = $('sendBtn');
            const stopBtn = $('stopBtn');
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
            
            const container = $('messagesContainer');
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
                if (!window.KaguyaStream) throw new Error('stream_helper_unavailable');
                await window.KaguyaStream.postSSE('/deepseek/chat', {
                        apiKey: deepseekConfig.apiKey,
                        apiUrl: deepseekConfig.apiUrl,
                        model: deepseekConfig.model,
                        messages: messages
                    }, {
                    onReader: function(reader) { currentReader = reader; },
                    shouldStop: function() { return !currentReader; },
                    onFrame: function(data) {
                        if (data.content) {
                            fullContent += data.content;
                            contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
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
                            chat.messages.push({role: 'assistant', content: fullContent, reasoning: fullReasoning, time: replyTime});
                            history[history.length - 1][1] = fullContent;
                            saveChats();
                        }
                    }
                });
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

        function switchPermSub(sub, btnEl) {
            var subs = ['Mode', 'Denials', 'Audit', 'Rules', 'Safety'];
            subs.forEach(function(s) {
                var el = document.getElementById('permSub' + s);
                if (el) el.style.display = 'none';
            });
            var target = document.getElementById('permSub' + sub.charAt(0).toUpperCase() + sub.slice(1));
            if (target) target.style.display = '';
            var container = btnEl ? btnEl.parentElement : document.querySelector('#permissionsTab .memory-filter-btn');
            if (container) {
                (container.parentElement || container).querySelectorAll('.memory-filter-btn').forEach(function(b) { b.classList.remove('active'); });
            }
            if (btnEl) btnEl.classList.add('active');
            if (sub === 'mode') loadPermMode();
            if (sub === 'denials') loadPermDenials();
            if (sub === 'audit') loadPermAudit();
            if (sub === 'rules') loadPermRules();
            if (sub === 'safety') loadCmdAllowlist();
        }

        function loadPermMode() {
            fetch('/agent/v2/permissions/mode').then(r=>r.json()).then(function(data) {
                var modeEl = document.getElementById('permCurrentMode');
                if (modeEl) modeEl.textContent = data.global_mode || 'unknown';
                var grid = document.getElementById('permModeGrid');
                if (grid && data.available_modes) {
                    grid.innerHTML = '';
                    data.available_modes.forEach(function(m) {
                        var isActive = m.id === data.global_mode;
                        var card = document.createElement('div');
                        card.style.cssText = 'padding:8px;border-radius:8px;border:1px solid ' + (isActive ? 'var(--accent)' : 'var(--border)') + ';background:' + (isActive ? 'rgba(16,185,129,0.1)' : 'var(--bg-secondary)') + ';cursor:pointer;transition:all 0.15s;';
                        card.innerHTML = '<div style="font-size:12px;font-weight:600;color:var(--text-primary);">' + m.name + '</div><div style="font-size:10px;color:var(--text-muted);margin-top:2px;">' + m.description + '</div>';
                        card.onclick = function() { setPermMode(m.id); };
                        grid.appendChild(card);
                    });
                }
            }).catch(function(){});
            fetch('/agent/v2/permissions/stats').then(r=>r.json()).then(function(data) {
                var grid = document.getElementById('permStatsGrid');
                if (grid) {
                    var items = [
                        {label:'总请求',value:data.total_requests||0,color:'#3b82f6'},
                        {label:'自动批准',value:data.auto_approved||0,color:'#10b981'},
                        {label:'用户批准',value:data.user_approved||0,color:'#8b5cf6'},
                        {label:'拒绝',value:data.rejected||0,color:'#ef4444'},
                        {label:'待处理',value:data.pending||0,color:'#f59e0b'},
                        {label:'管道版本',value:data.pipeline_version||'2.0',color:'#6b7280'},
                    ];
                    grid.innerHTML = '';
                    items.forEach(function(item) {
                        var card = document.createElement('div');
                        card.style.cssText = 'padding:6px 8px;border-radius:6px;background:var(--bg-secondary);border:1px solid var(--border);';
                        card.innerHTML = '<div style="font-size:10px;color:var(--text-muted);">' + item.label + '</div><div style="font-size:14px;font-weight:700;color:' + item.color + ';">' + item.value + '</div>';
                        grid.appendChild(card);
                    });
                }
            }).catch(function(){});
            loadPermPending();
        }

        function setPermMode(modeId) {
            fetch('/agent/v2/permissions/mode', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:modeId})}).then(r=>r.json()).then(function(data) {
                if (data.status === 'ok') loadPermMode();
            }).catch(function(){});
        }

        function loadPermPending() {
            fetch('/agent/v2/permissions/pending').then(r=>r.json()).then(function(data) {
                var list = document.getElementById('permPendingList');
                if (list) {
                    list.innerHTML = '';
                    var pending = data.pending || [];
                    if (pending.length === 0) {
                        list.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:8px;text-align:center;">暂无待审批请求</div>';
                    } else {
                        pending.forEach(function(p) {
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg-secondary);';
                            card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:12px;font-weight:600;color:var(--text-primary);">' + (p.tool_name||'unknown') + '</span><span style="font-size:10px;padding:2px 6px;border-radius:4px;background:' + (p.risk_level==='critical'?'#ef4444':p.risk_level==='high'?'#f59e0b':'#10b981') + ';color:#fff;">' + (p.risk_level||'unknown') + '</span></div><div style="font-size:10px;color:var(--text-muted);margin-top:4px;">' + (p.reason||'') + '</div><div style="display:flex;gap:4px;margin-top:6px;"><button data-rid="' + p.request_id + '" data-act="allow" class="perm-respond-btn" style="flex:1;padding:4px;border-radius:4px;background:#10b981;color:#fff;border:none;cursor:pointer;font-size:11px;">允许</button><button data-rid="' + p.request_id + '" data-act="allow_always" class="perm-respond-btn" style="flex:1;padding:4px;border-radius:4px;background:#3b82f6;color:#fff;border:none;cursor:pointer;font-size:11px;">始终允许</button><button data-rid="' + p.request_id + '" data-act="deny" class="perm-respond-btn" style="flex:1;padding:4px;border-radius:4px;background:#ef4444;color:#fff;border:none;cursor:pointer;font-size:11px;">拒绝</button></div>';
                            list.appendChild(card);
                        });
                    }
                }
            }).catch(function(){});
        }

        function respondPerm(requestId, decision) {
            fetch('/agent/v2/permissions/respond', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:requestId,decision:decision})}).then(r=>r.json()).then(function(data) {
                loadPermPending();
            }).catch(function(){});
        }

        document.addEventListener('click', function(e) {
            var btn = e.target.closest('.perm-respond-btn');
            if (btn) {
                var rid = btn.getAttribute('data-rid');
                var act = btn.getAttribute('data-act');
                if (rid && act) respondPerm(rid, act);
            }
        });

        function loadPermDenials() {
            fetch('/agent/v2/permissions/denials?limit=20').then(r=>r.json()).then(function(data) {
                var statsEl = document.getElementById('permDenialStats');
                if (statsEl && data.stats) {
                    var s = data.stats;
                    statsEl.innerHTML = '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;"><div style="padding:4px 8px;border-radius:4px;background:var(--bg-secondary);text-align:center;"><div style="font-size:10px;color:var(--text-muted);">总拒绝</div><div style="font-size:14px;font-weight:700;color:#ef4444;">' + (s.total_denials||0) + '</div></div><div style="padding:4px 8px;border-radius:4px;background:var(--bg-secondary);text-align:center;"><div style="font-size:10px;color:var(--text-muted);">连续拒绝</div><div style="font-size:14px;font-weight:700;color:#f59e0b;">' + (s.consecutive_denials||0) + '</div></div><div style="padding:4px 8px;border-radius:4px;background:var(--bg-secondary);text-align:center;"><div style="font-size:10px;color:var(--text-muted);">需升级</div><div style="font-size:14px;font-weight:700;color:' + (s.should_escalate?'#ef4444':'#10b981') + ';">' + (s.should_escalate?'是':'否') + '</div></div></div>';
                }
                var list = document.getElementById('permDenialList');
                if (list) {
                    list.innerHTML = '';
                    var records = data.records || [];
                    if (records.length === 0) {
                        list.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:8px;text-align:center;">暂无拒绝记录</div>';
                    } else {
                        records.reverse().forEach(function(r) {
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg-secondary);';
                            card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:11px;font-weight:600;color:var(--text-primary);">' + (r.tool_name||'') + '</span><span style="font-size:9px;padding:1px 6px;border-radius:3px;background:#ef4444;color:#fff;">' + (r.reason_code||'') + '</span></div><div style="font-size:10px;color:var(--text-muted);margin-top:2px;">' + (r.reason_description||'') + '</div><div style="font-size:9px;color:var(--text-muted);margin-top:2px;">步骤:' + (r.pipeline_step||'') + ' | 路径:' + (r.resource_path||'') + ' | 规则:' + (r.policy_rule_id||'') + '</div>';
                            list.appendChild(card);
                        });
                    }
                }
            }).catch(function(){});
        }

        function loadPermAudit() {
            fetch('/agent/v2/permissions/audit?limit=30').then(r=>r.json()).then(function(data) {
                var list = document.getElementById('permAuditList');
                if (list) {
                    list.innerHTML = '';
                    var entries = data.entries || [];
                    if (entries.length === 0) {
                        list.innerHTML = '<div style="font-size:11px;color:var(--text-muted);padding:8px;text-align:center;">暂无审计记录</div>';
                    } else {
                        entries.reverse().forEach(function(e) {
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg-secondary);';
                            var decColor = e.decision==='allow'?'#10b981':e.decision==='deny'?'#ef4444':'#6b7280';
                            card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:11px;font-weight:600;color:var(--text-primary);">' + (e.tool_name||'') + '</span><span style="font-size:9px;padding:1px 6px;border-radius:3px;background:' + decColor + ';color:#fff;">' + (e.decision||'') + '</span></div><div style="font-size:10px;color:var(--text-muted);margin-top:2px;">' + (e.reason||'') + '</div><div style="font-size:9px;color:var(--text-muted);margin-top:2px;">' + (e.auto_approved?'🤖 自动':'👤 手动') + ' | 步骤:' + (e.pipeline_step||'') + ' | ' + (e.timestamp||'') + '</div>';
                            list.appendChild(card);
                        });
                    }
                }
            }).catch(function(){});
        }

        function loadPermRules() {
            fetch('/agent/v2/permissions/rules').then(r=>r.json()).then(function(data) {
                var list = document.getElementById('permRulesList');
                if (list) {
                    list.innerHTML = '';
                    var rules = data.rules || [];
                    rules.forEach(function(r) {
                        var card = document.createElement('div');
                        card.style.cssText = 'padding:6px 8px;border-radius:6px;border:1px solid var(--border);background:var(--bg-secondary);';
                        var decColor = r.decision==='allow'?'#10b981':r.decision==='deny'?'#ef4444':'#f59e0b';
                        card.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;"><span style="font-size:11px;font-weight:600;color:var(--text-primary);">' + (r.tool_name||'*') + ' → ' + (r.pattern||'*') + '</span><span style="font-size:9px;padding:1px 6px;border-radius:3px;background:' + decColor + ';color:#fff;">' + (r.decision||'') + '</span></div><div style="font-size:9px;color:var(--text-muted);margin-top:2px;">来源:' + (r.source||'') + ' | 优先级:' + (r.priority||0) + ' | ' + (r.description||'') + '</div>';
                        list.appendChild(card);
                    });
                }
            }).catch(function(){});
        }

        function showAddRuleDialog() {
            var toolName = prompt('工具名称 (如 Bash, Edit, *):');
            if (!toolName) return;
            var pattern = prompt('匹配模式 (如 /path/*, *):', '*');
            var decision = prompt('决策 (allow, deny, ask):', 'ask');
            if (!decision) return;
            fetch('/agent/v2/permissions/rules', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:toolName,pattern:pattern,decision:decision,source:'user',description:'User added rule'})}).then(r=>r.json()).then(function(data) {
                if (data.status === 'ok') loadPermRules();
            }).catch(function(){});
        }

        function checkCmdSafety() {
            var cmd = document.getElementById('cmdSafetyInput').value;
            if (!cmd) return;
            fetch('/agent/v2/command-safety', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd})}).then(r=>r.json()).then(function(data) {
                var resultEl = document.getElementById('cmdSafetyResult');
                if (resultEl) {
                    resultEl.style.display = '';
                    var color = data.is_safe ? '#10b981' : '#ef4444';
                    var icon = data.is_safe ? '✅' : '❌';
                    var html = '<div style="font-size:13px;font-weight:600;color:' + color + ';">' + icon + ' ' + (data.is_safe ? '安全' : '不安全') + '</div>';
                    if (data.reason) html += '<div style="font-size:11px;color:var(--text-muted);margin-top:4px;">原因: ' + data.reason + '</div>';
                    html += '<div style="font-size:10px;color:var(--text-muted);margin-top:4px;">可分类: ' + (data.classifiable ? '是' : '否') + ' | 只读: ' + (data.is_read_only ? '是' : '否') + '</div>';
                    resultEl.innerHTML = html;
                }
            }).catch(function(){});
        }

        function loadCmdAllowlist() {
            var list = document.getElementById('cmdAllowlist');
            if (list) {
                var cmds = ['ls','dir','cat','head','tail','grep','rg','find','git','python','python3','pip','npm','node','go','cargo','curl','wget','tree','file','stat','ps','df','du','echo','pwd','whoami','hostname','date','uname','env','which','diff','sort','uniq','wc','javac','java','rustc'];
                list.innerHTML = '';
                cmds.forEach(function(cmd) {
                    var tag = document.createElement('span');
                    tag.style.cssText = 'font-size:10px;padding:2px 8px;border-radius:4px;background:rgba(16,185,129,0.1);color:#10b981;border:1px solid rgba(16,185,129,0.3);';
                    tag.textContent = cmd;
                    list.appendChild(tag);
                });
            }
        }
        
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

        function analyzeProjectStructure() {
            var path = prompt('输入项目路径:', 'D:\\claude-code-main\\claude-code-main');
            if (!path) return;
            fetch('/agent/file-analyzer/analyze', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:path})}).then(r=>r.json()).then(function(data) {
                if (data.error) { alert('Error: ' + data.error); return; }
                localStorage.setItem('lastAnalyzedProject', path);
                var statsEl = document.getElementById('fileAnalyzerStats');
                if (statsEl) {
                    var cats = data.categories || {};
                    var items = [
                        {label:'总文件',value:data.total_files,color:'#3b82f6'},
                        {label:'源文件',value:cats.source||0,color:'#10b981'},
                        {label:'配置',value:cats.config||0,color:'#f59e0b'},
                        {label:'测试',value:cats.test||0,color:'#8b5cf6'},
                        {label:'文档',value:cats.documentation||0,color:'#06b6d4'},
                        {label:'耗时',value:data.analysis_time_ms+'ms',color:'#6b7280'},
                    ];
                    statsEl.innerHTML = '';
                    items.forEach(function(item) {
                        var card = document.createElement('div');
                        card.style.cssText = 'padding:6px;border-radius:6px;background:var(--bg-secondary);border:1px solid var(--border);text-align:center;';
                        card.innerHTML = '<div style="font-size:9px;color:var(--text-muted);">' + item.label + '</div><div style="font-size:14px;font-weight:700;color:' + item.color + ';">' + item.value + '</div>';
                        statsEl.appendChild(card);
                    });
                }
                loadFileTree(path);
                loadStructureRecs();
            }).catch(function(e){ alert('Error: ' + e); });
        }

        function loadFileTree(projectPath) {
            fetch('/agent/file-analyzer/tree?path=' + encodeURIComponent(projectPath) + '&depth=3').then(r=>r.json()).then(function(data) {
                var container = document.getElementById('fileTreeContainer');
                if (container) {
                    container.innerHTML = '';
                    container.appendChild(renderTree(data));
                }
            }).catch(function(){});
        }

        function renderTree(node, depth) {
            depth = depth || 0;
            var el = document.createElement('div');
            el.style.marginLeft = (depth * 16) + 'px';
            if (node.type === 'directory') {
                var header = document.createElement('div');
                header.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 4px;border-radius:4px;cursor:pointer;font-size:12px;color:var(--text-primary);';
                header.innerHTML = '📁 ' + node.name;
                header.onmouseover = function(){ this.style.background='var(--bg-secondary)'; };
                header.onmouseout = function(){ this.style.background=''; };
                el.appendChild(header);
                var childContainer = document.createElement('div');
                childContainer.style.display = 'none';
                if (node.children) {
                    node.children.forEach(function(child) {
                        childContainer.appendChild(renderTree(child, depth + 1));
                    });
                }
                header.onclick = function() {
                    childContainer.style.display = childContainer.style.display === 'none' ? '' : 'none';
                };
                el.appendChild(childContainer);
            } else {
                var catIcons = {source:'📄',header:'📋',config:'⚙️',documentation:'📖',test:'🧪',build:'🔨',asset:'🖼️',data:'💾',script:'📜',style:'🎨',template:'📝',other:'📎'};
                var icon = catIcons[node.category] || '📎';
                var fileEl = document.createElement('div');
                fileEl.style.cssText = 'display:flex;align-items:center;gap:4px;padding:2px 4px;border-radius:4px;font-size:11px;color:var(--text-secondary);';
                var sizeStr = node.size ? (' (' + (node.size < 1024 ? node.size + 'B' : (node.size / 1024).toFixed(1) + 'KB') + ')') : '';
                var lineStr = node.lines ? (' ' + node.lines + '行') : '';
                fileEl.innerHTML = icon + ' ' + node.name + '<span style="font-size:9px;color:var(--text-muted);">' + sizeStr + lineStr + '</span>';
                fileEl.onmouseover = function(){ this.style.background='var(--bg-secondary)'; };
                fileEl.onmouseout = function(){ this.style.background=''; };
                el.appendChild(fileEl);
            }
            return el;
        }

        function loadFileDeps() {
            var path = document.getElementById('depFilePath').value;
            var projectPath = localStorage.getItem('lastAnalyzedProject') || '';
            if (!projectPath) { alert('请先分析项目'); return; }
            fetch('/agent/file-analyzer/dependencies?path=' + encodeURIComponent(projectPath) + '&file=' + encodeURIComponent(path) + '&depth=2').then(r=>r.json()).then(function(data) {
                var container = document.getElementById('fileDepContainer');
                if (container) {
                    container.innerHTML = '';
                    var edges = data.edges || [];
                    if (edges.length === 0) {
                        container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:8px;">无依赖关系</div>';
                    } else {
                        edges.forEach(function(e) {
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:4px 8px;border-radius:6px;background:var(--bg-secondary);border:1px solid var(--border);font-size:10px;';
                            card.innerHTML = '<span style="color:var(--text-primary);">' + (e.source||'').split('/').pop() + '</span> <span style="color:var(--accent);">→</span> <span style="color:var(--text-primary);">' + (e.target||'').split('/').pop() + '</span> <span style="color:var(--text-muted);">(' + (e.dep_type||'import') + ')</span>';
                            container.appendChild(card);
                        });
                    }
                }
            }).catch(function(){});
        }

        function loadStructureRecs() {
            var projectPath = localStorage.getItem('lastAnalyzedProject') || '';
            if (!projectPath) return;
            fetch('/agent/file-analyzer/recommendations?path=' + encodeURIComponent(projectPath)).then(r=>r.json()).then(function(data) {
                var container = document.getElementById('structureRecsContainer');
                if (container) {
                    container.innerHTML = '';
                    var recs = data.recommendations || [];
                    if (recs.length === 0) {
                        container.innerHTML = '<div style="font-size:11px;color:var(--text-muted);text-align:center;padding:8px;">✅ 项目结构良好，无优化建议</div>';
                    } else {
                        recs.forEach(function(r) {
                            var sevColors = {error:'#ef4444',warning:'#f59e0b',info:'#3b82f6'};
                            var card = document.createElement('div');
                            card.style.cssText = 'padding:8px;border-radius:8px;border:1px solid var(--border);background:var(--bg-secondary);';
                            card.innerHTML = '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;"><span style="font-size:9px;padding:1px 6px;border-radius:3px;background:' + (sevColors[r.severity]||'#6b7280') + ';color:#fff;">' + (r.severity||'info') + '</span><span style="font-size:12px;font-weight:600;color:var(--text-primary);">' + (r.title||'') + '</span></div><div style="font-size:10px;color:var(--text-muted);">' + (r.description||'') + '</div>' + (r.suggestion ? '<div style="font-size:10px;color:var(--accent);margin-top:4px;">💡 ' + r.suggestion + '</div>' : '');
                            container.appendChild(card);
                        });
                    }
                }
            }).catch(function(){});
        }

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
