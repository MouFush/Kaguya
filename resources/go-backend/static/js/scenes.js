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
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}, device_id: generateDeviceId()})
            }).then(() => {
                fetch('/scenes/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({scene_id: sceneId, provider, fields, device_id: generateDeviceId()})
                }).then(r => r.json()).then(data => {
                    if (!data.success) {
                        if (outputEl) outputEl.textContent = `生成失败：${data.error || '未知错误'}`;
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
            fetch('/scenes/history?scene_id=' + currentSceneId).then(r => r.json()).then(data => {
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
            fetch('/scenes/history', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    sceneHistoryList = [];
                    renderSceneHistoryPanel();
                    showToast('历史记录已清空');
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
            fetch('/external/config?device_id='+generateDeviceId()).then(r => r.json()).then(data => {
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
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}, device_id: generateDeviceId()})
            }).then(r => r.json()).then(data => {
                if (!data.success) {
                    if (statusEl) statusEl.textContent = `保存失败: ${data.error || '未知错误'}`;
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
            fetch('/external/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({active_provider: provider, providers: externalApiConfig.providers || {}, device_id: did})
            }).then(() => {
                fetch('/external/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({provider, device_id: did})
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
        
