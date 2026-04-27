/**
 * 辉夜AI - 系统监控面板
 * 功能: 实时性能监控、资源使用追踪、告警展示
 */

class MonitoringDashboard {
    constructor() {
        this.isOpen = false;
        this.refreshInterval = null;
        this.charts = {};
        this.init();
    }

    init() {
        this._createUI();
        this._addStyles();
        console.log('[监控面板] 初始化完成');
    }

    _createUI() {
        const container = document.createElement('div');
        container.id = 'monitoring-dashboard';
        container.className = 'monitoring-dashboard';
        container.style.display = 'none';
        
        container.innerHTML = `
            <div class="monitor-header">
                <h2>📊 系统监控面板</h2>
                <div class="monitor-actions">
                    <button class="monitor-btn" onclick="monitoringDashboard.refresh()">🔄 刷新</button>
                    <button class="monitor-btn close" onclick="monitoringDashboard.close()">&times;</button>
                </div>
            </div>
            <div class="monitor-content">
                <!-- 概览卡片 -->
                <div class="monitor-overview">
                    <div class="metric-card">
                        <div class="metric-icon">⚡</div>
                        <div class="metric-info">
                            <span class="metric-value" id="rpm-value">-</span>
                            <span class="metric-label">请求/分钟</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">❌</div>
                        <div class="metric-info">
                            <span class="metric-value" id="error-rate-value">-</span>
                            <span class="metric-label">错误率</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">⏱️</div>
                        <div class="metric-info">
                            <span class="metric-value" id="avg-response-value">-</span>
                            <span class="metric-label">平均响应</span>
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-icon">👥</div>
                        <div class="metric-info">
                            <span class="metric-value" id="active-users-value">-</span>
                            <span class="metric-label">活跃用户</span>
                        </div>
                    </div>
                </div>

                <!-- 系统资源 -->
                <div class="monitor-section">
                    <h3>💻 系统资源</h3>
                    <div class="resource-grid">
                        <div class="resource-item">
                            <span class="resource-label">CPU</span>
                            <div class="progress-bar">
                                <div class="progress-fill" id="cpu-progress"></div>
                            </div>
                            <span class="resource-value" id="cpu-value">-</span>
                        </div>
                        <div class="resource-item">
                            <span class="resource-label">内存</span>
                            <div class="progress-bar">
                                <div class="progress-fill" id="memory-progress"></div>
                            </div>
                            <span class="resource-value" id="memory-value">-</span>
                        </div>
                        <div class="resource-item">
                            <span class="resource-label">磁盘</span>
                            <div class="progress-bar">
                                <div class="progress-fill" id="disk-progress"></div>
                            </div>
                            <span class="resource-value" id="disk-value">-</span>
                        </div>
                    </div>
                </div>

                <!-- 端点性能 -->
                <div class="monitor-section">
                    <h3>🔌 API端点性能</h3>
                    <div class="endpoint-table-container">
                        <table class="endpoint-table">
                            <thead>
                                <tr>
                                    <th>端点</th>
                                    <th>请求数</th>
                                    <th>平均响应</th>
                                    <th>错误数</th>
                                    <th>状态</th>
                                </tr>
                            </thead>
                            <tbody id="endpoint-tbody">
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 告警信息 -->
                <div class="monitor-section">
                    <h3>🚨 最近告警</h3>
                    <div class="alerts-container" id="alerts-container">
                        <div class="alert-item info">暂无告警信息</div>
                    </div>
                </div>

                <!-- 缓存统计 -->
                <div class="monitor-section">
                    <h3>💾 缓存统计</h3>
                    <div class="cache-stats">
                        <div class="cache-section">
                            <h4>L1 内存缓存</h4>
                            <div class="cache-metrics" id="l1-cache-stats">
                                <span>加载中...</span>
                            </div>
                        </div>
                        <div class="cache-section">
                            <h4>L2 磁盘缓存</h4>
                            <div class="cache-metrics" id="l2-cache-stats">
                                <span>加载中...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        this.panel = container;
    }

    _addStyles() {
        if (document.getElementById('monitoring-dashboard-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'monitoring-dashboard-styles';
        styles.textContent = `
            .monitoring-dashboard {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 90%;
                max-width: 1000px;
                height: 85%;
                max-height: 800px;
                background: linear-gradient(135deg, #1a1f2e 0%, #2d3748 100%);
                border-radius: 16px;
                box-shadow: 0 25px 50px rgba(0,0,0,0.5);
                display: flex;
                flex-direction: column;
                z-index: 10001;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }

            .monitor-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px 24px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .monitor-header h2 {
                margin: 0;
                font-size: 1.5rem;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }

            .monitor-actions {
                display: flex;
                gap: 12px;
            }

            .monitor-btn {
                padding: 8px 16px;
                background: rgba(102, 126, 234, 0.2);
                border: 1px solid rgba(102, 126, 234, 0.3);
                border-radius: 8px;
                color: #e2e8f0;
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
            }

            .monitor-btn:hover {
                background: rgba(102, 126, 234, 0.3);
            }

            .monitor-btn.close {
                padding: 8px 12px;
                font-size: 20px;
                line-height: 1;
            }

            .monitor-content {
                flex: 1;
                overflow-y: auto;
                padding: 24px;
            }

            .monitor-overview {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }

            .metric-card {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 20px;
                background: rgba(255,255,255,0.05);
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.1);
            }

            .metric-icon {
                font-size: 32px;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(102, 126, 234, 0.1);
                border-radius: 12px;
            }

            .metric-info {
                display: flex;
                flex-direction: column;
            }

            .metric-value {
                font-size: 28px;
                font-weight: 700;
                color: #667eea;
            }

            .metric-label {
                font-size: 14px;
                color: #a0aec0;
                margin-top: 4px;
            }

            .monitor-section {
                margin-bottom: 24px;
            }

            .monitor-section h3 {
                margin: 0 0 16px 0;
                font-size: 18px;
                color: #e2e8f0;
                padding-bottom: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .resource-grid {
                display: grid;
                gap: 16px;
            }

            .resource-item {
                display: flex;
                align-items: center;
                gap: 16px;
                padding: 16px;
                background: rgba(255,255,255,0.03);
                border-radius: 8px;
            }

            .resource-label {
                width: 60px;
                font-size: 14px;
                color: #a0aec0;
            }

            .progress-bar {
                flex: 1;
                height: 8px;
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                border-radius: 4px;
                transition: width 0.3s ease;
            }

            .progress-fill.warning {
                background: linear-gradient(90deg, #f6ad55 0%, #ed8936 100%);
            }

            .progress-fill.danger {
                background: linear-gradient(90deg, #fc8181 0%, #f56565 100%);
            }

            .resource-value {
                width: 60px;
                text-align: right;
                font-size: 14px;
                color: #e2e8f0;
            }

            .endpoint-table-container {
                overflow-x: auto;
            }

            .endpoint-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
            }

            .endpoint-table th,
            .endpoint-table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }

            .endpoint-table th {
                color: #a0aec0;
                font-weight: 500;
                background: rgba(255,255,255,0.03);
            }

            .endpoint-table td {
                color: #e2e8f0;
            }

            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
            }

            .status-badge.success {
                background: rgba(72, 187, 120, 0.2);
                color: #68d391;
            }

            .status-badge.warning {
                background: rgba(246, 173, 85, 0.2);
                color: #f6ad55;
            }

            .status-badge.danger {
                background: rgba(252, 129, 129, 0.2);
                color: #fc8181;
            }

            .alerts-container {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .alert-item {
                padding: 12px 16px;
                border-radius: 8px;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .alert-item.info {
                background: rgba(102, 126, 234, 0.1);
                border-left: 3px solid #667eea;
            }

            .alert-item.warning {
                background: rgba(246, 173, 85, 0.1);
                border-left: 3px solid #f6ad55;
            }

            .alert-item.danger {
                background: rgba(252, 129, 129, 0.1);
                border-left: 3px solid #fc8181;
            }

            .alert-time {
                font-size: 12px;
                color: #a0aec0;
                margin-left: auto;
            }

            .cache-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 16px;
            }

            .cache-section {
                padding: 16px;
                background: rgba(255,255,255,0.03);
                border-radius: 8px;
            }

            .cache-section h4 {
                margin: 0 0 12px 0;
                font-size: 14px;
                color: #a0aec0;
            }

            .cache-metrics {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }

            .cache-metric {
                display: flex;
                justify-content: space-between;
                font-size: 13px;
            }

            .cache-metric-label {
                color: #a0aec0;
            }

            .cache-metric-value {
                color: #e2e8f0;
                font-weight: 500;
            }
        `;
        document.head.appendChild(styles);
    }

    open() {
        this.panel.style.display = 'flex';
        this.isOpen = true;
        this.refresh();
        this.startAutoRefresh();
    }

    close() {
        this.panel.style.display = 'none';
        this.isOpen = false;
        this.stopAutoRefresh();
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => this.refresh(), 5000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refresh() {
        try {
            // 获取监控数据
            const response = await fetch('/api/monitoring/dashboard');
            const data = await response.json();

            if (data.success) {
                this._updateOverview(data.data);
                this._updateSystemResources(data.data.system_status);
                this._updateEndpoints(data.data.endpoint_summary);
                this._updateAlerts(data.data.alerts);
                this._updateCacheStats(data.data.cache_stats);
            }
        } catch (e) {
            console.error('刷新监控数据失败:', e);
        }
    }

    _updateOverview(data) {
        document.getElementById('rpm-value').textContent = data.rpm?.toFixed(1) || '-';
        document.getElementById('error-rate-value').textContent = (data.error_rate?.toFixed(2) || '-') + '%';
        document.getElementById('avg-response-value').textContent = '-';
        document.getElementById('active-users-value').textContent = '-';
    }

    _updateSystemResources(status) {
        if (!status) return;

        // CPU
        const cpuPercent = status.cpu_percent || 0;
        document.getElementById('cpu-value').textContent = cpuPercent.toFixed(1) + '%';
        const cpuProgress = document.getElementById('cpu-progress');
        cpuProgress.style.width = cpuPercent + '%';
        cpuProgress.className = 'progress-fill' + (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');

        // 内存
        const memPercent = status.memory_percent || 0;
        document.getElementById('memory-value').textContent = memPercent.toFixed(1) + '%';
        const memProgress = document.getElementById('memory-progress');
        memProgress.style.width = memPercent + '%';
        memProgress.className = 'progress-fill' + (memPercent > 85 ? ' danger' : memPercent > 70 ? ' warning' : '');

        // 磁盘
        const diskPercent = status.disk_usage_percent || 0;
        document.getElementById('disk-value').textContent = diskPercent.toFixed(1) + '%';
        const diskProgress = document.getElementById('disk-progress');
        diskProgress.style.width = diskPercent + '%';
        diskProgress.className = 'progress-fill' + (diskPercent > 90 ? ' danger' : diskPercent > 75 ? ' warning' : '');
    }

    _updateEndpoints(endpoints) {
        const tbody = document.getElementById('endpoint-tbody');
        if (!endpoints || Object.keys(endpoints).length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#a0aec0;">暂无数据</td></tr>';
            return;
        }

        tbody.innerHTML = Object.entries(endpoints).map(([endpoint, data]) => {
            const statusClass = data.error_count > 0 ? 'warning' : 'success';
            const statusText = data.error_count > 0 ? '警告' : '正常';
            
            return `
                <tr>
                    <td>${endpoint}</td>
                    <td>${data.count}</td>
                    <td>${data.avg_response_time.toFixed(2)}ms</td>
                    <td>${data.error_count}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                </tr>
            `;
        }).join('');
    }

    _updateAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        if (!alerts || alerts.length === 0) {
            container.innerHTML = '<div class="alert-item info">暂无告警信息</div>';
            return;
        }

        container.innerHTML = alerts.map(alert => {
            const typeClass = alert.type.includes('high') ? 'danger' : 'warning';
            const time = new Date(alert.timestamp * 1000).toLocaleTimeString();
            
            return `
                <div class="alert-item ${typeClass}">
                    <span>${alert.message}</span>
                    <span class="alert-time">${time}</span>
                </div>
            `;
        }).join('');
    }

    _updateCacheStats(stats) {
        if (!stats) return;

        // L1缓存
        const l1Stats = stats.l1_memory || {};
        document.getElementById('l1-cache-stats').innerHTML = `
            <div class="cache-metric">
                <span class="cache-metric-label">条目数:</span>
                <span class="cache-metric-value">${l1Stats.size || 0} / ${l1Stats.max_size || 0}</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">内存使用:</span>
                <span class="cache-metric-value">${(l1Stats.memory_usage_mb || 0).toFixed(2)} MB</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">命中率:</span>
                <span class="cache-metric-value">${(l1Stats.hit_rate || 0).toFixed(2)}%</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">淘汰数:</span>
                <span class="cache-metric-value">${l1Stats.evictions || 0}</span>
            </div>
        `;

        // L2缓存
        const l2Stats = stats.l2_disk || {};
        document.getElementById('l2-cache-stats').innerHTML = `
            <div class="cache-metric">
                <span class="cache-metric-label">磁盘使用:</span>
                <span class="cache-metric-value">${(l2Stats.size_mb || 0).toFixed(2)} MB</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">最大容量:</span>
                <span class="cache-metric-value">${l2Stats.max_size_mb || 0} MB</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">命中率:</span>
                <span class="cache-metric-value">${(l2Stats.hit_rate || 0).toFixed(2)}%</span>
            </div>
            <div class="cache-metric">
                <span class="cache-metric-label">请求数:</span>
                <span class="cache-metric-value">${(l2Stats.hits || 0) + (l2Stats.misses || 0)}</span>
            </div>
        `;
    }
}

// 初始化全局实例
let monitoringDashboard;

document.addEventListener('DOMContentLoaded', () => {
    monitoringDashboard = new MonitoringDashboard();
});

// 添加打开按钮
function addMonitoringButton() {
    const toolbar = document.querySelector('.toolbar, .header-actions, nav');
    if (toolbar && !document.getElementById('monitor-open-btn')) {
        const btn = document.createElement('button');
        btn.id = 'monitor-open-btn';
        btn.className = 'monitor-open-btn';
        btn.innerHTML = '📊 监控';
        btn.onclick = () => monitoringDashboard.open();
        toolbar.appendChild(btn);

        const style = document.createElement('style');
        style.textContent = `
            .monitor-open-btn {
                padding: 8px 16px;
                background: rgba(72, 187, 120, 0.2);
                border: 1px solid rgba(72, 187, 120, 0.3);
                border-radius: 8px;
                color: #68d391;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
                margin-left: 8px;
            }
            .monitor-open-btn:hover {
                background: rgba(72, 187, 120, 0.3);
            }
        `;
        document.head.appendChild(style);
    }
}

setTimeout(addMonitoringButton, 2500);
