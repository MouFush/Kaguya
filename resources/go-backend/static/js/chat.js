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
            renderRoleList();
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
            fetch('/lora/list').then(r => r.json()).then(data => {
                document.getElementById('loraList').innerHTML = data.loras.map(l => {
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
            
            fetch('/web/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query, max_results: 10})
            }).then(function(r) { return r.json(); }).then(function(data) {
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
            
            fetch('/web/fetch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            }).then(function(r) { return r.json(); }).then(function(data) {
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
                        <span class="finetune-title">${escapeHtml(ds.name)}</span>
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
                        <span class="finetune-title">${escapeHtml(job.name)}</span>
                        <span class="finetune-status ${job.status}">${job.status}</span>
                    </div>
                    <div class="finetune-meta">
                        <span>方法: ${job.method}</span>
                        <span>数据: ${escapeHtml(job.dataset_name)}</span>
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
                
                const datasetOptions = data.datasets.map((ds, i) => `${i + 1}. ${escapeHtml(ds.name)} (${ds.sample_count}样本)`).join(String.fromCharCode(10));
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
        let currentMemoryFilter = 'all';
        
        function refreshMemoryStats() {
            fetch('/memory/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const longTermEl = document.getElementById('memLongTerm');
                    const pinnedEl = document.getElementById('memPinned');
                    const avgImpEl = document.getElementById('memAvgImportance');
                    const entitiesEl = document.getElementById('memEntities');
                    const profileEl = document.getElementById('memProfile');
                    if (longTermEl) longTermEl.textContent = data.stats.long_term_count;
                    if (pinnedEl) pinnedEl.textContent = data.stats.pinned_count;
                    if (avgImpEl) avgImpEl.textContent = data.stats.avg_importance;
                    if (entitiesEl) entitiesEl.textContent = data.stats.entity_count;
                    if (profileEl) profileEl.textContent = data.stats.profile_count;
                }
            });
        }
        
        function searchMemories() {
            const query = document.getElementById('memorySearchInput').value || 'all';
            const body = {query: query, top_k: 50};
            
            if (currentMemoryFilter === 'pinned') {
                body.pinned_only = true;
            } else if (currentMemoryFilter !== 'all') {
                body.memory_type = currentMemoryFilter;
            }
            
            fetch('/memory/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    renderMemoryList(data.memories);
                }
            });
        }
        
        function filterMemories(filter, btnEl) {
            currentMemoryFilter = filter;
            document.querySelectorAll('.memory-filter-btn').forEach(b => b.classList.remove('active'));
            if (btnEl) btnEl.classList.add('active');
            searchMemories();
        }
        
        function renderMemoryList(memories) {
            const container = document.getElementById('memoryList');
            if (!memories || memories.length === 0) {
                container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无记忆</div>';
                return;
            }
            
            const pinnedMemories = memories.filter(m => m.pinned);
            const unpinnedMemories = memories.filter(m => !m.pinned);
            const sortedMemories = [...pinnedMemories, ...unpinnedMemories];
            
            container.innerHTML = sortedMemories.map(m => {
                const importanceDots = Array(5).fill(0).map((_, i) => 
                    `<div class="importance-dot ${i < m.importance * 5 ? 'active' : ''}"></div>`
                ).join('');
                
                const date = new Date(m.created_at * 1000).toLocaleDateString();
                const pinnedClass = m.pinned ? ' pinned' : '';
                const pinnedBadge = m.pinned ? '<span class="memory-pinned-badge">📌 永久</span>' : '';
                const pinBtnClass = m.pinned ? 'memory-pin-btn unpin' : 'memory-pin-btn';
                const pinBtnText = m.pinned ? '📌 取消置顶' : '📌 置顶';
                
                return `
                    <div class="memory-item${pinnedClass}">
                        <div class="memory-content">${escapeHtml(m.content)}</div>
                        <div class="memory-meta">
                            <span class="memory-type ${m.type}">${m.type}</span>
                            ${pinnedBadge}
                            <span>📊</span>
                            <div class="memory-importance">${importanceDots}</div>
                            <span>🕐 ${date}</span>
                            <span>👁️ ${m.access_count}次</span>
                            <div class="memory-actions">
                                <button class="${pinBtnClass}" onclick="toggleMemoryPin('${m.id}', ${m.pinned})">${pinBtnText}</button>
                                <button class="memory-btn" onclick="deleteMemory('${m.id}')">🗑️</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function toggleMemoryPin(memoryId, currentPinned) {
            fetch(`/memory/${memoryId}/pin`, {method: 'PUT'}).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast(currentPinned ? '已取消置顶' : '已置顶为永久记忆');
                    searchMemories();
                    refreshMemoryStats();
                }
            });
        }
        
        function showAddMemoryModal() {
            const overlay = document.createElement('div');
            overlay.className = 'add-memory-modal-overlay';
            overlay.id = 'addMemoryModalOverlay';
            overlay.onclick = function(e) { if (e.target === overlay) closeAddMemoryModal(); };
            
            overlay.innerHTML = `
                <div class="add-memory-modal">
                    <h3>📝 添加记忆</h3>
                    <label>记忆内容</label>
                    <textarea id="addMemContent" placeholder="输入要记住的信息..."></textarea>
                    <label>记忆类型</label>
                    <select id="addMemType">
                        <option value="fact">事实 (fact)</option>
                        <option value="preference">偏好 (preference)</option>
                        <option value="experience">经历 (experience)</option>
                    </select>
                    <label>分类</label>
                    <select id="addMemCategory">
                        <option value="general">通用</option>
                        <option value="personal">个人信息</option>
                        <option value="work">工作</option>
                        <option value="study">学习</option>
                        <option value="hobby">爱好</option>
                        <option value="health">健康</option>
                        <option value="social">社交</option>
                    </select>
                    <div class="pin-toggle">
                        <label class="toggle"><input type="checkbox" id="addMemPinned"><span class="toggle-slider"></span></label>
                        <label style="margin:0;cursor:pointer;" onclick="document.getElementById('addMemPinned').click()">📌 Pin as permanent memory (will not be cleaned)</label>
                    </div>
                    <div class="modal-actions">
                        <button class="btn-cancel" onclick="closeAddMemoryModal()">取消</button>
                        <button class="btn-save" onclick="submitAddMemory()">💾 保存</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(overlay);
        }
        
        function closeAddMemoryModal() {
            const overlay = document.getElementById('addMemoryModalOverlay');
            if (overlay) overlay.remove();
        }
        
        function submitAddMemory() {
            const content = document.getElementById('addMemContent').value.trim();
            if (!content) { showToast('请输入记忆内容'); return; }
            
            const type = document.getElementById('addMemType').value;
            const category = document.getElementById('addMemCategory').value;
            const pinned = document.getElementById('addMemPinned').checked ? 1 : 0;
            
            fetch('/memory', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, type, category, pinned})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast(pinned ? '永久记忆已添加' : '记忆已添加');
                    closeAddMemoryModal();
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
            if (!confirm('Consolidate memories? This will clean outdated and low-importance memories (pinned memories will not be cleaned).')) return;
            
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
        
