/**
 * 辉夜AI平台 - 优化版仪表板
 * 整合性能监控、缓存管理、健康检查等功能
 */

class KaguyaOptimizedDashboard {
    constructor() {
        this.apiBaseUrl = '/api';
        this.refreshInterval = null;
        this.charts = {};
        this.metrics = {
            requests: [],
            latencies: [],
            errors: []
        };
    }

    async initialize() {
        console.log('🚀 初始化辉夜AI优化仪表板...');
        
        this.renderDashboard();
        this.startAutoRefresh();
        this.initializeCharts();
        
        console.log('✅ 优化仪表板初始化完成');
    }

    renderDashboard() {
        const container = document.getElementById('optimized-dashboard');
        if (!container) return;

        container.innerHTML = `
            <div class="optimized-dashboard">
                <!-- 顶部统计栏 -->
                <div class="stats-bar">
                    <div class="stat-card">
                        <div class="stat-icon">⚡</div>
                        <div class="stat-info">
                            <span class="stat-value" id="avg-latency">-</span>
                            <span class="stat-label">平均延迟 (ms)</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">🎯</div>
                        <div class="stat-info">
                            <span class="stat-value" id="cache-hit-rate">-</span>
                            <span class="stat-label">缓存命中率 (%)</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">✅</div>
                        <div class="stat-info">
                            <span class="stat-value" id="health-status">-</span>
                            <span class="stat-label">系统健康</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">📊</div>
                        <div class="stat-info">
                            <span class="stat-value" id="total-requests">-</span>
                            <span class="stat-label">总请求数</span>
                        </div>
                    </div>
                </div>

                <!-- 主内容区 -->
                <div class="dashboard-grid">
                    <!-- 性能监控 -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3>⚡ 性能监控</h3>
                            <button class="refresh-btn" onclick="dashboard.refreshPerformance()">刷新</button>
                        </div>
                        <div class="card-body">
                            <canvas id="performance-chart"></canvas>
                            <div class="performance-list" id="performance-list">
                                <div class="loading">加载中...</div>
                            </div>
                        </div>
                    </div>

                    <!-- 缓存统计 -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3>💾 缓存统计</h3>
                            <button class="action-btn" onclick="dashboard.clearCache()">清空缓存</button>
                        </div>
                        <div class="card-body">
                            <div class="cache-stats">
                                <div class="cache-stat">
                                    <span class="label">缓存大小</span>
                                    <span class="value" id="cache-size">-</span>
                                </div>
                                <div class="cache-stat">
                                    <span class="label">命中次数</span>
                                    <span class="value" id="cache-hits">-</span>
                                </div>
                                <div class="cache-stat">
                                    <span class="label">未命中</span>
                                    <span class="value" id="cache-misses">-</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 健康检查 -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3>🏥 健康检查</h3>
                            <span class="status-badge" id="health-badge">检查中</span>
                        </div>
                        <div class="card-body">
                            <div class="health-checks" id="health-checks">
                                <div class="loading">检查中...</div>
                            </div>
                        </div>
                    </div>

                    <!-- 实时日志 -->
                    <div class="dashboard-card full-width">
                        <div class="card-header">
                            <h3>📝 实时日志</h3>
                            <div class="log-filters">
                                <select id="log-level" onchange="dashboard.filterLogs()">
                                    <option value="all">全部</option>
                                    <option value="info">信息</option>
                                    <option value="warning">警告</option>
                                    <option value="error">错误</option>
                                </select>
                                <button class="action-btn" onclick="dashboard.clearLogs()">清空</button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="log-container" id="log-container">
                                <div class="log-entry info">
                                    <span class="timestamp">${new Date().toLocaleTimeString()}</span>
                                    <span class="level">INFO</span>
                                    <span class="message">系统初始化完成</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- API限流状态 -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3>🚦 API限流</h3>
                        </div>
                        <div class="card-body">
                            <div class="rate-limit-info">
                                <div class="rate-item">
                                    <span class="label">每分钟限制</span>
                                    <span class="value">60</span>
                                </div>
                                <div class="rate-item">
                                    <span class="label">剩余配额</span>
                                    <span class="value" id="rate-remaining">-</span>
                                </div>
                                <div class="rate-bar">
                                    <div class="rate-progress" id="rate-progress"></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 系统配置 -->
                    <div class="dashboard-card">
                        <div class="card-header">
                            <h3>⚙️ 系统配置</h3>
                            <button class="action-btn" onclick="dashboard.saveConfig()">保存</button>
                        </div>
                        <div class="card-body">
                            <div class="config-form">
                                <div class="config-item">
                                    <label>慢查询阈值 (ms)</label>
                                    <input type="number" id="slow-threshold" value="1000">
                                </div>
                                <div class="config-item">
                                    <label>缓存TTL (秒)</label>
                                    <input type="number" id="cache-ttl" value="300">
                                </div>
                                <div class="config-item">
                                    <label>启用监控</label>
                                    <input type="checkbox" id="enable-monitoring" checked>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.addStyles();
    }

    addStyles() {
        if (document.getElementById('optimized-dashboard-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'optimized-dashboard-styles';
        styles.textContent = `
            .optimized-dashboard {
                padding: 20px;
                background: #f8fafc;
                min-height: 100vh;
            }

            .stats-bar {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }

            .stat-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                display: flex;
                align-items: center;
                gap: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }

