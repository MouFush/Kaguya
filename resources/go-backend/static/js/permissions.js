        function switchTab(tab, clickedElement) {
            console.log('switchTab called:', tab, clickedElement);
            document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            if (clickedElement) clickedElement.classList.add('active');
            const targetTab = document.getElementById(tab + 'Tab');
            if (!targetTab) return;
            targetTab.classList.add('active');
            if (tab === 'roles') renderRoleList();
            if (tab === 'tools') renderToolList();
            if (tab === 'prompts') renderPromptList();
            if (tab === 'console') loadProjectCenter();
            if (tab === 'ecosystem') loadProjectCenter();
            if (tab === 'scenes') initScenesCenter();
            if (tab === 'project') loadProjectCenter();
            if (tab === 'mcp') loadMcpPlugins();
            if (tab === 'workflow') loadWorkflows();
            if (tab === 'memory') { refreshMemoryStats(); searchMemories(); }
            if (tab === 'knowledge') { loadRagDocuments(); }
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
            if (sub === 'vision') loadMultimodalHistory();
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

