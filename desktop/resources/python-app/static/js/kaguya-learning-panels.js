// Learning, multimodal vision, and memory panels extracted from the main shell.
        function learningGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function learningPost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
        }

        function learningDelete(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.del(path);
        }

        function learningPut(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.put(path, payload || {});
        }
        // ==================== 模型微调平台 ====================
        function refreshFinetuneData() {
            loadFinetuneDatasets();
            loadFinetuneJobs();
        }
        
        function loadFinetuneDatasets() {
            learningGet('/finetune/datasets').then(data => {
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
            learningGet('/finetune/jobs').then(data => {
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
            input.onchange = async function(e) {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('name', name);
                formData.append('format', file.name.split('.').pop());
                
                try {
                    if (!window.KaguyaUpload) throw new Error('upload_helper_unavailable');
                    const data = await window.KaguyaUpload.uploadForm('/finetune/dataset/upload', formData);
                    if (data.success) {
                        showToast(`数据集上传成功，包含 ${data.sample_count} 个样本`);
                        loadFinetuneDatasets();
                    } else {
                        showToast('上传失败: ' + window.KaguyaUpload.summarizeError(data), 'error');
                    }
                } catch (err) {
                    showToast('上传失败: ' + (window.KaguyaUpload ? window.KaguyaUpload.summarizeError(err) : (err.message || err)), 'error');
                }
            };
            input.click();
        }
        
        function showCreateJob() {
            console.log('showCreateJob called');
            const name = prompt('训练任务名称:');
            if (!name) return;
            
            learningGet('/finetune/datasets').then(data => {
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
                
                learningPost('/finetune/job', {name, dataset_id: dataset.id, config}).then(data => {
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
            learningPost(`/finetune/job/${jobId}/start`).then(data => {
                if (data.success) {
                    showToast('训练已开始');
                    loadFinetuneJobs();
                } else {
                    showToast('启动失败: ' + (data.error || '未知错误'));
                }
            });
        }
        
        function stopFinetuneJob(jobId) {
            learningPost(`/finetune/job/${jobId}/stop`).then(data => {
                if (data.success) {
                    showToast('训练已停止');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneJob(jobId) {
            if (!confirm('确定要删除这个训练任务吗？')) return;
            
            learningDelete(`/finetune/job/${jobId}`).then(data => {
                if (data.success) {
                    showToast('训练任务已删除');
                    loadFinetuneJobs();
                }
            });
        }
        
        function deleteFinetuneDataset(datasetId) {
            if (!confirm('确定要删除这个数据集吗？')) return;
            
            learningDelete(`/finetune/dataset/${datasetId}`).then(data => {
                if (data.success) {
                    showToast('数据集已删除');
                    loadFinetuneDatasets();
                }
            });
        }
        
        // ==================== 多模态视觉理解系统 ====================
        let currentMultimodalImage = null;
        let currentImageId = null;
        
        async function uploadMultimodalImage(event) {
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
            
            try {
                if (!window.KaguyaUpload) throw new Error('upload_helper_unavailable');
                const data = await window.KaguyaUpload.uploadForm('/multimodal/upload', formData);
                if (data.success) {
                    currentImageId = data.result.image_id;
                    showToast('图片上传成功');
                } else {
                    showToast('上传失败: ' + window.KaguyaUpload.summarizeError(data), 'error');
                }
            } catch (err) {
                showToast('上传失败: ' + (window.KaguyaUpload ? window.KaguyaUpload.summarizeError(err) : (err.message || err)), 'error');
            }
        }
        
        function analyzeImage(task) {
            if (!currentImageId) {
                showToast('请先上传图片');
                return;
            }
            
            learningPost('/multimodal/analyze', {image_id: currentImageId, task: task}).then(data => {
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
        
        function loadVisionHistory() {
            learningGet('/multimodal/history').then(data => {
                if (data.success && data.history.length > 0) {
                    // 可以在这里显示历史记录
                }
            });
        }
        
        function clearMultimodalHistory() {
            if (!confirm('确定要清除所有分析结果吗？')) return;
            
            learningPost('/multimodal/clear').then(data => {
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
            learningGet('/memory/stats').then(data => {
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
            
            learningPost('/memory/search', body).then(data => {
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
            learningPut(`/memory/${memoryId}/pin`).then(data => {
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
            
            learningPost('/memory', {content, type, category, pinned}).then(data => {
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
            
            learningDelete(`/memory/${memoryId}`).then(data => {
                if (data.success) {
                    showToast('记忆已删除');
                    searchMemories();
                    refreshMemoryStats();
                }
            });
        }
        
        function consolidateMemories() {
            if (!confirm('Consolidate memories? This will clean outdated and low-importance memories (pinned memories will not be cleaned).')) return;
            
            learningPost('/memory/consolidate').then(data => {
                if (data.success) {
                    showToast('记忆整合完成');
                    refreshMemoryStats();
                    searchMemories();
                }
            });
        }
