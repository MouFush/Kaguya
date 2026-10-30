// File analyzer panel extracted from the main shell.
        function fileAnalyzerGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function fileAnalyzerPost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
        }

        function analyzeProjectStructure() {
            var path = prompt('输入项目路径:', 'D:\\claude-code-main\\claude-code-main');
            if (!path) return;
            fileAnalyzerPost('/agent/file-analyzer/analyze', {path:path}).then(function(data) {
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
            fileAnalyzerGet('/agent/file-analyzer/tree?path=' + encodeURIComponent(projectPath) + '&depth=3').then(function(data) {
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
            fileAnalyzerGet('/agent/file-analyzer/dependencies?path=' + encodeURIComponent(projectPath) + '&file=' + encodeURIComponent(path) + '&depth=2').then(function(data) {
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
            fileAnalyzerGet('/agent/file-analyzer/recommendations?path=' + encodeURIComponent(projectPath)).then(function(data) {
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
