// Project center, console, workspace, ops, release, alert, AB, and integration panels extracted from the main shell.
        function projectGet(path) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.get(path);
        }

        function projectPost(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.json(path, payload || {});
        }

        function projectPut(path, payload) {
            if (!window.KaguyaAPI) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.put(path, payload || {});
        }

        function projectRaw(path, options) {
            if (!window.KaguyaAPI || !window.KaguyaAPI.raw) return Promise.reject(new Error('api_client_unavailable'));
            return window.KaguyaAPI.raw(path, options || {});
        }

        let _projectCenterLoading = false;
        function loadProjectCenter() {
            if (_projectCenterLoading) return;
            _projectCenterLoading = true;
            projectPost('/project/batch').then(res => {
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
            projectGet(`/workspace/projects?q=${q}`).then(data => {
                if (!data.success) return;
                workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
        }

        function refreshWorkspaceProjects() {
            projectGet('/workspace/projects?refresh=1').then(data => {
                if (data.success) workspaceProjects = data.projects || [];
                renderWorkspaceProjects();
            });
            projectGet('/workspace/projects/overview').then(data => {
                if (data.success) workspaceOverview = data.overview || {};
                renderWorkspaceOverview();
                renderFeatureCenterMeta();
            });
        }

        function loadConsoleData() {
            Promise.all([
                projectGet('/console/overview'),
                projectGet('/console/recommendations')
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
            projectGet('/system/metrics')
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
            projectPost('/scheduler/tasks', { name, time, repeat, type }).then(data => {
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
            projectGet('/scheduler/tasks')
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
            projectGet('/performance/stats?range=' + range)
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
            projectRaw('/performance/export')
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
            projectGet('/console/governance-report')
                .then(data => {
                    if (data.success) {
                        showToast('治理报告已生成');
                    }
                });
        }

        function checkAllServicesHealth() {
            showToast('正在检查服务健康状态...');
            projectGet('/services/health-check')
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
            projectPost('/services/' + serviceId + '/restart')
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
            projectGet('/dependencies/analyze')
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
            projectGet('/dependencies/security-check')
                .then(data => {
                    if (data.success) {
                        showToast('发现 ' + (data.vulnerabilities?.length || 0) + ' 个潜在问题');
                    }
                });
        }

        function refreshGitStatus() {
            projectGet('/git/status')
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
            projectPost('/workspace/projects', { name, path, description: desc }).then(data => {
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
            projectGet('/templates/search?q=' + encodeURIComponent(query))
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
            projectPost('/deploy/execute', { target }).then(data => {
                showToast(data.success ? '部署成功' : '部署失败');
            });
        }

        function refreshDataFlowStats() {
            projectGet('/dataflow/stats')
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
            projectGet(`/search/global?q=${q}&entity=${entity}&limit=60`).then(data => {
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
            projectGet(`/artifacts?q=${q}`).then(data => {
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
            (editingArtifactId ? projectPut(url, payload) : projectPost(url, payload)).then(data => {
                if (!data.success) return showToast(data.error || '保存失败');
                closeModal('artifactModal');
                showToast(editingArtifactId ? '产物已更新' : '产物已新增');
                recordFeatureAction(editingArtifactId ? '更新产物' : '新增产物', '项目中台');
                editingArtifactId = null;
                loadProjectCenter();
            });
        }
        
        function showArtifactVersions(id) {
            projectGet(`/artifacts/${id}/versions`).then(data => {
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
            projectPost(`/artifacts/${id}/restore`, {version, editor: 'ui'}).then(data => {
                if (!data.success) return showToast(data.error || '回滚失败');
                showToast('已回滚到指定版本');
                closeModal('artifactVersionsModal');
                loadProjectCenter();
            });
        }
        
        function toggleArtifactPin(id, pinned) {
            projectPost(`/artifacts/${id}/pin`, {pinned}).then(data => {
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
            projectPost('/project/tasks', {title, description, priority, owner, status: 'todo'}).then(data => {
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
            projectPost(`/project/tasks/${draggingTaskId}/status`, {status}).then(data => {
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
            projectPost('/project/tasks/batch_status', {task_ids: ids, status}).then(data => {
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
            projectPost('/playbooks', {name, category, description, template}).then(data => {
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
            projectPost(`/playbooks/${id}/run`, {topic, goal, context, constraints}).then(data => {
                if (!data.success) return showToast(data.error || '运行失败');
                usePrompt(data.prompt || '');
                switchTab('prompts', document.querySelector('.sidebar-tab[onclick*="prompts"]'));
                showToast('剧本已生成并填入输入框');
                recordFeatureAction('运行剧本模板', '项目中台');
            });
        }
        
        function loadProjectActivity() {
            projectGet('/project/activity?limit=40').then(data => {
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
            projectPost('/project/milestones', payload).then(data => {
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
            projectPost('/project/risks', payload).then(data => {
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
            projectGet(`/ops/campaigns?q=${q}`).then(data => {
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
            projectPost('/ops/campaigns', payload).then(data => {
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
            projectPost('/release/plans', payload).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('releasePlanModal');
                showToast('已新增发布计划');
                recordFeatureAction('新增发布计划', '发布中心');
                loadProjectCenter();
            });
        }
        
        function updateReleaseStatus(id, status) { crudUpdate('/release/plans', id, {status}); }
        
        function toggleReleaseCheck(id, index, checked) {
            projectPost(`/release/plans/${id}/check`, {index, checked}).then(data => {
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
            projectPost('/alerts/rules', payload).then(data => {
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
            projectPost('/ab/experiments', payload).then(data => {
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
            projectPost(`/ab/experiments/${id}/metrics`, {baseline, variant}).then(data => {
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
            projectPost('/integrations', payload).then(data => {
                if (!data.success) return showToast(data.error || '创建失败');
                closeModal('integrationModal');
                showToast('已新增集成');
                recordFeatureAction('新增集成', '集成市场');
                loadProjectCenter();
            });
        }

        function updateIntegrationStatus(id, status) { crudUpdate('/integrations', id, {status}); }

        function deleteIntegration(id) { crudDelete('/integrations', id, () => showToast('已删除集成')); }
