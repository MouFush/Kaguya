function loadRagDocuments() {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.get('/rag/documents').then(data => {
                if (data.success) {
                    ragDocuments = data.documents;
                    renderRagDocList();
                    updateRagStats();
                    renderFeatureCenterMeta();
                } else if (data.error) {
                    console.warn('RAG documents unavailable:', data);
                }
            });
        }
        
        function updateRagStats() {
            if (!window.KaguyaAPI) return;
            window.KaguyaAPI.get('/rag/stats').then(data => {
                if (data.success) {
                    const stats = data.stats;
                    const docsEl = $('ragStatDocs');
                    const chunksEl = $('ragStatChunks');
                    const charsEl = $('ragStatChars');
                    if (docsEl) docsEl.textContent = stats.total_docs;
                    if (chunksEl) chunksEl.textContent = stats.total_chunks;
                    if (charsEl) charsEl.textContent = stats.total_chars > 1000 ? (stats.total_chars/1000).toFixed(1) + 'K' : stats.total_chars;
                    const ragStatsEl = document.getElementById('ragStats');
                    const cacheInfo = stats.cache_size > 0 ? ` | 💾 缓存: ${stats.cache_size}` : '';
                    if (ragStatsEl) ragStatsEl.title = `唯一文档: ${stats.unique_hashes || 0}${cacheInfo}`;
                } else if (data.error) {
                    console.warn('RAG stats unavailable:', data);
                }
            });
        }
        
        function renderRagDocList() {
            const list = $('ragDocList');
            const filter = $('ragCategoryFilter').value;
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
                        <span style="flex:1;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
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
            const ragToggle=$('ragToggle'); ragEnabled = ragToggle ? ragToggle.checked : false;
            updateRagIndicator();
            renderFeatureCenterMeta();
            showToast(ragEnabled ? 'RAG已启用 - 将基于文档回答' : 'RAG已禁用');
        }
        
        function updateRagIndicator() {
            const indicators = $('headerIndicators');
            let html = indicators.innerHTML;
            const ragIndicator = '<div class="indicator tool"><span>📚</span><span>RAG</span></div>';
            if (ragEnabled && !html.includes('RAG')) {
                indicators.innerHTML = ragIndicator + html;
            } else if (!ragEnabled) {
                indicators.innerHTML = html.replace(ragIndicator, '');
            }
        }
        
        async function uploadRagFile(event) {
            const files = event.target.files;
            if (!files || !files.length) return;
            try {
                if (!window.KaguyaUpload) throw new Error('upload_helper_unavailable');
                if (files.length === 1) {
                    const file = files[0];
                    const formData = new FormData();
                    formData.append('file', file, file.name);
                    showToast('正在上传: ' + file.name);
                    const data = await window.KaguyaUpload.uploadForm('/rag/upload', formData);
                    if (data.success) {
                        showToast('上传成功: ' + ((data.document && data.document.filename) || file.name));
                        loadRagDocuments();
                    } else {
                        showToast('上传失败: ' + window.KaguyaUpload.summarizeError(data), 'error');
                    }
                } else {
                    showToast(`正在上传 ${files.length} 个文件...`);
                    const data = await window.KaguyaUpload.uploadFiles('/rag/batch_upload', files, {
                        onProgress: function(info) { showToast(`正在上传第 ${info.batch}/${info.totalBatches} 批...`); },
                        stopOnError: false,
                    });
                    if (data.success) {
                        const rawResults = data.results || [];
                        const success = rawResults.reduce(function(total, item) {
                            if (item && item.success === false) return total;
                            if (item && Array.isArray(item.results)) return total + item.results.filter(r => r.success !== false).length;
                            return total + 1;
                        }, 0);
                        showToast(`上传完成: ${success}/${files.length} 成功`);
                        loadRagDocuments();
                    } else {
                        showToast('上传失败: ' + window.KaguyaUpload.summarizeError(data), 'error');
                    }
                }
            } catch(e) {
                showToast('上传失败: ' + (window.KaguyaUpload ? window.KaguyaUpload.summarizeError(e) : (e.message || e)), 'error');
            } finally {
                event.target.value = '';
            }
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
            const title = $('addTextTitle').value.trim() || '手动输入';
            const content = $('addTextContent').value.trim();
            const tags = $('addTextTags').value.split(',').map(t => t.trim()).filter(t => t);
            
            if (content.length < 50) {
                showToast('内容至少需要50个字符');
                return;
            }
            
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/rag/add_text', {text: content, title, tags}).then(data => {
                if (data.success) {
                    showToast('文本已添加到知识库');
                    closeModal();
                    loadRagDocuments();
                } else {
                    showToast('添加失败: ' + (data.message || data.error || '未知错误'));
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
                const overlay = $('modalOverlay');
                if (overlay) overlay.classList.remove('show');
            }
        }
        
        function showModal(html) {
            const overlay = $('modalOverlay');
            overlay.querySelector('.modal').innerHTML = html;
            overlay.classList.add('show');
        }
        
        function deleteRagDoc(docId) {
            if (!confirm('确定删除此文档？相关分块也将被删除。')) return;
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.del('/rag/delete/' + docId)
                .then(data => {
                    if (data.success) {
                        showToast('文档已删除');
                        loadRagDocuments();
                    } else {
                        showToast('删除失败: ' + (data.message || data.error || '未知错误'), 'error');
                    }
                });
        }
        
        function searchRagDocs() {
            const query = $('ragSearchInput').value.trim();
            const resultsDiv = $('ragSearchResults');
            if (!query) {
                resultsDiv.innerHTML = '';
                return;
            }
            const category = $('ragCategoryFilter').value;
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.json('/rag/search', {
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
                }).then(data => {
                if (data.success && data.results.length) {
                    lastRagResults = data.results;
                    var qualityHtml = data.quality ? '<div style="font-size:9px;color:var(--text-muted);margin-bottom:8px;">类型: ' + data.query_type + ' | 质量: ' + data.quality.reason + ' (' + data.quality.score + ')</div>' : '';
                    var resultsHtml = '';
                    for (var i = 0; i < data.results.length; i++) {
                        var r = data.results[i];
                        var textPreview = r.text.length > 120 ? r.text.slice(0, 120) + '...' : r.text;
            textPreview = textPreview.replace(/<\//g, '&lt;').replace(/>/g, '&gt;');
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
                    const msg = data.error ? ('搜索失败: ' + (data.message || data.error)) : '未找到相关内容';
                    resultsDiv.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:10px;">' + escapeHtml(msg) + '</div>';
                }
            });
        }
        
        function useRagResult(text) {
            const input = $('mainInput');
            input.value = '基于以下内容回答: ' + text + '\n\n问题: ';
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
                            style="width:100%;" oninput="$('topKValue').textContent=this.value">
                    </div>
                    <div style="margin-bottom:12px;">
                        <label style="font-size:12px;color:var(--text-secondary);display:block;margin-bottom:6px;">
                            TF-IDF权重: <b id="alphaValue">${ragSettings.alpha}</b>
                        </label>
                        <input type="range" id="ragAlpha" min="0" max="100" value="${ragSettings.alpha * 100}" 
                            style="width:100%;" oninput="$('alphaValue').textContent=(this.value/100).toFixed(2)">
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
            ragSettings.topK = parseInt($('ragTopK').value);
            ragSettings.alpha = parseInt($('ragAlpha').value) / 100;
            ragSettings.useRerank = $('ragRerank').checked;
            ragSettings.showScores = $('ragShowScores').checked;
            ragSettings.useCache = $('ragCache').checked;
            ragSettings.useExpansion = $('ragExpansion').checked;
            ragSettings.useHyde = $('ragHyde').checked;
            ragSettings.useMultiQuery = $('ragMultiQuery').checked;
            ragSettings.useDecomposition = $('ragDecomposition').checked;
            ragSettings.useAdaptive = document.getElementById('ragAdaptive').checked;
            ragSettings.useRrf = document.getElementById('ragRrf').checked;
            ragSettings.useMetadataFilter = document.getElementById('ragMetadataFilter').checked;
            ragSettings.useTimeWeight = document.getElementById('ragTimeWeight').checked;
            ragSettings.useIterative = document.getElementById('ragIterative').checked;
            closeModal();
            showToast('RAG设置已保存');
        }
        
        function previewRagDoc(docId) {
            if (!window.KaguyaAPI) return showToast('API client unavailable');
            window.KaguyaAPI.get('/rag/preview/' + docId).then(data => {
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
                } else {
                    showToast('预览失败: ' + (data.message || data.error || '未知错误'), 'error');
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
        
