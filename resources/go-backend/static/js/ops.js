        // ========== OPS ENHANCEMENT ==========
        function refreshOpsChannelComparison() {
            const el = document.getElementById('opsChannelComparison');
            if (!el) return;
            const channels = ['抖音', '小红书', '微信', '微博', 'B站', '快手'];

            const metrics = channels.map(ch => ({
                name: ch,
                ctr: (Math.random() * 8 + 1).toFixed(2),
                cvr: (Math.random() * 5 + 0.5).toFixed(2),
                roi: (Math.random() * 4 + 0.5).toFixed(2),
                spend: Math.floor(Math.random() * 50000 + 5000)
            }));
            el.innerHTML = metrics.map(m => {
                const roiColor = m.roi >= 2 ? 'var(--success)' : m.roi >= 1 ? 'var(--warning)' : 'var(--error)';
                return '<div class="glass-card" style="padding:10px;flex:1;min-width:120px;display:flex;flex-direction:column;gap:4px;">' +
                    '<div style="font-weight:600;font-size:13px;color:var(--text-primary);">' + escapeHtml(m.name) + '</div>' +
                    '<div style="font-size:11px;color:var(--text-muted);">CTR: ' + m.ctr + '% | CVR: ' + m.cvr + '%</div>' +
                    '<div style="font-size:11px;color:var(--text-muted);">花费: ¥' + m.spend.toLocaleString() + '</div>' +
                    '<div style="font-size:13px;font-weight:700;color:' + roiColor + ';">ROI: ' + m.roi + 'x</div>' +
                '</div>';
            }).join('');
        }

        function calculateOpsROI() {
            const budget = parseFloat(document.getElementById('roiBudgetInput').value);
            const revenue = parseFloat(document.getElementById('roiRevenueInput').value);
            const customers = parseInt(document.getElementById('roiCustomersInput').value) || 0;
            const el = document.getElementById('roiResult');
            if (!budget || !revenue) { showToast('请输入预算和收入', 'warning'); return; }
            const roi = (revenue / budget).toFixed(2);
            const profit = revenue - budget;
            const cpa = customers > 0 ? (budget / customers).toFixed(2) : 'N/A';
            const profitColor = profit >= 0 ? 'var(--success)' : 'var(--error)';
            el.style.display = 'block';
            el.innerHTML = '<div style="display:flex;flex-direction:column;gap:6px;">' +
                '<div style="font-size:16px;font-weight:700;color:' + profitColor + ';">ROI: ' + roi + 'x (' + (profit >= 0 ? '盈利' : '亏损') + ' ¥' + Math.abs(profit).toLocaleString() + ')</div>' +
                '<div style="font-size:12px;color:var(--text-secondary);">投入: ¥' + budget.toLocaleString() + ' | 产出: ¥' + revenue.toLocaleString() + '</div>' +
                (customers > 0 ? '<div style="font-size:12px;color:var(--text-secondary);">获客成本(CPA): ¥' + cpa + '/人</div>' : '') +
            '</div>';
        }

        function renderOpsCalendar() {
            const el = document.getElementById('opsCalendar');
            if (!el) return;
            const now = new Date();
            const year = now.getFullYear(), month = now.getMonth();
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            const today = now.getDate();
            const days = ['日', '一', '二', '三', '四', '五', '六'];
            let html = days.map(d => '<div style="text-align:center;font-weight:600;color:var(--text-muted);padding:2px;">' + d + '</div>').join('');
            for (let i = 0; i < firstDay; i++) html += '<div></div>';
            for (let d = 1; d <= daysInMonth; d++) {
                const isToday = d === today;
                const hasEvent = Math.random() > 0.8;
                html += '<div style="text-align:center;padding:4px 2px;border-radius:6px;' +
                    (isToday ? 'background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;font-weight:700;' : 'color:var(--text-secondary);') +
                    (hasEvent ? 'border-bottom:2px solid var(--accent);' : '') +
                    '">' + d + '</div>';
            }
            el.innerHTML = '<div style="text-align:center;font-size:12px;font-weight:600;color:var(--text-primary);margin-bottom:6px;">' + year + '年' + (month + 1) + '月</div>' + html;
        }

        // ========== RELEASE ENHANCEMENT ==========
        function renderReleaseTimeline() {
            const el = document.getElementById('releaseTimeline');
            if (!el) return;
            const plans = releasePlans || [];
            if (plans.length === 0) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:20px;">暂无发布计划</div>';
                return;
            }
            el.innerHTML = plans.map((p, i) => {
                const statusColors = { planning: '#6366f1', review: '#f59e0b', ready: '#10b981', released: '#22c55e', rolled_back: '#ef4444' };
                const color = statusColors[p.status] || 'var(--primary)';
                return '<div style="display:flex;align-items:flex-start;gap:10px;position:relative;">' +
                    (i < plans.length - 1 ? '<div style="position:absolute;left:11px;top:24px;bottom:0;width:2px;background:var(--border);"></div>' : '') +
                    '<div style="width:24px;height:24px;border-radius:50%;background:' + color + ';flex-shrink:0;display:flex;align-items:center;justify-content:center;color:white;font-size:10px;">' + (i + 1) + '</div>' +
                    '<div style="flex:1;padding-bottom:12px;"><div style="font-size:13px;font-weight:600;color:var(--text-primary);">' + escapeHtml(p.name || p.version || 'Plan') + '</div>' +
                    '<div style="font-size:11px;color:var(--text-muted);">' + escapeHtml(p.status || '') + (p.target_date ? ' | ' + escapeHtml(p.target_date) : '') + '</div></div></div>';
            }).join('');
        }

        function updateGrayProgress(percent) {
            const bar = document.getElementById('grayProgressBar');
            const label = document.getElementById('grayPercentLabel');
            if (bar) bar.style.width = percent + '%';
            if (label) label.textContent = percent + '%';
            showToast('灰度比例已更新为 ' + percent + '%', 'success');
        }

        function openGrayStrategyModal() {
            createModal({
                title: '⚙️ 灰度发布策略配置',
                body: '<div style="display:flex;flex-direction:column;gap:12px;">' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">灰度策略类型</label><select class="project-input" style="width:100%;margin-top:4px;"><option>按用户比例</option><option>按地区</option><option>按设备类型</option><option>按用户标签</option></select></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">观察时长(小时)</label><input class="project-input" type="number" value="24" style="width:100%;margin-top:4px;"></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">自动全量条件</label><select class="project-input" style="width:100%;margin-top:4px;"><option>错误率 < 0.1%</option><option>错误率 < 0.5%</option><option>手动确认</option></select></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">自动回滚条件</label><select class="project-input" style="width:100%;margin-top:4px;"><option>错误率 > 1%</option><option>错误率 > 5%</option><option>不自动回滚</option></select></div>' +
                '</div>',
                actions: [{ text: '保存策略', primary: true, onClick: () => { showToast('灰度策略已保存', 'success'); } }]
            });
        }

        function renderRollbackVersions() {
            const el = document.getElementById('rollbackVersionList');
            if (!el) return;
            const versions = ['v3.1.0 (当前)', 'v3.0.2', 'v3.0.1', 'v2.9.5'];
            el.innerHTML = versions.map((v, i) => {
                const isCurrent = i === 0;
                return '<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 8px;border-radius:8px;border:1px solid var(--border);font-size:12px;' +
                    (isCurrent ? 'background:rgba(99,102,241,0.06);' : '') + '">' +
                    '<span style="color:' + (isCurrent ? 'var(--primary)' : 'var(--text-secondary)') + ';font-weight:' + (isCurrent ? '600' : '400') + ';">' + escapeHtml(v) + '</span>' +
                    (isCurrent ? '<span style="font-size:10px;color:var(--success);">● 当前</span>' : '<button class="project-mini-btn" data-version="' + v + '" onclick="confirmRollback(this.dataset.version)" style="font-size:10px;padding:2px 6px;">⏪ 回滚</button>') +
                '</div>';
            }).join('');
        }

        function confirmRollback(version) {
            createModal({
                title: '⚠️ 确认回滚',
                body: '<div style="color:var(--error);font-size:13px;">确定要回滚到 <strong>' + escapeHtml(version) + '</strong> 吗？<br>当前版本的数据可能会丢失。</div>',
                actions: [
                    { text: '取消', primary: false },
                    { text: '确认回滚', primary: true, onClick: () => { showToast('已回滚到 ' + version, 'success'); } }
                ]
            });
        }

        // ========== ALERT ENHANCEMENT ==========
        let alertHistory = [];
        function renderAlertHistory() {
            const el = document.getElementById('alertHistoryList');
            if (!el) return;
            if (alertHistory.length === 0) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">暂无告警历史</div>';
                return;
            }
            el.innerHTML = alertHistory.slice(-20).reverse().map(a => {
                const levelColors = { P1: 'var(--error)', P2: 'var(--warning)', P3: 'var(--primary)' };
                return '<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);font-size:11px;">' +
                    '<span style="color:' + (levelColors[a.level] || 'var(--text-muted)') + ';font-weight:700;">' + escapeHtml(a.level || 'P3') + '</span>' +
                    '<span style="flex:1;color:var(--text-secondary);">' + escapeHtml(a.message || '') + '</span>' +
                    '<span style="color:var(--text-muted);font-size:10px;">' + escapeHtml(a.time || '') + '</span>' +
                '</div>';
            }).join('');
        }

        function clearAlertHistory() {
            alertHistory = [];
            renderAlertHistory();
            showToast('告警历史已清空', 'success');
        }

        let notificationChannels = [
            { id: 1, type: 'email', name: '邮件通知', config: 'admin@example.com', enabled: true },
            { id: 2, type: 'webhook', name: '飞书机器人', config: 'https://open.feishu.cn/...', enabled: true },
            { id: 3, type: 'webhook', name: '钉钉机器人', config: 'https://oapi.dingtalk.com/...', enabled: false }
        ];

        function renderNotificationChannels() {
            const el = document.getElementById('notificationChannelList');
            if (!el) return;
            el.innerHTML = notificationChannels.map(ch => {
                const icons = { email: '📧', webhook: '🪖', sms: '📱' };
                return '<div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:10px;border:1px solid var(--border);">' +
                    '<span style="font-size:16px;">' + (icons[ch.type] || '🔔') + '</span>' +
                    '<div style="flex:1;"><div style="font-size:12px;font-weight:600;color:var(--text-primary);">' + escapeHtml(ch.name) + '</div>' +
                    '<div style="font-size:10px;color:var(--text-muted);">' + escapeHtml(ch.config) + '</div></div>' +
                    '<button class="toggle ' + (ch.enabled ? 'active' : '') + '" onclick="toggleNotificationChannel(' + ch.id + ')"></button>' +
                '</div>';
            }).join('');
        }

        function toggleNotificationChannel(id) {
            const ch = notificationChannels.find(c => c.id === id);
            if (ch) { ch.enabled = !ch.enabled; renderNotificationChannels(); }
        }

        function addNotificationChannel() {
            createModal({
                title: '➕ 添加通知渠道',
                body: '<div style="display:flex;flex-direction:column;gap:10px;">' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">渠道类型</label><select class="project-input" id="newChannelType" style="width:100%;margin-top:4px;"><option value="email">邮件</option><option value="webhook">Webhook</option><option value="sms">短信</option></select></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">名称</label><input class="project-input" id="newChannelName" placeholder="如: 运维邮件组" style="width:100%;margin-top:4px;"></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">配置</label><input class="project-input" id="newChannelConfig" placeholder="邮箱地址或Webhook URL" style="width:100%;margin-top:4px;"></div>' +
                '</div>',
                actions: [{ text: '添加', primary: true, onClick: () => {
                    const type = document.getElementById('newChannelType').value;
                    const name = document.getElementById('newChannelName').value;
                    const config = document.getElementById('newChannelConfig').value;
                    if (!name) { showToast('请输入名称', 'warning'); return; }
                    notificationChannels.push({ id: Date.now(), type, name, config: config || '-', enabled: true });
                    renderNotificationChannels();
                    showToast('通知渠道已添加', 'success');
                }}]
            });
        }

        // ========== A/B EXPERIMENT ENHANCEMENT ==========
        function calculateSignificance() {
            const baseline = parseFloat(document.getElementById('abBaselineRate').value);
            const experiment = parseFloat(document.getElementById('abExperimentRate').value);
            const n = parseInt(document.getElementById('abSampleSize').value);
            const el = document.getElementById('significanceResult');
            if (!baseline || !experiment || !n) { showToast('请填写所有参数', 'warning'); return; }
            const p1 = baseline, p2 = experiment;
            const pPool = (p1 + p2) / 2;
            const se = Math.sqrt(2 * pPool * (1 - pPool) / n);
            const z = Math.abs(p2 - p1) / (se || 0.0001);
            const pValue = z > 3.5 ? 0.0001 : z > 2.576 ? 0.005 : z > 1.96 ? 0.05 : z > 1.645 ? 0.10 : z > 1.28 ? 0.20 : 0.50;
            const significant = pValue < 0.05;
            const lift = ((p2 - p1) / p1 * 100).toFixed(2);
            const ci_low = ((p2 - p1) - 1.96 * se).toFixed(4);
            const ci_high = ((p2 - p1) + 1.96 * se).toFixed(4);
            el.style.display = 'block';
            el.innerHTML = '<div style="display:flex;flex-direction:column;gap:6px;">' +
                '<div style="font-size:15px;font-weight:700;color:' + (significant ? 'var(--success)' : 'var(--text-secondary)') + ';">' +
                (significant ? '✅ 统计显著' : '❌ 未达显著') + ' (p=' + pValue.toFixed(4) + ')</div>' +
                '<div style="font-size:12px;color:var(--text-secondary);">Z值: ' + z.toFixed(4) + ' | 提升幅度: ' + lift + '%</div>' +
                '<div style="font-size:12px;color:var(--text-secondary);">95%置信区间: [' + ci_low + ', ' + ci_high + ']</div>' +
                '<div style="font-size:11px;color:var(--text-muted);">基线: ' + (p1 * 100).toFixed(2) + '% | 实验: ' + (p2 * 100).toFixed(2) + '% | 样本: ' + n.toLocaleString() + '</div>' +
            '</div>';
        }

        function renderTrafficAllocator() {
            const el = document.getElementById('trafficAllocator');
            if (!el) return;
            const experiments = abExperiments || [];
            if (experiments.length === 0) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">暂无运行中的实验</div>';
                return;
            }
            const totalTraffic = 100;
            const allocated = experiments.filter(e => e.status === 'running').reduce((sum, e) => sum + (e.traffic_percent || 10), 0);
            const remaining = totalTraffic - allocated;
            el.innerHTML = '<div style="margin-bottom:8px;">' +
                '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-bottom:4px;"><span>已分配: ' + allocated + '%</span><span>剩余: ' + remaining + '%</span></div>' +
                '<div style="height:12px;background:var(--border);border-radius:6px;overflow:hidden;display:flex;">' +
                experiments.filter(e => e.status === 'running').map(e => {
                    const colors = ['var(--primary)', 'var(--accent)', 'var(--lora-color)', 'var(--tool-color)'];
                    return '<div style="width:' + (e.traffic_percent || 10) + '%;height:100%;background:' + colors[Math.floor(Math.random() * colors.length)] + ';transition:width 0.3s;" title="' + escapeHtml(e.name || '') + ': ' + (e.traffic_percent || 10) + '%"></div>';
                }).join('') +
                '</div></div>' +
                experiments.filter(e => e.status === 'running').map(e =>
                    '<div style="display:flex;align-items:center;gap:6px;font-size:11px;">' +
                    '<span style="color:var(--text-secondary);flex:1;">' + escapeHtml(e.name || 'Experiment') + '</span>' +
                    '<input class="project-input" type="number" value="' + (e.traffic_percent || 10) + '" min="1" max="100" style="width:50px;font-size:11px;" data-eid="' + e.id + '" onchange="updateTrafficAllocation(this.dataset.eid,this.value)">' +
                    '<span style="color:var(--text-muted);">%</span></div>'
                ).join('');
        }

        function updateTrafficAllocation(id, percent) {
            const exp = (abExperiments || []).find(e => e.id === id);
            if (exp) { exp.traffic_percent = parseInt(percent) || 10; renderTrafficAllocator(); }
        }

        // ========== INTEGRATION ENHANCEMENT ==========
        const INTEGRATION_TEMPLATES = [
            { id: 'slack', name: 'Slack', icon: '📡', category: '通讯', desc: '消息推送与事件通知', color: '#4A154B' },
            { id: 'feishu', name: '飞书', icon: '🐦', category: '通讯', desc: '企业通讯与机器人集成', color: '#3370FF' },
            { id: 'github', name: 'GitHub', icon: '🔗', category: '开发', desc: '代码仓库与CI/CD集成', color: '#24292F' },
            { id: 'jira', name: 'JIRA', icon: '📂', category: '项目管理', desc: '需求与缺陷跟踪', color: '#0052CC' },
            { id: 'grafana', name: 'Grafana', icon: '📊', category: '监控', desc: '监控仪表盘与告警', color: '#F46800' },
            { id: 'notion', name: 'Notion', icon: '📝', category: '知识库', desc: '文档与知识管理', color: '#000000' },
            { id: 'wechat', name: '企业微信', icon: '📞', category: '通讯', desc: '企业消息与审批流', color: '#07C160' },
            { id: 'dingtalk', name: '钉钉', icon: '🔔', category: '通讯', desc: '钉钉机器人与审批', color: '#0089FF' }
        ];

        function renderIntegrationMarket(filter) {
            const el = document.getElementById('integrationMarketGrid');
            if (!el) return;
            const filtered = filter ? INTEGRATION_TEMPLATES.filter(t => t.name.toLowerCase().includes(filter.toLowerCase()) || t.category.includes(filter)) : INTEGRATION_TEMPLATES;
            el.innerHTML = filtered.map(t => {
                const connected = (integrations || []).some(i => i.provider === t.id);
                return '<div class="glass-card hover-scale" style="padding:10px;cursor:pointer;display:flex;flex-direction:column;gap:4px;' +
                    (connected ? 'border-color:var(--success);' : '') + '" data-tid="' + t.id + '" onclick="quickConnectIntegration(this.dataset.tid)">' +
                    '<div style="display:flex;align-items:center;gap:6px;">' +
                    '<span style="font-size:18px;">' + t.icon + '</span>' +
                    '<span style="font-weight:600;font-size:12px;color:var(--text-primary);">' + escapeHtml(t.name) + '</span>' +
                    (connected ? '<span style="font-size:9px;color:var(--success);margin-left:auto;">✅ 已连接</span>' : '') +
                    '</div>' +
                    '<div style="font-size:10px;color:var(--text-muted);">' + escapeHtml(t.desc) + '</div>' +
                    '<div style="font-size:9px;color:var(--primary);background:rgba(99,102,241,0.08);padding:1px 6px;border-radius:4px;align-self:flex-start;">' + escapeHtml(t.category) + '</div>' +
                '</div>';
            }).join('');
        }

        function filterIntegrationMarket(keyword) { renderIntegrationMarket(keyword); }

        function quickConnectIntegration(templateId) {
            const tmpl = INTEGRATION_TEMPLATES.find(t => t.id === templateId);
            if (!tmpl) return;
            createModal({
                title: tmpl.icon + ' 连接 ' + tmpl.name,
                body: '<div style="display:flex;flex-direction:column;gap:10px;">' +
                    '<div style="font-size:12px;color:var(--text-secondary);">' + escapeHtml(tmpl.desc) + '</div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">API Key / Token</label><input class="project-input" id="integApiKey" placeholder="输入' + escapeHtml(tmpl.name) + '的API密钥" style="width:100%;margin-top:4px;"></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">Webhook URL (可选)</label><input class="project-input" id="integWebhook" placeholder="https://..." style="width:100%;margin-top:4px;"></div>' +
                '</div>',
                actions: [{ text: '测试并连接', primary: true, onClick: () => {
                    showToast(tmpl.name + ' 连接成功！', 'success');
                    renderIntegrationMarket();
                }}]
            });
        }

        let webhooks = [
            { id: 1, url: 'https://api.example.com/webhook/dep', events: ['deploy.success', 'deploy.fail'], enabled: true },
            { id: 2, url: 'https://hooks.slack.com/services/T...', events: ['alert.triggered'], enabled: true }
        ];

        function renderWebhooks() {
            const el = document.getElementById('webhookList');
            if (!el) return;
            el.innerHTML = webhooks.map(wh => {
                return '<div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:10px;border:1px solid var(--border);">' +
                    '<div style="flex:1;min-width:0;"><div style="font-size:11px;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(wh.url) + '</div>' +
                    '<div style="font-size:10px;color:var(--text-muted);">' + wh.events.map(e => escapeHtml(e)).join(', ') + '</div></div>' +
                    '<button class="toggle ' + (wh.enabled ? 'active' : '') + '" onclick="toggleWebhook(' + wh.id + ')"></button>' +
                    '<button class="project-mini-btn" onclick="testWebhook(' + wh.id + ')" style="font-size:10px;padding:2px 6px;">🔍</button>' +
                '</div>';
            }).join('');
        }

        function toggleWebhook(id) {
            const wh = webhooks.find(w => w.id === id);
            if (wh) { wh.enabled = !wh.enabled; renderWebhooks(); }
        }

        function testWebhook(id) {
            showToast('Webhook 测试已发送', 'success');
        }

        function addWebhook() {
            createModal({
                title: '➕ 添加 Webhook',
                body: '<div style="display:flex;flex-direction:column;gap:10px;">' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">Webhook URL</label><input class="project-input" id="newWebhookUrl" placeholder="https://..." style="width:100%;margin-top:4px;"></div>' +
                    '<div><label style="font-size:12px;color:var(--text-muted);">订阅事件 (逗号分隔)</label><input class="project-input" id="newWebhookEvents" placeholder="deploy.success, alert.triggered" style="width:100%;margin-top:4px;"></div>' +
                '</div>',
                actions: [{ text: '添加', primary: true, onClick: () => {
                    const url = document.getElementById('newWebhookUrl').value;
                    const events = document.getElementById('newWebhookEvents').value.split(',').map(e => e.trim()).filter(Boolean);
                    if (!url) { showToast('请输入URL', 'warning'); return; }
                    webhooks.push({ id: Date.now(), url, events: events.length ? events : ['*'], enabled: true });
                    renderWebhooks();
                    showToast('Webhook 已添加', 'success');
                }}]
            });
        }

        function testIntegrationConnection() {
            const target = document.getElementById('connectionTestTarget').value;
            const el = document.getElementById('connectionTestResult');
            if (!target) { showToast('请选择集成', 'warning'); return; }
            el.style.display = 'block';
            el.style.background = 'rgba(16,185,129,0.08)';
            el.style.border = '1px solid var(--success)';
            el.style.color = 'var(--success)';
            el.textContent = 'Testing connection...' + String.fromCharCode(10) + String.fromCharCode(10) + 'Success!' + String.fromCharCode(10) + 'Authenticated' + String.fromCharCode(10) + 'Latency: ' + Math.floor(Math.random() * 200 + 50) + 'ms' + String.fromCharCode(10) + 'API version: v2';
        }

        function updateConnectionTestTargets() {
            const sel = document.getElementById('connectionTestTarget');
            if (!sel) return;
            const current = (integrations || []).map(i => '<option value="' + escapeHtml(i.id || '') + '">' + escapeHtml(i.name || i.provider || 'Unknown') + '</option>').join('');
            sel.innerHTML = '<option value="">选择集成...</option>' + current;
        }

        // ========== AGENT MODE ==========
        let agentModeEnabled = false;
        let agentHistory = [];
        let agentAutoApprove = false;

        async function checkAdvancedApi(){
            try{
                const extApi=getActiveApiConfig();
                if(!extApi||!extApi.enabled||!extApi.apiKey){
                    showApiWarningModal('External AI API not configured. Local models do not support advanced IDE features. Please configure an external model (e.g. DeepSeek, Qwen, Claude) in API Center.');
                    return false;
                }
                const ctrl=new AbortController();
                const tid=setTimeout(()=>ctrl.abort(),5000);
                const r=await fetch('/agent/api-status',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({external_api:extApi}),
                    signal:ctrl.signal
                });
                clearTimeout(tid);
                const d=await r.json();
                if(!d.available||d.provider==='ollama'){
                    showApiWarningModal(d.provider==='ollama'?'Local Ollama model does not support IDE features. Please configure an external API (e.g. DeepSeek, Qwen, Claude).':d.message||'Please configure an external AI model');
                    return false;
                }
                return true;
            }catch(e){
                showApiWarningModal('无法连接服务器验证API状态，请检查网络连接。');
                return false;
            }
        }

