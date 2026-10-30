        function loadUserProfile() {
            fetch('/account/profile').then(r => r.json()).then(data => {
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
            fetch('/account/profile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(profile)
            }).then(r => r.json()).then(data => {
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
            fetch('/account/tokens').then(r => r.json()).then(data => {
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
            fetch('/account/tokens', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    const token = data.token || '';
                    prompt('请复制Token（仅显示一次）：', token);
                    loadApiTokens();
                } else showToast(data.error || '生成失败');
            });
        }

        function revokeApiToken(id) {
            if (!confirm('确定要撤销此Token吗？')) return;
            fetch('/account/tokens', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id})
            }).then(r => r.json()).then(data => {
                if (data.success) { loadApiTokens(); showToast('Token已撤销'); }
                else showToast(data.error || '撤销失败');
            });
        }

        function loadActiveSessions() {
            fetch('/account/sessions').then(r => r.json()).then(data => {
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
            fetch('/account/sessions', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id})
            }).then(r => r.json()).then(data => {
                if (data.success) { loadActiveSessions(); showToast('会话已踢出'); }
                else showToast(data.error || '操作失败');
            });
        }

        function loadUserActivityLog() {
            fetch('/project/activity?limit=20').then(r => r.json()).then(data => {
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
        
        function stopGeneration() {
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
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
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
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                // 忽略 thinking 类型的数据，不显示思考过程
                                if (data.done) {
                                    // 生成完成后渲染 markdown
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
                            } catch (e) {
                                console.error('Parse error:', e, 'Line:', line);
                            }
                        }
                    }
                }
                currentReader = null;
                contentEl.id = '';
                contentEl.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
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
                
                const res = await fetch('/stream', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
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
                    })
                });
                
                currentReader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                // 处理思考过程内容 (Qwen3.5 模型的 thinking 字段)
                                if (data.thinking) {
                                    fullReasoning += data.thinking;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                // 兼容旧格式的 reasoning 字段
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
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

        const API_PROVIDERS={
            deepseek:{name:'DeepSeek',color:'#4f46e5',icon:'&#x1F916;',url:'https://api.deepseek.com',models:[
                {id:'deepseek-chat',label:'DeepSeek V3.2 (通用对话)'},
                {id:'deepseek-reasoner',label:'DeepSeek R1 (深度推理)'},
                {id:'deepseek-coder',label:'DeepSeek Coder (代码专用)'},
                {id:'deepseek-v3.2-lite',label:'DeepSeek V3.2 Lite (轻量)'}
            ],docUrl:'https://platform.deepseek.com'},
            glm:{name:'GLM (智谱)',color:'#10b981',icon:'&#x1F4A1;',url:'https://open.bigmodel.cn/api/paas/v4',models:[
                {id:'glm-5',label:'GLM-5 (最新旗舰)'},
                {id:'glm-5-plus',label:'GLM-5 Plus (增强版)'},
                {id:'glm-4-flash',label:'GLM-4 Flash (快速)'},
                {id:'glm-4-long',label:'GLM-4 Long (长文本)'}
            ],docUrl:'https://open.bigmodel.cn'},
            claude:{name:'Claude (Anthropic)',color:'#d97706',icon:'&#x1F9D0;',url:'https://api.anthropic.com/v1/messages',models:[
                {id:'claude-opus-4-6',label:'Claude Opus 4.6 (最强)'},
                {id:'claude-opus-4-5',label:'Claude Opus 4.5'},
                {id:'claude-sonnet-4',label:'Claude Sonnet 4 (均衡)'},
                {id:'claude-haiku-3-5',label:'Claude Haiku 3.5 (快速)'}
            ],docUrl:'https://console.anthropic.com'},
            openai:{name:'OpenAI',color:'#10a37f',icon:'&#x1F9E0;',url:'https://api.openai.com/v1/chat/completions',models:[
                {id:'gpt-5.3-codex',label:'GPT-5.3 Codex (代码)'},
                {id:'gpt-5.4',label:'GPT-5.4 (最新旗舰)'},
                {id:'gpt-4o',label:'GPT-4o (多模态)'},
                {id:'o4-mini',label:'O4 Mini (快速)'}
            ],docUrl:'https://platform.openai.com'},
            kimi:{name:'Kimi (月之暗面)',color:'#7c3aed',icon:'&#x1F31C;',url:'https://api.moonshot.ai/v1',models:[
                {id:'kimi-k2.6',label:'Kimi K2.6 (最新)'},
                {id:'kimi-k2.5',label:'Kimi K2.5'},
                {id:'moonshot-v1-auto',label:'Moonshot V1 Auto'},
                {id:'moonshot-v1-128k',label:'Moonshot V1 128K'},
                {id:'moonshot-v1-32k',label:'Moonshot V1 32K'}
            ],docUrl:'https://platform.kimi.ai'},
            minimax:{name:'MiniMax',color:'#ec4899',icon:'&#x26A1;',url:'https://api.minimaxi.com/v1',models:[
                {id:'MiniMax-M2.7',label:'MiniMax M2.7 (最新)'},
                {id:'MiniMax-M2.7-highspeed',label:'MiniMax M2.7 Highspeed'},
                {id:'MiniMax-M2.5',label:'MiniMax M2.5'},
                {id:'abab6.5s-chat',label:'abab 6.5s Chat'},
                {id:'abab6.5t-chat',label:'abab 6.5t Chat'},
                {id:'abab5.5s-chat',label:'abab 5.5s Chat'}
            ],docUrl:'https://platform.minimaxi.com'},
            gemini:{name:'Gemini (Google)',color:'#4285f4',icon:'&#x1F52E;',url:'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',models:[
                {id:'gemini-3.1-pro',label:'Gemini 3.1 Pro (最新)'},
                {id:'gemini-3.1-ultra',label:'Gemini 3.1 Ultra (最强)'},
                {id:'gemini-2.5-flash',label:'Gemini 2.5 Flash (快速)'},
                {id:'gemini-2.5-pro',label:'Gemini 2.5 Pro (均衡)'}
            ],docUrl:'https://ai.google.dev'},
            qwen:{name:'Qwen (通义千问)',color:'#ff6a00',icon:'&#x1F525;',url:'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',models:[
                {id:'qwen-max',label:'Qwen-Max'},
                {id:'qwen-plus',label:'Qwen-Plus'},
                {id:'qwen-turbo',label:'Qwen-Turbo'},
                {id:'qwen-long',label:'Qwen-Long'},
                {id:'qwen-coder-plus',label:'Qwen-Coder-Plus'},
                {id:'qwen-vl-max',label:'Qwen-VL-Max'},
                {id:'qwen-math-plus',label:'Qwen-Math-Plus'}
            ],docUrl:'https://dashscope.console.aliyun.com'}
        };
        let _currentApiProvider=localStorage.getItem('active_api_provider')||'deepseek';

        function getApiProviders(){try{return JSON.parse(localStorage.getItem('api_providers')||'{}');}catch(e){return{};}}
        function chooseActiveApiProvider(cfg){
          var selected=localStorage.getItem('active_api_provider')||_currentApiProvider||'deepseek';
          if(API_PROVIDERS[selected]&&cfg[selected]&&cfg[selected].enabled&&(cfg[selected].apiKey||cfg[selected].hasSavedKey))return selected;
          for(const pv of Object.keys(API_PROVIDERS)){
            const c=cfg[pv];
            if(c&&c.enabled&&(c.apiKey||c.hasSavedKey))return pv;
          }
          return API_PROVIDERS[selected]?selected:'deepseek';
        }
        function saveApiProviders(cfg){
          localStorage.setItem('api_providers',JSON.stringify(cfg));
          var activeProvider=chooseActiveApiProvider(cfg);
          _currentApiProvider=activeProvider;
          localStorage.setItem('active_api_provider',activeProvider);
          var backendCfg={active_provider:activeProvider,providers:{},device_id:generateDeviceId()};
          Object.keys(cfg).forEach(function(k){
            var c=cfg[k];
            backendCfg.providers[k]={api_url:c.apiUrl||'',api_key:c.apiKey||'',model:c.model||''};
          });
          fetch('/external/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(backendCfg)}).catch(function(){});
          var activeCfg=cfg[activeProvider]||{};
          if(activeCfg.apiKey){
            var bindPayload={device_id:generateDeviceId(),provider:activeProvider,apiKey:activeCfg.apiKey,apiUrl:activeCfg.apiUrl||API_PROVIDERS[activeProvider].url,model:activeCfg.model||API_PROVIDERS[activeProvider].models[0].id};
            fetch('/api/device/bind',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(bindPayload)}).catch(function(){});
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
            content.innerHTML=`<div style="background:linear-gradient(135deg,${p.color}15,${p.color}05);border-radius:12px;padding:16px;margin-bottom:18px;"><div style="font-size:14px;font-weight:700;color:var(--text-primary);margin-bottom:6px;">${p.icon} ${p.name}</div><div style="font-size:11px;color:var(--text-secondary);line-height:1.6;">访问 <a href="${p.docUrl}" target="_blank" style="color:${p.color};">官方平台</a> 获取 API Key</div></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">API Key</label><input type="password" id="ap_apiKey" value="${cfg.apiKey||''}" placeholder="sk-/api-xxxxxxxx" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);outline:none;transition:var(--transition);" onfocus="this.style.borderColor='${p.color}'" onblur="this.style.borderColor=''"></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">API 地址</label><input type="text" id="ap_apiUrl" value="${cfg.apiUrl||p.url}" placeholder="${p.url}" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);outline:none;"></div><div style="margin-bottom:14px;"><label style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:6px;font-weight:600;">模型选择</label><select id="ap_model" style="width:100%;padding:11px;border:1px solid var(--border);border-radius:10px;font-size:13px;background:var(--bg-secondary);color:var(--text-primary);">${modelOpts}</select></div><div style="display:flex;align-items:center;justify-content:space-between;padding:12px;background:var(--bg-secondary);border-radius:10px;margin-bottom:16px;"><span style="font-size:12px;font-weight:600;color:var(--text-primary);">启用 ${p.name}</span><label class="toggle"><input type="checkbox" id="ap_enabled" ${cfg.enabled?'checked':''}><span class="toggle-slider"></span></label></div><div style="display:flex;gap:8px;"><button onclick="testApiConnection('${pv}')" style="flex:1;padding:10px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:10px;font-size:12px;cursor:pointer;color:var(--text-secondary);font-weight:600;transition:var(--transition);" onmouseover="this.style.borderColor='${p.color}'" onmouseout="this.style.borderColor=''">❓ 测试连接</button><button onclick="saveApiProvider('${pv}')" style="flex:1;padding:10px;background:linear-gradient(135deg,${p.color},${p.color}cc);border:none;border-radius:10px;font-size:12px;cursor:pointer;color:#fff;font-weight:700;box-shadow:0 2px 10px rgba(0,0,0,0.2);">✔ 保存</button></div>`;
        }

        function saveApiProvider(pv){
            const providers=getApiProviders();
            providers[pv]={
                apiKey:(document.getElementById('ap_apiKey').value||'').trim(),
                apiUrl:(document.getElementById('ap_apiUrl').value||API_PROVIDERS[pv].url||'').trim(),
                model:(document.getElementById('ap_model').value||'').trim(),
                enabled:document.getElementById('ap_enabled').checked
            };
            if(providers[pv].enabled&&providers[pv].apiKey){
                _currentApiProvider=pv;
                localStorage.setItem('active_api_provider',pv);
            }
            saveApiProviders(providers);
            updateApiIndicator();
            showToast(API_PROVIDERS[pv].name+' 配置已保存');
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
                const r=await fetch('/agent/api-test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:pv,apiKey:apiKey,apiUrl:apiUrl,model:model})});
                const d=await r.json();
                if(d.success){statusEl.innerHTML='<span style="color:#10b981;">&#x2705; 连接成功! 模型: '+(d.model||'OK')+'</span>';return;}
                lastError=d.error||'连接失败';
                if(d.error&&d.error.includes('401')&&attempt===1){
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
        
        let modelsConfig = JSON.parse(localStorage.getItem('models_config') || '{}');
        
        function openModelsConfig() {
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu', 'mistral', 'groq', 'xai'];
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
            const models = ['openai', 'claude', 'gemini', 'qwen', 'moonshot', 'zhipu', 'mistral', 'groq', 'xai'];
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
                    if (!currentReader) break;
                    const { done, value } = await currentReader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split("\n");
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                // 处理正式回答内容
                                if (data.content) {
                                    fullContent += data.content;
                                    // 生成过程中显示原始文本，避免 markdown 解析错误
                                    contentEl.innerHTML = fullContent.replace(/\n/g, '<br>');
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                // 处理思考过程内容
                                if (data.reasoning) {
                                    fullReasoning += data.reasoning;
                                    hasReasoning = true;
                                    if (reasoningSection) reasoningSection.style.display = 'block';
                                    if (reasoningContentEl) reasoningContentEl.textContent = fullReasoning;
                                    requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
                                }
                                if (data.done) {
                                    // 生成完成后渲染 markdown
                                    if (settings.markdown) {
                                        contentEl.innerHTML = safeMarkedParse(fullContent);
                                    }
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
