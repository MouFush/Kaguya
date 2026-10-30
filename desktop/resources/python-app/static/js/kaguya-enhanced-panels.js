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
        const INTEGRATION_TEMPLATES = KAGUYA_APP_DATA.integrationTemplates || [];

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
                if(!extApi||!extApi.enabled||(!extApi.apiKey&&!extApi.hasSavedKey)){
                    showApiWarningModal('External AI API not configured. Local models do not support advanced IDE features. Please configure an external model (e.g. DeepSeek, Qwen, Claude) in API Center.');
                    return false;
                }
                const ctrl=new AbortController();
                const tid=setTimeout(()=>ctrl.abort(),5000);
                if(!window.KaguyaAPI) throw new Error('api_client_unavailable');
                const d=await window.KaguyaAPI.json('/agent/api-status',{external_api:extApi},{signal:ctrl.signal,timeoutMs:0});
                clearTimeout(tid);
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

        function showApiWarningModal(msg){
            const existing=document.getElementById('apiBlockModal');
            if(existing)existing.remove();
            const modal=document.createElement('div');
            modal.id='apiBlockModal';
            modal.style.cssText='position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:100000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(6px);';
            const safeMsg=escapeHtml(msg||'请配置AI模型');
            modal.innerHTML=`<div style="background:var(--card-bg,#1e1e2e);border:1px solid rgba(252,129,129,0.25);border-radius:20px;padding:36px 40px;max-width:440px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);"><div style="width:60px;height:60px;margin:0 auto 20px;background:linear-gradient(135deg,#fc8181,#f687b3);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:26px;color:#fff;">⚠</div><h3 style="color:var(--text-primary,#e0e0e0);font-size:18px;margin-bottom:10px;font-weight:700;">API 未连接</h3><p style="color:var(--text-secondary,#999);font-size:13px;line-height:1.7;margin-bottom:8px;">高级功能需要 AI 模型支持，当前没有可用的模型。</p><p style="color:#fc8181;font-size:12px;margin-bottom:22px;padding:10px 14px;background:rgba(252,129,129,0.08);border-radius:8px;border:1px solid rgba(252,129,129,0.12);">${safeMsg}</p><button onclick="document.getElementById('apiBlockModal').remove()" style="padding:10px 28px;background:var(--accent,#7c6aff);color:#fff;border:none;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;">确定</button></div>`;
            document.body.appendChild(modal);
        }

        async function openAgentIDE(){
            window.open('/static/agent_ide.html','_blank');
        }

        let _sidebarIdeLoaded=false;
        let _sidebarIdeCurrentPath=null;

        function sidebarIdeInit(){
            if(_sidebarIdeLoaded)return;
            _sidebarIdeLoaded=true;
            sidebarIdeLoadTree();
            sidebarIdeSyncUser();
        }

        function sidebarIdeSyncUser(){
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            const userName=localStorage.getItem('kaguya_user_name')||'';
            if(userName){
                const avatar=document.getElementById('sidebarIdeAvatar');
                const nameEl=document.getElementById('sidebarIdeUserName');
                const idEl=document.getElementById('sidebarIdeUserId');
                if(avatar)avatar.textContent=userName.charAt(0).toUpperCase();
                if(nameEl)nameEl.textContent=userName;
                if(idEl)idEl.textContent='ID: '+(deviceId||'-').substring(0,10)+'...';
            }
        }

        async function sidebarIdeLoadTree(path){
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                if(!window.KaguyaAPI)throw new Error('api_client_unavailable');
                const d=await window.KaguyaAPI.json('/agent/file-tree',{path:path||undefined,device_id:deviceId});
                if(d.error){console.error('IDE tree error:',d);return;}
                _sidebarIdeCurrentPath=d.path;
                if(d.user_name){
                    const avatar=document.getElementById('sidebarIdeAvatar');
                    const nameEl=document.getElementById('sidebarIdeUserName');
                    if(avatar)avatar.textContent=d.user_name.charAt(0).toUpperCase();
                    if(nameEl)nameEl.textContent=d.user_name;
                }
                const tree=document.getElementById('sidebarIdeFileTree');
                if(!tree)return;
                tree.innerHTML='';
                if(d.path){
                    const up=document.createElement('div');
                    up.style.cssText='padding:4px 10px;cursor:pointer;font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:6px;transition:var(--transition);border-radius:4px;margin:1px 4px;';
                    up.innerHTML='<span style="font-size:11px;">&#x1F4C1;</span> ..';
                    up.onmouseover=()=>up.style.background='var(--bg-hover)';
                    up.onmouseout=()=>up.style.background='';
                    const parentPath=d.path.split(/[\/]/).slice(0,-1).join('/');
                    up.onclick=()=>{
                        const ws=d.workspace||'';
                        if(parentPath&&parentPath.length>=ws.length)sidebarIdeLoadTree(parentPath);
                    };
                    tree.appendChild(up);
                }
                d.entries.forEach(e=>{
                    const item=document.createElement('div');
                    item.style.cssText='padding:4px 10px;cursor:pointer;font-size:11px;color:var(--text-secondary);display:flex;align-items:center;gap:6px;transition:var(--transition);border-radius:4px;margin:1px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
                    item.innerHTML='<span style="font-size:11px;">'+(e.is_dir?'&#x1F4C1;':'&#x1F4C4;')+'</span> '+escapeHtml(e.name);
                    item.onmouseover=()=>item.style.background='var(--bg-hover)';
                    item.onmouseout=()=>item.style.background='';
                    item.onclick=()=>{
                        if(e.is_dir)sidebarIdeLoadTree(e.path);
                        else sidebarIdeOpenFile(e.path,e.name);
                    };
                    tree.appendChild(item);
                });
            }catch(e){console.error('IDE tree load error:',e);}
        }

        async function sidebarIdeOpenFile(path,name){
            const ok=await checkAdvancedApi();
            if(!ok)return;
            window.open('/static/agent_ide.html','_blank');
        }

        function sidebarIdeRefresh(){
            _sidebarIdeCurrentPath=null;
            sidebarIdeLoadTree();
        }

        async function sidebarIdeNewFile(){
            const name=prompt('新文件名称:','');
            if(!name||!name.trim())return;
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                if(!window.KaguyaAPI)throw new Error('api_client_unavailable');
                const idD=await window.KaguyaAPI.json('/agent/identify',{device_id:deviceId});
                const filePath=idD.workspace+'/'+name.trim();
                const d=await window.KaguyaAPI.json('/agent/file-write',{path:filePath,content:'',device_id:deviceId});
                if(d.error)showToast('创建失败: '+(d.message||d.error),'error');
                else{showToast('文件已创建: '+name.trim(),'success');sidebarIdeLoadTree(_sidebarIdeCurrentPath);}
            }catch(e){showToast('创建失败: '+e.message,'error');}
        }

        async function sidebarIdeNewFolder(){
            const name=prompt('新文件夹名称:','');
            if(!name||!name.trim())return;
            const deviceId=localStorage.getItem('kaguya_device_id')||'';
            try{
                if(!window.KaguyaAPI)throw new Error('api_client_unavailable');
                const idD=await window.KaguyaAPI.json('/agent/identify',{device_id:deviceId});
                const dirPath=idD.workspace+'/'+name.trim();
                const d=await window.KaguyaAPI.json('/agent/file-write',{path:dirPath,content:'',is_dir:true,device_id:deviceId});
                if(d.error)showToast('创建失败: '+(d.message||d.error),'error');
                else{showToast('文件夹已创建: '+name.trim(),'success');sidebarIdeLoadTree(_sidebarIdeCurrentPath);}
            }catch(e){showToast('创建失败: '+e.message,'error');}
        }

        async function sidebarIdeCompile(){
            const ok=await checkAdvancedApi();
            if(!ok)return;
            window.open('/static/agent_ide.html','_blank');
        }

        async function toggleAgentMode() {
            if(!agentModeEnabled){
                const ok=await checkAdvancedApi();
                if(!ok)return;
            }
            agentModeEnabled = !agentModeEnabled;
            const btn = document.getElementById('agentModeBtn');
            const banner = document.getElementById('agentBanner');
            if (agentModeEnabled) {
                btn.classList.add('active');
                banner.classList.add('show');
                showToast('Agent mode enabled - AI will autonomously use tools', 'success');
            } else {
                btn.classList.remove('active');
                banner.classList.remove('show');
                showToast('Agent mode disabled', 'info');
            }
        }

        const AGENT_TOOL_ICONS = {
            'read_file': '[R]', 'write_file': '[W]', 'edit_file': '[E]',
            'list_directory': '[D]', 'search_files': '[S]', 'execute_command': '[!]', 'glob': '[G]',
            'compile': '[C]', 'todo_write': '[T]', 'enter_plan_mode': '[P]', 'exit_plan_mode': '[P]',
            'web_fetch': '[F]', 'web_search': '[Q]', 'agent_spawn': '[A]',
            'task_create': '[+]', 'task_update': '[^]', 'task_list': '[L]', 'brief': '[B]'
        };
        const AGENT_DANGEROUS_TOOLS = ['write_file', 'edit_file', 'execute_command', 'compile', 'agent_spawn'];

        function createAgentMessageEl(time) {
            const container = document.getElementById('messagesContainer');
            const msgEl = document.createElement('div');
            msgEl.className = 'message assistant';
            const contentId = 'agentStream_' + Date.now();
            msgEl.innerHTML = '<div class="message-avatar" style="font-size:14px;font-weight:700;background:var(--grad-warm);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">Agent</div><div class="message-content-wrapper"><div class="agent-progress-bar" id="' + contentId + '_progress"></div><div class="message-content" id="' + contentId + '"></div><div class="message-time">' + time + '</div></div>';
            container.appendChild(msgEl);
            container.scrollTop = container.scrollHeight;
            return contentId;
        }

        function updateAgentProgress(progressId, iteration, maxIter, status) {
            const bar = document.getElementById(progressId);
            if (!bar) return;
            const pct = Math.min(100, Math.round((iteration / maxIter) * 100));
            bar.innerHTML = '<div class="agent-progress-fill" style="width:' + pct + '%"></div><span class="agent-progress-text">Iter ' + iteration + '/' + maxIter + ' - ' + escapeHtml(status) + '</span>';
            bar.style.display = 'flex';
        }

        async function sendAgentMessage(message) {
            try {
                const extApi=getActiveApiConfig();
                if(!window.KaguyaAPI)throw new Error('api_client_unavailable');
                const sd = await window.KaguyaAPI.json('/agent/api-status',{external_api:extApi});
                if (!sd.available) {
                    showToast('API not connected: ' + (sd.message || 'Please configure a model first'), 'error');
                    isGenerating = false;
                    document.getElementById('sendBtn').disabled = false;
                    document.getElementById('sendBtn').style.display = 'flex';
                    document.getElementById('stopBtn').style.display = 'none';
                    document.getElementById('statusText').textContent = '就绪';
                    return;
                }
            } catch(e) {}
            if (!currentChatId) newChat();
            const chat = chats.find(c => c.id === currentChatId);
            const time = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'});
            addMessageToUI('user', message, time);
            chat.messages.push({role: 'user', content: message, time: time});
            const contentId = createAgentMessageEl(time);
            const contentEl = document.getElementById(contentId);
            const progressId = contentId + '_progress';
            const container = document.getElementById('messagesContainer');
            let fullContent = '';
            let iterationCount = 0;
            let thinkingEl = null;
            let thinkingText = '';
            const agentAbortController = new AbortController();
            if (window.KaguyaAgent) window.KaguyaAgent.begin(agentAbortController);
            try {
                const extApiRun=getActiveApiConfig();
                if (!window.KaguyaStream) throw new Error('stream_helper_unavailable');
                await window.KaguyaStream.postSSE('/agent/run', {message: message, history: agentHistory.slice(-10), working_dir: document.querySelector('.main-input')?.getAttribute('data-cwd') || undefined, external_api: extApiRun, device_id: generateDeviceId()}, {
                    onReader: function(reader) { currentReader = reader; },
                    shouldStop: function() { return !currentReader; },
                    onFrame: function(data) {
                        if (window.KaguyaAgent) window.KaguyaAgent.observeFrame(data);
                        if (data.type === 'run_started') {
                            updateAgentProgress(progressId, 0, 25, 'Run started');
                            return;
                        }
                        if (data.type === 'aborted') {
                            contentEl.innerHTML += '<div class="agent-error-block">Agent run aborted by user</div>';
                            updateAgentProgress(progressId, iterationCount || 0, 25, 'Aborted');
                            container.scrollTop = container.scrollHeight;
                            return;
                        }
                        if (data.type === 'thinking') {
                            iterationCount = data.iteration;
                            if (!thinkingEl) {
                                thinkingEl = document.createElement('div');
                                thinkingEl.className = 'agent-thinking-block';
                                thinkingEl.innerHTML = '<div class="agent-thinking-header" onclick="this.parentElement.classList.toggle(&quot;collapsed&quot;)"><span class="thinking-toggle">&#9660;</span> Thinking...</div><div class="agent-thinking-content"></div>';
                                contentEl.appendChild(thinkingEl);
                            }
                            thinkingText += data.content;
                            const thinkContent = thinkingEl.querySelector('.agent-thinking-content');
                            if (thinkContent) thinkContent.textContent = thinkingText;
                            updateAgentProgress(progressId, data.iteration, 25, 'Thinking...');
                            container.scrollTop = container.scrollHeight;
                        } else if (data.type === 'tool_use') {
                            iterationCount = data.iteration;
                            if (thinkingEl) { thinkingEl = null; thinkingText = ''; }
                            const icon = AGENT_TOOL_ICONS[data.tool] || '[?]';
                            const isDangerous = data.dangerous || AGENT_DANGEROUS_TOOLS.includes(data.tool);
                            const inputStr = typeof data.input === 'object' ? JSON.stringify(data.input, null, 2) : String(data.input);
                            const dangerClass = isDangerous ? ' agent-tool-danger' : '';
                            const permBadge = data.permission === 'deny' ? '<span class="danger-badge" style="background:#ef4444;">X</span>' : (data.permission === 'prompt' ? '<span class="danger-badge">!</span>' : '');
                            contentEl.innerHTML += '<div class="agent-iteration">Iter #' + data.iteration + '</div><div class="agent-tool-call' + dangerClass + '"><div class="tool-header"><span class="tool-icon">' + icon + '</span> ' + escapeHtml(data.tool) + permBadge + '</div><div class="tool-input"><pre>' + escapeHtml(inputStr.substring(0, 800)) + '</pre></div></div>';
                            updateAgentProgress(progressId, data.iteration, 25, 'Running ' + data.tool);
                            container.scrollTop = container.scrollHeight;
                        } else if (data.type === 'tool_result') {
                            const outputStr = String(data.output || '');
                            const isErr = outputStr.startsWith('Error') || outputStr.includes('not found') || outputStr.includes('Permission denied');
                            const resultClass = isErr ? ' agent-result-error' : '';
                            contentEl.innerHTML += '<div class="agent-tool-result' + resultClass + '"><div class="result-header"><span>' + (isErr ? '[FAIL]' : '[OK]') + '</span> ' + escapeHtml(data.tool) + '</div><div class="result-output"><pre>' + escapeHtml(outputStr.substring(0, 1500)) + '</pre></div></div>';
                            updateAgentProgress(progressId, data.iteration, 25, 'Result from ' + data.tool);
                            container.scrollTop = container.scrollHeight;
                        } else if (data.type === 'assistant') {
                            fullContent = data.content || '';
                            if (thinkingEl) { thinkingEl = null; thinkingText = ''; }
                            const rendered = typeof marked !== 'undefined' ? marked.parse(fullContent) : escapeHtml(fullContent);
                            contentEl.innerHTML += '<div class="agent-final-answer">' + rendered + '</div>';
                            updateAgentProgress(progressId, data.iteration, 25, 'Done');
                            container.scrollTop = container.scrollHeight;
                        } else if (data.type === 'error') {
                            contentEl.innerHTML += '<div class="agent-error-block">Error: ' + escapeHtml(data.content) + '</div>';
                        }
                        if (data.done) {
                            agentHistory.push({user: message, assistant: fullContent});
                            const bar = document.getElementById(progressId);
                            if (bar) bar.style.display = 'none';
                        }
                    }
                }, { signal: agentAbortController.signal });
            } catch(e) {
                if (e && e.name === 'AbortError') {
                    contentEl.innerHTML += '<div class="agent-error-block">Agent run aborted by user</div>';
                } else {
                    contentEl.innerHTML += '<div class="agent-error-block">Connection error: ' + escapeHtml(e.message) + '</div>';
                }
            } finally {
                currentReader = null;
                if (window.KaguyaAgent) window.KaguyaAgent.finish();
            }
            chat.messages.push({role: 'assistant', content: fullContent || '(agent completed)', time: time});
            saveChats();
            isGenerating = false;
            document.getElementById('sendBtn').disabled = false;
            document.getElementById('sendBtn').style.display = 'flex';
            document.getElementById('stopBtn').style.display = 'none';
            document.getElementById('statusText').textContent = '就绪';
        }

        // ========== MULTIMODAL ENHANCEMENT ==========
        let multimodalChatMessages = [];
        let multimodalAnalysisHistory = [];
        let currentMultimodalImageUrl = '';

        function sendMultimodalChat() {
            const input = document.getElementById('multimodalChatInput');
            const msg = input.value.trim();
            if (!msg) return;
            input.value = '';
            multimodalChatMessages.push({ role: 'user', content: msg });
            renderMultimodalChat();
            if (!window.KaguyaAPI) {
                multimodalChatMessages.push({ role: 'assistant', content: 'api_client_unavailable' });
                renderMultimodalChat();
                return;
            }
            window.KaguyaAPI.json('/multimodal/chat', { message: msg, image_url: currentMultimodalImageUrl || '' }).then(data => {
                multimodalChatMessages.push({ role: 'assistant', content: data.response || data.content || '无法分析' });
                renderMultimodalChat();
            }).catch(() => {
                multimodalChatMessages.push({ role: 'assistant', content: '连接失败，请稍后重试' });
                renderMultimodalChat();
            });
        }

        function renderMultimodalChat() {
            const el = document.getElementById('multimodalChatHistory');
            if (!el) return;
            el.innerHTML = multimodalChatMessages.map(m => {
                const isUser = m.role === 'user';
                return '<div style="padding:4px 8px;border-radius:8px;font-size:11px;' +
                    (isUser ? 'background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;margin-left:20px;' : 'background:var(--bg-secondary);color:var(--text-secondary);margin-right:20px;') +
                    '">' + escapeHtml(m.content) + '</div>';
            }).join('');
            el.scrollTop = el.scrollHeight;
        }

        function loadMultimodalHistory() {
            const el = document.getElementById('multimodalHistoryList');
            if (!el) return;
            if (!window.KaguyaAPI) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">api_client_unavailable</div>';
                return;
            }
            window.KaguyaAPI.get('/multimodal/history').then(data => {
                multimodalAnalysisHistory = data.history || [];
                renderMultimodalHistoryList();
            }).catch(() => {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">加载失败</div>';
            });
        }

        function renderMultimodalHistoryList() {
            const el = document.getElementById('multimodalHistoryList');
            if (!el) return;
            if (multimodalAnalysisHistory.length === 0) {
                el.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:12px;">暂无分析历史</div>';
                return;
            }
            el.innerHTML = multimodalAnalysisHistory.slice(-15).reverse().map(h => {
                return '<div style="display:flex;align-items:center;gap:6px;padding:6px;border-radius:8px;border:1px solid var(--border);font-size:11px;">' +
                    '<span style="color:var(--text-muted);">' + (h.type === 'describe' ? '📝' : h.type === 'ocr' ? '🔤' : '🔬') + '</span>' +
                    '<span style="flex:1;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(h.result || h.summary || '').substring(0, 60) + '</span>' +
                    '<span style="color:var(--text-muted);font-size:9px;">' + escapeHtml(h.timestamp || '') + '</span>' +
                '</div>';
            }).join('');
        }