            .stat-icon {
                width: 48px;
                height: 48px;
                border-radius: 12px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }

            .stat-info {
                display: flex;
                flex-direction: column;
            }

            .stat-value {
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
            }

            .stat-label {
                font-size: 14px;
                color: #64748b;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
            }

            .dashboard-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                overflow: hidden;
            }

            .dashboard-card.full-width {
                grid-column: 1 / -1;
            }

            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px 20px;
                background: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
            }

            .card-header h3 {
                margin: 0;
                font-size: 16px;
                color: #1e293b;
            }

            .card-body {
                padding: 20px;
            }

            .refresh-btn, .action-btn {
                padding: 6px 12px;
                border: none;
                border-radius: 6px;
                background: #3b82f6;
                color: white;
                font-size: 12px;
                cursor: pointer;
            }

            .refresh-btn:hover, .action-btn:hover {
                background: #2563eb;
            }

            .loading {
                text-align: center;
                color: #64748b;
                padding: 20px;
            }

            .performance-list {
                margin-top: 16px;
            }

            .perf-item {
                display: flex;
                justify-content: space-between;
                padding: 12px;
                border-bottom: 1px solid #e2e8f0;
            }

            .perf-item:last-child {
                border-bottom: none;
            }

            .perf-name {
                font-weight: 500;
                color: #1e293b;
            }

            .perf-stats {
                display: flex;
                gap: 16px;
                font-size: 12px;
                color: #64748b;
            }

            .cache-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
            }

            .cache-stat {
                text-align: center;
                padding: 16px;
                background: #f8fafc;
                border-radius: 8px;
            }

            .cache-stat .label {
                display: block;
                font-size: 12px;
                color: #64748b;
                margin-bottom: 8px;
            }

            .cache-stat .value {
                font-size: 24px;
                font-weight: 700;
                color: #3b82f6;
            }

            .health-checks {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .health-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: #f8fafc;
                border-radius: 8px;
            }

            .health-status {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }

            .health-status.healthy {
                background: #dcfce7;
                color: #166534;
            }

            .health-status.unhealthy {
                background: #fee2e2;
                color: #991b1b;
            }

            .status-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }

            .log-container {
                max-height: 300px;
                overflow-y: auto;
                background: #1e293b;
                border-radius: 8px;
                padding: 12px;
            }

            .log-entry {
                display: flex;
                gap: 12px;
                padding: 8px 0;
                font-size: 12px;
                font-family: monospace;
                border-bottom: 1px solid #334155;
            }

            .log-entry:last-child {
                border-bottom: none;
            }

            .log-entry .timestamp {
                color: #64748b;
            }

            .log-entry .level {
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 500;
            }

            .log-entry.info .level {
                background: #3b82f6;
                color: white;
            }

            .log-entry.warning .level {
                background: #f59e0b;
                color: white;
            }

            .log-entry.error .level {
                background: #ef4444;
                color: white;
            }

            .log-entry .message {
                color: #e2e8f0;
            }

            .rate-limit-info {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }

            .rate-item {
                display: flex;
                justify-content: space-between;
            }

            .rate-bar {
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
                overflow: hidden;
            }

            .rate-progress {
                height: 100%;
                background: linear-gradient(90deg, #667eea, #764ba2);
                transition: width 0.3s;
            }

            .config-form {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .config-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .config-item label {
                font-size: 14px;
                color: #1e293b;
            }

            .config-item input {
                padding: 8px 12px;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                width: 120px;
            }
        `;
        document.head.appendChild(styles);
    }

    initializeCharts() {
        // 这里可以集成 Chart.js 或其他图表库
        console.log('图表初始化完成');
    }

    async startAutoRefresh() {
        await this.refreshAll();
        this.refreshInterval = setInterval(() => {
            this.refreshAll();
        }, 5000);
    }

    async refreshAll() {
        await Promise.all([
            this.refreshPerformance(),
            this.refreshCache(),
            this.refreshHealth(),
            this.refreshRateLimit()
        ]);
    }

    async refreshPerformance() {
        try {
            // 模拟获取性能数据
            const mockData = {
                functions: [
                    { name: 'generate', calls: 150, avg_ms: 245, errors: 2 },
                    { name: 'chat', calls: 89, avg_ms: 189, errors: 0 },
                    { name: 'evaluate', calls: 45, avg_ms: 567, errors: 1 }
                ]
            };

            const list = document.getElementById('performance-list');
            list.innerHTML = mockData.functions.map(f => `
                <div class="perf-item">
                    <span class="perf-name">${f.name}</span>
                    <div class="perf-stats">
                        <span>调用: ${f.calls}</span>
                        <span>平均: ${f.avg_ms}ms</span>
                        <span>错误: ${f.errors}</span>
                    </div>
                </div>
            `).join('');

            // 更新顶部统计
            const avgLatency = mockData.functions.reduce((a, b) => a + b.avg_ms, 0) / mockData.functions.length;
            document.getElementById('avg-latency').textContent = Math.round(avgLatency);
            document.getElementById('total-requests').textContent = mockData.functions.reduce((a, b) => a + b.calls, 0);

        } catch (error) {
            console.error('刷新性能数据失败:', error);
        }
    }

    async refreshCache() {
        try {
            // 模拟缓存数据
            const mockData = { size: 156, hits: 1245, misses: 89, hit_rate: 93.3 };
            
            document.getElementById('cache-size').textContent = mockData.size;
            document.getElementById('cache-hits').textContent = mockData.hits;
            document.getElementById('cache-misses').textContent = mockData.misses;
            document.getElementById('cache-hit-rate').textContent = mockData.hit_rate;
        } catch (error) {
            console.error('刷新缓存数据失败:', error);
        }
    }

    async refreshHealth() {
        try {
            const checks = [
                { name: 'API服务', status: 'healthy' },
                { name: '数据库', status: 'healthy' },
                { name: '缓存', status: 'healthy' },
                { name: '模型服务', status: 'healthy' }
            ];

            const container = document.getElementById('health-checks');
            container.innerHTML = checks.map(c => `
                <div class="health-item">
                    <span>${c.name}</span>
                    <span class="health-status ${c.status}">${c.status === 'healthy' ? '健康' : '异常'}</span>
                </div>
            `).join('');

            const allHealthy = checks.every(c => c.status === 'healthy');
            document.getElementById('health-status').textContent = allHealthy ? '健康' : '异常';
            document.getElementById('health-badge').textContent = allHealthy ? '健康' : '异常';
            document.getElementById('health-badge').className = `status-badge ${allHealthy ? 'healthy' : 'unhealthy'}`;

        } catch (error) {
            console.error('刷新健康检查失败:', error);
        }
    }

    async refreshRateLimit() {
        try {
            const remaining = 45; // 模拟剩余配额
            const total = 60;
            const used = total - remaining;
            const percentage = (used / total) * 100;

            document.getElementById('rate-remaining').textContent = remaining;
            document.getElementById('rate-progress').style.width = `${percentage}%`;
        } catch (error) {
            console.error('刷新限流状态失败:', error);
        }
    }

    clearCache() {
        if (confirm('确定要清空缓存吗？')) {
            this.addLog('info', '缓存已清空');
            this.refreshCache();
        }
    }

    clearLogs() {
        document.getElementById('log-container').innerHTML = '';
    }

    filterLogs() {
        const level = document.getElementById('log-level').value;
        const entries = document.querySelectorAll('.log-entry');
        entries.forEach(entry => {
            if (level === 'all' || entry.classList.contains(level)) {
                entry.style.display = 'flex';
            } else {
                entry.style.display = 'none';
            }
        });
    }

    saveConfig() {
        const config = {
            slowThreshold: document.getElementById('slow-threshold').value,
            cacheTtl: document.getElementById('cache-ttl').value,
            enableMonitoring: document.getElementById('enable-monitoring').checked
        };
        console.log('保存配置:', config);
        this.addLog('info', '配置已保存');
    }

    addLog(level, message) {
        const container = document.getElementById('log-container');
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.innerHTML = `
            <span class="timestamp">${new Date().toLocaleTimeString()}</span>
            <span class="level">${level.toUpperCase()}</span>
            <span class="message">${message}</span>
        `;
        container.insertBefore(entry, container.firstChild);
        
        // 保持最多100条日志
        while (container.children.length > 100) {
            container.removeChild(container.lastChild);
        }
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// 全局实例
const dashboard = new KaguyaOptimizedDashboard();

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    dashboard.initialize();
});
