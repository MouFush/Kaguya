// Security, auth, account, and project settings panels extracted from the main shell.
        function adminGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function adminPost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
        }

        function adminDelete(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            if (!payload) return window.KaguyaAPI.del(path);
            return window.KaguyaAPI.request(path, {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
        }

        function refreshSecurityStatus() {
            adminGet('/security/status').then(data => {
                if (!data.success) return;
                const s = data.status;
                const cards = document.getElementById('securityStatusCards');
                if (cards) {
                    const items = [
                        {label: '访问认证', value: s.auth_enabled ? '已启用' : '未启用', icon: '🔐', color: s.auth_enabled ? '#10b981' : '#ef4444'},
                        {label: '速率限制', value: s.rate_limit_active ? '已启用' : '未启用', icon: '⏱️', color: s.rate_limit_active ? '#10b981' : '#ef4444'},
                        {label: 'IP控制', value: s.ip_whitelist_mode === 'whitelist' ? '白名单' : '开放', icon: '🌐', color: s.ip_whitelist_mode === 'whitelist' ? '#10b981' : '#f59e0b'},
                        {label: '代码沙箱', value: s.code_sandbox ? '已启用' : '未启用', icon: '💻', color: s.code_sandbox ? '#10b981' : '#ef4444'},
                        {label: '审计日志', value: (s.audit_events_count || 0) + '条', icon: '📋', color: '#667eea'},
                        {label: '安全警告', value: (s.recent_warnings || 0) + '条', icon: '⚠️', color: s.recent_warnings > 0 ? '#f59e0b' : '#10b981'}
                    ];
                    cards.innerHTML = items.map(i => `<div class="ops-kpi-card" style="background:linear-gradient(135deg,${i.color}18,${i.color}08);border-color:${i.color}33;"><div style="font-size:20px;">${i.icon}</div><div style="font-size:11px;font-weight:600;color:${i.color};">${i.value}</div><div style="font-size:10px;color:var(--text-muted);">${i.label}</div></div>`).join('');
                }
                const grid = document.getElementById('securityShieldGrid');
                if (grid) {
                    const shields = [
                        {name: '访问认证', icon: '🔐', on: s.auth_enabled, desc: s.auth_enabled ? '密码保护，公网访问安全' : '未启用，任何人都可访问'},
                        {name: 'XSS防护', icon: '🔒', on: s.xss_protection, desc: '检测并阻止跨站脚本攻击'},
                        {name: 'SSRF防护', icon: '🌐', on: s.ssrf_protection, desc: '阻止对内网地址的请求'},
                        {name: '代码沙箱', icon: '💻', on: s.code_sandbox, desc: '限制代码执行权限和危险操作'},
                        {name: 'API Key脱敏', icon: '🔑', on: s.api_key_masking, desc: 'GET接口返回脱敏后的Key'},
                        {name: '速率限制', icon: '⏱️', on: s.rate_limit_active, desc: '防止暴力请求和DDoS攻击'},
                        {name: '输入验证', icon: '✅', on: s.input_validation, desc: '检测SQL注入和XSS攻击向量'},
                        {name: 'CSRF防护', icon: '🛡️', on: s.csrf_protection, desc: '防止跨站请求伪造攻击'},
                        {name: '审计日志', icon: '📋', on: s.audit_logging, desc: '记录所有安全相关事件'},
                        {name: '安全Session', icon: '🔐', on: s.session_secure, desc: 'HttpOnly + SameSite Cookie'},
                        {name: 'IP白名单', icon: '🌐', on: s.ip_whitelist_mode === 'whitelist', desc: s.ip_whitelist_mode === 'whitelist' ? `白名单模式，${s.ip_whitelist_count}个IP` : '开放模式，所有IP可访问'},
                        {name: '数据加密', icon: '🗝️', on: s.encryption_version >= 2, desc: s.encryption_version >= 2 ? 'AES级别CTR流加密+HMAC认证' : '基础HMAC完整性校验'}
                    ];
                    grid.innerHTML = shields.map(sh => `<div style="background:${sh.on ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)'};border:1px solid ${sh.on ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'};border-radius:8px;padding:8px 10px;display:flex;align-items:center;gap:8px;">
                        <span style="font-size:16px;">${sh.icon}</span>
                        <div style="flex:1;"><div style="font-size:11px;font-weight:600;color:var(--text-primary);">${sh.name} <span style="font-size:9px;color:${sh.on ? '#10b981' : '#ef4444'};">${sh.on ? '✅' : '❌'}</span></div><div style="font-size:9px;color:var(--text-muted);">${sh.desc}</div></div>
                    </div>`).join('');
                }
                loadSecurityAudit();
                loadAuthStatus();
                loadIpWhitelist();
            });
        }

        function loadSecurityAudit() {
            const filter = document.getElementById('securityAuditFilter')?.value || '';
            adminGet('/security/audit' + (filter ? '?severity=' + encodeURIComponent(filter) : '')).then(data => {
                if (!data.success) return;
                const list = document.getElementById('securityAuditList');
                if (!list) return;
                if (!data.events.length) {
                    list.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:20px;">暂无安全审计日志</div>';
                    return;
                }
                const severityColors = {critical: '#ef4444', warning: '#f59e0b', info: '#667eea'};
                const severityLabels = {critical: '严重', warning: '警告', info: '信息'};
                list.innerHTML = data.events.slice().reverse().map(e => `<div style="padding:8px 10px;border-left:3px solid ${severityColors[e.severity] || '#667eea'};background:var(--bg-secondary);border-radius:0 8px 8px 0;margin-bottom:6px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:11px;font-weight:600;color:${severityColors[e.severity] || '#667eea'};">${severityLabels[e.severity] || e.severity} · ${e.type}</span>
                        <span style="font-size:10px;color:var(--text-muted);">${e.timestamp || ''}</span>
                    </div>
                    <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">${escapeHtml(e.detail || '')}</div>
                    <div style="font-size:9px;color:var(--text-muted);margin-top:2px;">IP: ${e.ip || 'unknown'}</div>
                </div>`).join('');
            });
        }

        function clearSecurityAudit() {
            adminPost('/security/audit/clear').then(data => {
                if (data.success) { loadSecurityAudit(); showToast('审计日志已清空'); }
            });
        }

        function runSecurityScan() {
            adminGet('/dependencies/security-check').then(data => {
                const list = document.getElementById('securityVulnList');
                if (!list) return;
                if (!data.vulnerabilities || !data.vulnerabilities.length) {
                    list.innerHTML = '<div style="text-align:center;color:#10b981;padding:20px;font-size:13px;">✅ 未发现安全漏洞</div>';
                    return;
                }
                const sevColors = {high: '#ef4444', medium: '#f59e0b', low: '#667eea'};
                list.innerHTML = data.vulnerabilities.map(v => `<div style="padding:8px 10px;border-left:3px solid ${sevColors[v.severity] || '#667eea'};background:var(--bg-secondary);border-radius:0 8px 8px 0;">
                    <div style="font-size:11px;font-weight:600;color:${sevColors[v.severity] || '#667eea'};">${v.severity?.toUpperCase() || 'UNKNOWN'} · ${v.type || ''}</div>
                    <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">${escapeHtml(v.message || '')}</div>
                </div>`).join('');
            });
        }

        function loadAuthStatus() {
            adminGet('/auth/setup').then(data => {
                const panel = document.getElementById('authManagementPanel');
                if (!panel) return;
                const enabled = data.enabled;
                const hasPwd = data.has_password;
                panel.innerHTML = `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;padding:10px;background:${enabled ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'};border:1px solid ${enabled ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};border-radius:10px;">
                        <span style="font-size:24px;">${enabled ? '🛡️' : '⚠️'}</span>
                        <div style="flex:1;">
                            <div style="font-size:13px;font-weight:600;color:${enabled ? '#10b981' : '#ef4444'};">${enabled ? '访问认证已启用' : '访问认证未启用'}</div>
                            <div style="font-size:11px;color:var(--text-muted);">${enabled ? '所有访问需要密码验证，公网访问安全' : '任何人都可访问，公网环境有泄露风险'}</div>
                        </div>
                        <button class="project-mini-btn" style="background:${enabled ? '#ef4444' : '#10b981'};color:#fff;border:none;" onclick="${enabled ? 'disableAuth()' : 'showEnableAuthDialog()'}">${enabled ? '禁用' : '启用'}</button>
                    </div>
                    ${enabled ? `
                    <div style="margin-bottom:10px;">
                        <button class="project-mini-btn" onclick="showChangePasswordDialog()" style="width:100%;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;padding:8px;">🔑 修改访问密码</button>
                    </div>
                    <div style="margin-bottom:10px;">
                        <button class="project-mini-btn" onclick="logoutAllDevices()" style="width:100%;background:#f59e0b;color:#fff;border:none;padding:8px;">🚪 踢出所有其他设备</button>
                    </div>
                    ` : ''}
                    <div style="font-size:10px;color:var(--text-muted);padding:6px 0;border-top:1px solid var(--border-color);">
                        💡 启用认证后，从公网访问需要输入密码。API调用需在Header中携带 <code style="background:var(--bg-secondary);padding:1px 4px;border-radius:3px;">Authorization: Bearer &lt;token&gt;</code>
                    </div>
                `;
            });
        }

        function showEnableAuthDialog() {
            const pwd = prompt('设置访问密码（至少4位）：');
            if (!pwd || pwd.length < 4) { if (pwd) showToast('密码至少4位'); return; }
            adminPost('/auth/setup', {action: 'enable', password: pwd}).then(data => {
                if (data.success) { showToast('认证已启用，请牢记密码'); loadAuthStatus(); refreshSecurityStatus(); }
                else showToast(data.error || '操作失败');
            });
        }

        function disableAuth() {
            if (!confirm('确定要禁用访问认证吗？公网环境下可能导致数据泄露！')) return;
            adminPost('/auth/setup', {action: 'disable'}).then(data => {
                if (data.success) { showToast('认证已禁用'); loadAuthStatus(); refreshSecurityStatus(); }
                else showToast(data.error || '操作失败');
            });
        }

        function showChangePasswordDialog() {
            const oldPwd = prompt('输入当前密码：');
            if (!oldPwd) return;
            const newPwd = prompt('输入新密码（至少4位）：');
            if (!newPwd || newPwd.length < 4) { if (newPwd) showToast('密码至少4位'); return; }
            adminPost('/auth/setup', {action: 'change_password', old_password: oldPwd, new_password: newPwd}).then(data => {
                if (data.success) { showToast('密码已修改，需重新登录'); loadAuthStatus(); }
                else showToast(data.error || '修改失败');
            });
        }

        function logoutAllDevices() {
            if (!confirm('将踢出所有其他设备（当前设备不受影响），确定？')) return;
            adminPost('/auth/logout-all').then(data => {
                if (data.success) showToast('已踢出所有其他设备');
                else showToast(data.error || '操作失败');
            });
        }

        function loadIpWhitelist() {
            adminGet('/security/ip-whitelist').then(data => {
                const panel = document.getElementById('ipWhitelistPanel');
                if (!panel) return;
                const wl = data.whitelist || [];
                const mode = data.mode || 'open';
                panel.innerHTML = `
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;padding:8px;background:${mode === 'whitelist' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'};border:1px solid ${mode === 'whitelist' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'};border-radius:10px;">
                        <span style="font-size:20px;">${mode === 'whitelist' ? '✅' : '🌐'}</span>
                        <div style="flex:1;">
                            <div style="font-size:12px;font-weight:600;color:${mode === 'whitelist' ? '#10b981' : '#f59e0b'};">${mode === 'whitelist' ? '白名单模式' : '开放模式'}</div>
                            <div style="font-size:10px;color:var(--text-muted);">${mode === 'whitelist' ? '仅白名单IP可访问' : '所有IP均可访问'}</div>
                        </div>
                        <button class="project-mini-btn" style="background:${mode === 'whitelist' ? '#ef4444' : '#10b981'};color:#fff;border:none;" onclick="toggleIpMode()">${mode === 'whitelist' ? '切换开放' : '切换白名单'}</button>
                    </div>
                    <div style="display:flex;gap:6px;margin-bottom:8px;">
                        <input class="project-input" id="newIpInput" placeholder="输入IP地址 (如 192.168.1.100)" style="flex:1;">
                        <button class="project-mini-btn" onclick="addIpToWhitelist()" style="background:#667eea;color:#fff;border:none;">➕ 添加</button>
                    </div>
                    <div style="font-size:10px;color:var(--text-muted);margin-bottom:6px;">当前IP: <code style="background:var(--bg-secondary);padding:1px 4px;border-radius:3px;">${data.current_ip || 'unknown'}</code></div>
                    <div style="max-height:150px;overflow-y:auto;display:flex;flex-direction:column;gap:4px;">
                        ${wl.length ? wl.map(ip => `<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;background:var(--bg-secondary);border-radius:6px;">
                            <span style="font-size:11px;font-family:monospace;color:var(--text-primary);">${escapeHtml(ip)}</span>
                            <button style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:12px;" onclick="removeIpFromWhitelist('${escapeHtml(ip)}')">✕</button>
                        </div>`).join('') : '<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:10px;">白名单为空</div>'}
                    </div>
                `;
            });
        }

        function toggleIpMode() {
            adminPost('/security/ip-whitelist/mode').then(data => {
                if (data.success) { loadIpWhitelist(); showToast(data.mode === 'whitelist' ? '已切换为白名单模式' : '已切换为开放模式'); }
                else showToast(data.error || '操作失败');
            });
        }

        function addIpToWhitelist() {
            const ip = document.getElementById('newIpInput')?.value?.trim();
            if (!ip) { showToast('请输入IP地址'); return; }
            adminPost('/security/ip-whitelist', {ip: ip}).then(data => {
                if (data.success) { loadIpWhitelist(); showToast('IP已添加'); }
                else showToast(data.error || '添加失败');
            });
        }

        function removeIpFromWhitelist(ip) {
            adminDelete('/security/ip-whitelist', {ip: ip}).then(data => {
                if (data.success) { loadIpWhitelist(); showToast('IP已移除'); }
                else showToast(data.error || '移除失败');
            });
        }

        function loadProjectConfig() {
            adminGet('/project/config').then(data => {
                if (!data.success) return;
                const c = data.config;
                document.getElementById('projectConfigName').value = c.name || '';
                document.getElementById('projectConfigDesc').value = c.description || '';
                document.getElementById('projectConfigTags').value = (c.tags || []).join(', ');
                document.getElementById('projectConfigVersion').value = c.version || '';
                document.getElementById('projectConfigOwner').value = c.owner || '';
                refreshProjectStats();
            });
        }

        function saveProjectConfig() {
            const config = {
                name: document.getElementById('projectConfigName')?.value || '',
                description: document.getElementById('projectConfigDesc')?.value || '',
                tags: (document.getElementById('projectConfigTags')?.value || '').split(',').map(t => t.trim()).filter(Boolean),
                version: document.getElementById('projectConfigVersion')?.value || '',
                owner: document.getElementById('projectConfigOwner')?.value || ''
            };
            adminPost('/project/config', config).then(data => {
                if (data.success) showToast('项目配置已保存');
                else showToast(data.error || '保存失败');
            });
        }

        function refreshProjectStats() {
            adminGet('/project/stats').then(data => {
                if (!data.success) return;
                const s = data.stats;
                const panel = document.getElementById('projectStatsPanel');
                if (!panel) return;
                const bars = [
                    {label: '任务完成率', value: s.task_done_rate || 0, max: 100, color: '#10b981', suffix: '%'},
                    {label: '里程碑进度', value: s.milestone_progress || 0, max: 100, color: '#667eea', suffix: '%'},
                    {label: '风险缓解率', value: s.risk_mitigated_rate || 0, max: 100, color: '#f59e0b', suffix: '%'},
                    {label: '运营活动完成率', value: s.campaign_done_rate || 0, max: 100, color: '#ec4899', suffix: '%'},
                    {label: '发布成功率', value: s.release_success_rate || 0, max: 100, color: '#8b5cf6', suffix: '%'}
                ];
                panel.innerHTML = bars.map(b => `<div>
                    <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:3px;">
                        <span style="color:var(--text-secondary);">${b.label}</span>
                        <span style="color:${b.color};font-weight:600;">${b.value}${b.suffix}</span>
                    </div>
                    <div style="height:6px;background:var(--bg-secondary);border-radius:3px;overflow:hidden;">
                        <div style="height:100%;width:${Math.min(b.value, 100)}%;background:${b.color};border-radius:3px;transition:width 0.5s;"></div>
                    </div>
                </div>`).join('') + `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px;">
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_artifacts || 0}</div><div style="font-size:9px;color:var(--text-muted);">产物</div></div>
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_tasks || 0}</div><div style="font-size:9px;color:var(--text-muted);">任务</div></div>
                    <div style="text-align:center;padding:6px;background:var(--bg-secondary);border-radius:6px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);">${s.total_activities || 0}</div><div style="font-size:9px;color:var(--text-muted);">活动</div></div>
                </div>`;
            });
        }

        function exportProjectData() {
            adminGet('/project/export').then(data => {
                if (!data.success) { showToast(data.error || '导出失败'); return; }
                const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `kaguya_project_${new Date().toISOString().slice(0,10)}.json`;
                a.click(); URL.revokeObjectURL(url);
                showToast('项目数据已导出');
            });
        }

        function importProjectData(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const data = JSON.parse(e.target.result);
                    adminPost('/project/import', data).then(res => {
                        if (res.success) { showToast(`导入成功: ${res.imported || 0}条数据`); loadProjectCenter(); }
                        else showToast(res.error || '导入失败');
                    });
                } catch(err) { showToast('文件格式无效'); }
            };
            reader.readAsText(file);
            event.target.value = '';
        }

        function exportChatHistory() {
            adminGet('/chats/export').then(data => {
                if (!data.success) { showToast(data.error || '导出失败'); return; }
                const blob = new Blob([JSON.stringify(data.chats || [], null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `kaguya_chats_${new Date().toISOString().slice(0,10)}.json`;
                a.click(); URL.revokeObjectURL(url);
                showToast('对话记录已导出');
            });
        }

        function clearAllProjectData() {
            if (!confirm('确定要清空所有项目数据吗？此操作不可恢复！')) return;
            adminPost('/project/clear').then(data => {
                if (data.success) { showToast('项目数据已清空'); loadProjectCenter(); }
                else showToast(data.error || '清空失败');
            });
        }

        function loadUserProfile() {
            adminGet('/account/profile').then(data => {
                if (!data.success) return;
                const p = data.profile;
                document.getElementById('userNickname').value = p.nickname || '';
                document.getElementById('userEmail').value = p.email || '';
                document.getElementById('userAvatarSelect').value = p.avatar || '🌙';
                document.getElementById('userAvatarDisplay').textContent = p.avatar || '🌙';
                document.getElementById('userDisplayName').textContent = p.nickname || '辉夜用户';
                loadApiTokens();
                loadActiveSessions();
                loadUserActivityLog();
            });
        }

        function saveUserProfile() {
            const profile = {
                nickname: document.getElementById('userNickname')?.value || '',
                email: document.getElementById('userEmail')?.value || '',
                avatar: document.getElementById('userAvatarSelect')?.value || '🌙'
            };
            adminPost('/account/profile', profile).then(data => {
                if (data.success) {
                    showToast('个人信息已保存');
                    document.getElementById('userAvatarDisplay').textContent = profile.avatar;
                    document.getElementById('userDisplayName').textContent = profile.nickname || '辉夜用户';
                } else showToast(data.error || '保存失败');
            });
        }

        function updateAvatarPreview() {
            const avatar = document.getElementById('userAvatarSelect')?.value || '🌙';
            document.getElementById('userAvatarDisplay').textContent = avatar;
        }

        function loadApiTokens() {
            adminGet('/account/tokens').then(data => {
                const list = document.getElementById('apiTokenList');
                if (!list) return;
                const tokens = data.tokens || [];
                if (!tokens.length) {
                    list.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:10px;">暂无API Token</div>';
                    return;
                }
                list.innerHTML = tokens.map(t => `<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--bg-secondary);border-radius:8px;">
                    <div style="flex:1;">
                        <div style="font-size:11px;font-weight:600;color:var(--text-primary);">${escapeHtml(t.name || 'Token')}</div>
                        <div style="font-size:10px;color:var(--text-muted);font-family:monospace;">${t.token_mask || '****'}</div>
                        <div style="font-size:9px;color:var(--text-muted);">创建于 ${t.created_at || ''}</div>
                    </div>
                    <button style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:12px;" onclick="revokeApiToken('${t.id}')">🗑️</button>
                </div>`).join('');
            });
        }

        function generateApiToken() {
            const name = prompt('Token名称（如：我的脚本）：');
            if (!name) return;
            adminPost('/account/tokens', {name: name}).then(data => {
                if (data.success) {
                    const token = data.token || '';
                    prompt('请复制Token（仅显示一次）：', token);
                    loadApiTokens();
                } else showToast(data.error || '生成失败');
            });
        }

        function revokeApiToken(id) {
            if (!confirm('确定要撤销此Token吗？')) return;
            adminDelete('/account/tokens', {id: id}).then(data => {
                if (data.success) { loadApiTokens(); showToast('Token已撤销'); }
                else showToast(data.error || '撤销失败');
            });
        }

        function loadActiveSessions() {
            adminGet('/account/sessions').then(data => {
                const list = document.getElementById('activeSessionList');
                if (!list) return;
                const sessions = data.sessions || [];
                if (!sessions.length) {
                    list.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:10px;">暂无活跃会话</div>';
                    return;
                }
                list.innerHTML = sessions.map(s => `<div style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--bg-secondary);border-radius:8px;">
                    <span style="font-size:16px;">${s.current ? '🟢' : '🔵'}</span>
                    <div style="flex:1;">
                        <div style="font-size:11px;font-weight:600;color:var(--text-primary);">${s.current ? '当前设备' : '其他设备'}</div>
                        <div style="font-size:10px;color:var(--text-muted);">IP: ${s.ip || 'unknown'} · ${s.last_active || ''}</div>
                    </div>
                    ${!s.current ? `<button style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:11px;" onclick="revokeSession('${s.id}')">踢出</button>` : ''}
                </div>`).join('');
            });
        }

        function revokeSession(id) {
            adminDelete('/account/sessions', {id: id}).then(data => {
                if (data.success) { loadActiveSessions(); showToast('会话已踢出'); }
                else showToast(data.error || '操作失败');
            });
        }

        function loadUserActivityLog() {
            adminGet('/project/activity?limit=20').then(data => {
                const list = document.getElementById('userActivityLog');
                if (!list) return;
                const activities = data.activities || [];
                if (!activities.length) {
                    list.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:11px;padding:10px;">暂无操作日志</div>';
                    return;
                }
                list.innerHTML = activities.slice().reverse().map(a => `<div style="padding:4px 8px;border-left:2px solid #667eea;background:var(--bg-secondary);border-radius:0 4px 4px 0;font-size:10px;">
                    <span style="color:var(--text-secondary);">${escapeHtml(a.action || a.type || '')}</span>
                    <span style="color:var(--text-muted);margin-left:6px;">${a.timestamp || ''}</span>
                </div>`).join('');
            });
        }
