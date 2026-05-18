// Agent permission dashboard extracted from the main shell.
        function permissionGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function permissionPost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
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
            permissionGet('/agent/v2/permissions/mode').then(function(data) {
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
            permissionGet('/agent/v2/permissions/stats').then(function(data) {
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
            permissionPost('/agent/v2/permissions/mode', {mode:modeId}).then(function(data) {
                if (data.status === 'ok') loadPermMode();
            }).catch(function(){});
        }

        function loadPermPending() {
            permissionGet('/agent/v2/permissions/pending').then(function(data) {
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
            permissionPost('/agent/v2/permissions/respond', {request_id:requestId,decision:decision}).then(function(data) {
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
            permissionGet('/agent/v2/permissions/denials?limit=20').then(function(data) {
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
            permissionGet('/agent/v2/permissions/audit?limit=30').then(function(data) {
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
            permissionGet('/agent/v2/permissions/rules').then(function(data) {
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
            permissionPost('/agent/v2/permissions/rules', {tool_name:toolName,pattern:pattern,decision:decision,source:'user',description:'User added rule'}).then(function(data) {
                if (data.status === 'ok') loadPermRules();
            }).catch(function(){});
        }

        function checkCmdSafety() {
            var cmd = document.getElementById('cmdSafetyInput').value;
            if (!cmd) return;
            permissionPost('/agent/v2/command-safety', {command:cmd}).then(function(data) {
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
