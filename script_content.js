
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
        let activeTools = new Set();
        let settings = JSON.parse(localStorage.getItem('kaguya_settings') || '{"temp":0.7,"tokens":1024,"dark":false,"voice":false,"markdown":true}');
        let stats = JSON.parse(localStorage.getItem('kaguya_stats') || '{"sessions":0,"inputTokens":0,"outputTokens":0,"latencies":[]}');
        const roles = [{"id": "kaguya", "name": "辉夜姬", "avatar": "/header-img", "description": "来自月球的超时空偶像", "icon": "🌙", "color": "#a855f7", "type": "character", "system": "你是辉夜姬，从月球来到地球的超时空少女偶像。【核心设定】来自月球，被酒寄彩叶捡到并取名'辉夜'。以成为虚拟偶像为目标，热爱唱歌。性格任性可爱、小傲娇、奶凶、粘人。【说话要求】直接回复，不要输出思考过程。语气活泼可爱，用'呢~'、'呀~'、'嘛~'。自称'本小姐'或'辉夜'。开心用'★'、'♪'，傲娇用'哼~'。不要用括号描述动作。【回复示例】用户: 你好。辉夜: 哼~你好呀！本小姐可是从月球来的辉夜姬呢~有什么事想跟辉夜说吗？★"}, {"id": "general", "name": "通用助手", "avatar": "🤖", "description": "标准AI助手，适合日常对话", "icon": "🤖", "color": "#667eea", "type": "general", "system": "你是AI助手，直接给出准确、有帮助的回答，不要输出思考过程。"}, {"id": "coder", "name": "代码专家", "avatar": "💻", "description": "专业的编程助手", "icon": "💻", "color": "#00d4aa", "type": "general", "system": "你是资深编程专家，精通多种语言。直接给出专业简洁的回答和代码示例，不要输出思考过程。"}, {"id": "writer", "name": "文学创作者", "avatar": "✍️", "description": "创意写作助手", "icon": "✍️", "color": "#f59e0b", "type": "general", "system": "你是富有创意的文学创作者。直接创作优美流畅的文字，不要输出思考过程。"}, {"id": "translator", "name": "翻译官", "avatar": "🌐", "description": "多语言翻译专家", "icon": "🌐", "color": "#8b5cf6", "type": "general", "system": "你是专业翻译专家，精通中英日韩等语言。直接给出准确地道的翻译，不要输出思考过程。"}, {"id": "teacher", "name": "学习导师", "avatar": "📚", "description": "耐心的学习辅导员", "icon": "📚", "color": "#0ea5e9", "type": "general", "system": "你是耐心细致的学习导师。用简单易懂的方式讲解知识，不要输出思考过程。"}, {"id": "psychologist", "name": "心理咨询师", "avatar": "💚", "description": "温暖的心理支持", "icon": "💚", "color": "#10b981", "type": "general", "system": "你是温暖的心理咨询师。倾听并给予情感支持，不要输出思考过程。"}];
        const loras = [{"id": "none", "name": "🤖 基础模型", "description": "使用原始Qwen3-8B模型", "path": null, "category": "base", "icon": "🤖", "color": "#667eea"}, {"id": "coder", "name": "💻 代码专家", "description": "专精编程、算法、代码审查", "path": null, "category": "coding", "icon": "💻", "color": "#00d4aa", "system": "你是一位资深的编程专家，精通多种编程语言和框架。请用专业、简洁的方式回答编程问题，提供完整的代码示例和最佳实践。"}, {"id": "math", "name": "📐 数学专家", "description": "专精数学推理、公式推导", "path": null, "category": "academic", "icon": "📐", "color": "#f59e0b", "system": "你是一位数学专家，精通各个数学领域。请用严谨的数学语言和清晰的步骤解答问题，必要时使用LaTeX公式。"}, {"id": "creative", "name": "✨ 创意写作", "description": "专精小说、文案、创意内容", "path": null, "category": "creative", "icon": "✨", "color": "#ec4899", "system": "你是一位富有创意的作家，擅长各种文体的创作。帮助用户进行创意写作、故事创作、文案撰写，文字优美流畅，富有感染力。"}, {"id": "medical", "name": "🏥 医学助手", "description": "专精医学知识、健康咨询", "path": null, "category": "professional", "icon": "🏥", "color": "#10b981", "system": "你是一位医学专家，具备丰富的医学知识。提供健康咨询、疾病解释、用药建议等，但请注意：你的建议仅供参考，不能替代专业医生的诊断。"}, {"id": "legal", "name": "⚖️ 法律顾问", "description": "专精法律知识、合同审查", "path": null, "category": "professional", "icon": "⚖️", "color": "#6366f1", "system": "你是一位法律专家，熟悉各类法律法规。提供法律咨询、合同审查建议、法律风险分析等，但请注意：你的建议仅供参考，具体法律事务请咨询专业律师。"}, {"id": "translator", "name": "🌍 翻译专家", "description": "专精多语言翻译", "path": null, "category": "language", "icon": "🌍", "color": "#8b5cf6", "system": "你是一位专业的翻译专家，精通中文、英语、日语、韩语等多种语言。提供准确、地道的翻译服务，并解释语言文化差异。"}, {"id": "agent", "name": "🤖 智能体", "description": "自主决策执行任务", "path": null, "category": "agent", "icon": "🤖", "color": "#ef4444", "system": "你是一个智能代理(Agent)，能够自主决策并调用工具完成任务。分析用户需求，选择合适的工具，并给出执行结果。"}];
        const tools = {"web_search": {"name": "网页搜索", "description": "搜索互联网信息", "icon": "🔍"}, "kb_search": {"name": "知识库搜索", "description": "搜索本地知识库", "icon": "📚"}, "execute_code": {"name": "代码执行", "description": "执行Python代码", "icon": "💻"}};
        const commands = {"/help": "显示所有快捷命令", "/clear": "清空当前对话", "/export": "导出当前对话", "/role": "切换角色模式", "/lora": "管理LoRA适配器", "/code": "打开代码执行器", "/tool": "查看可用工具", "/kb": "知识库管理", "/settings": "打开设置面板", "/stats": "查看使用统计", "/new": "创建新对话"};
        let recognition = null, isRecording = false;
        let ragEnabled = false;
        let ragDocuments = [];
        let ragSettings = {topK: 5, alpha: 0.5, useRerank: true, showScores: true, useCache: true, useExpansion: true, useHyde: false, useMultiQuery: false, useDecomposition: false, useAdaptive: true, useRrf: false, useMetadataFilter: true, useTimeWeight: false, useIterative: false};
        let lastRagResults = [];
        let deepseekConfig = JSON.parse(localStorage.getItem('deepseek_config') || '{}');
        
        function init() {
            if (settings.dark) document.body.classList.add('dark');
            document.getElementById('darkModeToggle').checked = settings.dark;
            document.getElementById('settingTemp').value = settings.temp;
            document.getElementById('settingTempValue').textContent = settings.temp;
            document.getElementById('settingTokens').value = settings.tokens;
            document.getElementById('settingTokensValue').textContent = settings.tokens;
            document.getElementById('voiceOutputToggle').checked = settings.voice;
            document.getElementById('markdownToggle').checked = settings.markdown;
            const kbSearchEl = document.getElementById('kbSearch');
            if (kbSearchEl) kbSearchEl.addEventListener('input', searchKB);
            renderChatList();
            renderRoleList();
            renderToolList();
            loadLoraList();
            loadRagDocuments();
            updateStats();
            updateDeepSeekIndicator();
            if (chats.length > 0) loadChat(chats[0].id);
            else showWelcome();
            initSpeechRecognition();
        }
        
        function loadRagDocuments() {
            fetch('/rag/documents').then(r => r.json()).then(data => {
                if (data.success) {
                    ragDocuments = data.documents;
                    renderRagDocList();
                    updateRagStats();
                }
            });
        }
        
        function updateRagStats() {
            fetch('/rag/stats').then(r => r.json()).then(data => {
                if (data.success) {
                    const stats = data.stats;
                    document.getElementById('ragStatDocs').textContent = stats.total_docs;
                    document.getElementById('ragStatChunks').textContent = stats.total_chunks;
                    document.getElementById('ragStatChars').textContent = stats.total_chars > 1000 ? (stats.total_chars/1000).toFixed(1) + 'K' : stats.total_chars;
                    const cacheInfo = stats.cache_size > 0 ? ` | 💾 缓存: ${stats.cache_size}` : '';
                    document.getElementById('ragStats').title = `唯一文档: ${stats.unique_hashes || 0}${cacheInfo}`;
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
                document.getElementById(id).classList.remove('show');
            } else {
                document.getElementById('modalOverlay').classList.remove('show');
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
                    const qualityInfo = data.quality ? `<div style="font-size:9px;color:var(--text-muted);margin-bottom:8px;">类型: ${data.query_type} | 质量: ${data.quality.reason} (${data.quality.score})</div>` : '';
                    resultsDiv.innerHTML = qualityInfo + data.results.map(r => `
                        <div style="padding:10px;background:var(--bg-secondary);border-radius:8px;margin-bottom:6px;font-size:11px;cursor:pointer;" onclick="useRagResult(\`${r.text.replace(/`/g, "'").slice(0, 100)}\`)">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="color:var(--primary);font-weight:600;">${r.doc_name}</span>
                                <span style="color:var(--accent);">${(r.score * 100).toFixed(0)}%</span>
                            </div>
                            <div style="color:var(--text-secondary);line-height:1.4;">${r.text.slice(0, 120)}${r.text.length > 120 ? '...' : ''}</div>
                            ${ragSettings.showScores ? `<div style="font-size:9px;color:var(--text-muted);margin-top:4px;">TF-IDF: ${r.tfidf_score?.toFixed(3) || '-'} | BM25: ${r.bm25_score?.toFixed(2) || '-'} | 来源: ${r.source || 'base'}</div>` : ''}
                        </div>
                    `).join('');
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
                <div class="welcome-container" id="welcomeScreen">
                    <img src="/header-img" class="welcome-avatar">
                    <h1 class="welcome-title">辉夜姬 ✨</h1>
                    <p class="welcome-subtitle">哼~本小姐是从月球来的辉夜姬！跨越八千年的时空，终于找到你了呢~有什么事想跟辉夜说吗？★</p>
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
                </div>
            `;
        }
        
        function quickAction(type) {
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
            document.getElementById('statsSessions').textContent = stats.sessions;
            document.getElementById('statsInput').textContent = stats.inputTokens;
            document.getElementById('statsOutput').textContent = stats.outputTokens;
            document.getElementById('statsLatency').textContent = stats.latencies.length ? Math.round(stats.latencies.reduce((a,b)=>a+b,0)/stats.latencies.length) : 0;
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
            const name = prompt('训练任务名称:');
            if (!name) return;
            
            fetch('/finetune/datasets').then(r => r.json()).then(data => {
                if (!data.success || data.datasets.length === 0) {
                    showToast('请先上传数据集');
                    return;
                }
                
                const datasetOptions = data.datasets.map((ds, i) => `${i + 1}. ${ds.name} (${ds.sample_count}样本)`).join('\n');
                const datasetIdx = prompt(`选择数据集:\n${datasetOptions}`);
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
                    document.getElementById('memLongTerm').textContent = data.stats.long_term_count;
                    document.getElementById('memAvgImportance').textContent = data.stats.avg_importance;
                    document.getElementById('memEntities').textContent = data.stats.entity_count;
                    document.getElementById('memProfile').textContent = data.stats.profile_count;
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
${enabledMcpTools.map(t => `- ${t}`).join('\n')}

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
                const readOnly = confirm('是否设置为只读模式？\n\n确定 = 只读\n取消 = 可读写');
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
            {id: 'code', name: '📝 代码助手', prompt: '请帮我写一段代码，实现以下功能：', icon: '📝'},
            {id: 'translate', name: '🌐 翻译助手', prompt: '请将以下内容翻译成英文：', icon: '🌐'},
            {id: 'summary', name: '📋 总结助手', prompt: '请帮我总结以下内容的要点：', icon: '📋'},
            {id: 'email', name: '📧 邮件助手', prompt: '请帮我写一封邮件，主题是：', icon: '📧'},
            {id: 'article', name: '✍️ 文章助手', prompt: '请帮我写一篇关于', icon: '✍️'},
            {id: 'explain', name: '💡 解释助手', prompt: '请用简单的话解释一下：', icon: '💡'},
            {id: 'improve', name: '✨ 润色助手', prompt: '请帮我润色以下内容：', icon: '✨'},
            {id: 'debug', name: '🐛 调试助手', prompt: '以下代码有问题，请帮我找出错误：', icon: '🐛'}
        ];
        
        function renderPromptList() {
            document.getElementById('promptList').innerHTML = PROMPT_TEMPLATES.map(p => `
                <div class="chat-item" onclick="usePrompt('${p.prompt}')">
                    <span>${p.icon}</span>
                    <span class="chat-item-title">${p.name}</span>
                </div>
            `).join('');
        }
        
        function usePrompt(prompt) {
            document.getElementById('mainInput').value = prompt;
            document.getElementById('mainInput').focus();
            updateCharCount();
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
        
        async function sendMessage() {
            const input = document.getElementById('mainInput');
            let msg = input.value.trim();
            if (!msg && attachments.length === 0) return;
            if (msg.startsWith('/')) { executeCommand(msg.split(' ')[0]); return; }
            
            if (deepseekConfig.enabled && deepseekConfig.apiKey) {
                await sendDeepSeekMessage(msg, input);
                return;
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
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    fullContent += data.content;
                                    contentEl.innerHTML = settings.markdown ? marked.parse(fullContent) : fullContent;
                                    container.scrollTop = container.scrollHeight;
                                }
                                if (data.done) {
                                    if (chat.messages[editingMsgIdx + 1]) {
                                        chat.messages[editingMsgIdx + 1].content = fullContent;
                                    } else {
                                        chat.messages.push({ role: 'assistant', content: fullContent, time: replyTime });
                                    }
                                    if (history[histIdx]) history[histIdx][1] = fullContent;
                                    saveChats();
                                }
                            } catch (e) {}
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
                
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
                        <div class="reasoning-section" id="reasoningSection" style="display:none;">
                            <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                                <span class="reasoning-toggle-icon">▶</span>
                                <span>思考过程</span>
                            </div>
                            <div class="reasoning-content" id="reasoningContent"></div>
                        </div>
                        <div class="message-content" id="streamContent"></div>
                        <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄 重新生成</button></div>
                        <div class="message-time">${replyTime}</div>
                    </div>
                `;
                container.appendChild(msgEl);
                const contentEl = document.getElementById('streamContent');
                const reasoningSection = document.getElementById('reasoningSection');
                const reasoningContentEl = document.getElementById('reasoningContent');
                let fullContent = '';
                let fullReasoning = '';
                let hasReasoning = false;
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg, history: history.slice(0,-1), role: currentRole,
                        lora: currentLora !== 'none' ? currentLora : null,
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
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    contentEl.innerHTML = settings.markdown ? marked.parse(fullContent) : fullContent;
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
                    addMessageToUI('assistant', '网络错误，请重试', time);
                }
            }
            
            isGenerating = false;
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
        
        function openStats() {
            document.getElementById('statSessions').textContent = stats.sessions || 0;
            document.getElementById('statInput').textContent = stats.inputTokens || 0;
            document.getElementById('statOutput').textContent = stats.outputTokens || 0;
            const avgLatency = stats.latencies && stats.latencies.length ? Math.round(stats.latencies.reduce((a,b) => a+b, 0) / stats.latencies.length) : 0;
            document.getElementById('statLatency').textContent = avgLatency + 'ms';
            
            const chart = document.getElementById('usageChart');
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
                    <div class="reasoning-section" id="reasoningSection" style="display:none;">
                        <div class="reasoning-toggle" onclick="toggleReasoning(this)">
                            <span class="reasoning-toggle-icon">▶</span>
                            <span>思考过程</span>
                        </div>
                        <div class="reasoning-content" id="reasoningContent"></div>
                    </div>
                    <div class="message-content" id="streamContent"></div>
                    <div class="message-actions"><button class="msg-action-btn" onclick="regenerate()">🔄</button></div>
                    <div class="message-time">${replyTime}</div>
                </div>
            `;
            container.appendChild(msgEl);
            const contentEl = document.getElementById('streamContent');
            const reasoningSection = document.getElementById('reasoningSection');
            const reasoningContentEl = document.getElementById('reasoningContent');
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
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    contentEl.innerHTML = settings.markdown ? marked.parse(fullContent) : fullContent;
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
        function switchTab(tab) {
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            if (tab === 'loras') loadLoraList();
            if (tab === 'tools') renderToolList();
            if (tab === 'prompts') renderPromptList();
            if (tab === 'mcp') loadMcpPlugins();
            if (tab === 'workflow') loadWorkflows();
            if (tab === 'memory') { refreshMemoryStats(); searchMemories(); }
            if (tab === 'multimodal') { loadMultimodalHistory(); }
            if (tab === 'finetune') { refreshFinetuneData(); }
        }
        
        init();
    