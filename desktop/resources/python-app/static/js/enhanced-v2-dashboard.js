/**
 * 辉夜AI平台 - 增强功能V2仪表板
 * 前端UI组件
 */

class EnhancedV2Dashboard {
    constructor() {
        this.apiBaseUrl = '/api/v2';
        this.refreshInterval = null;
        this.initialized = false;
    }

    async initialize() {
        console.log('🚀 初始化增强功能V2仪表板...');
        
        // 检查后端状态
        const status = await this.checkStatus();
        if (status.status === 'active') {
            this.initialized = true;
            this.renderDashboard();
            this.startAutoRefresh();
            console.log('✅ 增强功能V2仪表板初始化完成');
        } else {
            console.warn('⚠️ 增强功能V2未激活:', status.message);
            this.renderInactiveState();
        }
    }

    async checkStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/enhanced/status`);
            return await response.json();
        } catch (error) {
            return { status: 'error', message: error.message };
        }
    }

    renderDashboard() {
        const container = document.getElementById('enhanced-v2-container');
        if (!container) return;

        container.innerHTML = `
            <div class="enhanced-v2-dashboard">
                <div class="dashboard-header">
                    <h2>🚀 增强功能V2 控制面板</h2>
                    <span class="status-badge active">运行中</span>
                </div>
                
                <div class="dashboard-grid">
                    <!-- Agentic Workflow 卡片 -->
                    <div class="feature-card">
                        <div class="card-header">
                            <span class="icon">🔄</span>
                            <h3>Agentic Workflow</h3>
                        </div>
                        <div class="card-body">
                            <div class="feature-list">
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>记忆增强系统</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>工具使用规划</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>自我反思系统</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>多Agent编排</span>
                                </div>
                            </div>
                            <button class="action-btn" onclick="enhancedV2.createWorkflow()">
                                创建工作流
                            </button>
                        </div>
                    </div>

                    <!-- 模型服务 卡片 -->
                    <div class="feature-card">
                        <div class="card-header">
                            <span class="icon">⚡</span>
                            <h3>模型服务优化</h3>
                        </div>
                        <div class="card-body">
                            <div class="stats-grid">
                                <div class="stat-item">
                                    <span class="stat-value" id="model-replicas">-</span>
                                    <span class="stat-label">副本数</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="model-throughput">-</span>
                                    <span class="stat-label">吞吐量</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="model-latency">-</span>
                                    <span class="stat-label">延迟(ms)</span>
                                </div>
                            </div>
                            <div class="feature-list">
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>分布式推理</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>自动扩缩容</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>模型热切换</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 多模态 卡片 -->
                    <div class="feature-card">
                        <div class="card-header">
                            <span class="icon">🖼️</span>
                            <h3>多模态处理</h3>
                        </div>
                        <div class="card-body">
                            <div class="feature-list">
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>3D点云支持</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>时间序列处理</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>图数据支持</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>5种融合策略</span>
                                </div>
                            </div>
                            <button class="action-btn" onclick="enhancedV2.openMultimodalChat()">
                                多模态对话
                            </button>
                        </div>
                    </div>

                    <!-- 协作框架 卡片 -->
                    <div class="feature-card">
                        <div class="card-header">
                            <span class="icon">👥</span>
                            <h3>实时协作</h3>
                        </div>
                        <div class="card-body">
                            <div class="feature-list">
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>智能冲突解决</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>意图预测</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>CRDT文档同步</span>
                                </div>
                            </div>
                            <button class="action-btn" onclick="enhancedV2.createCollaborationSpace()">
                                创建协作空间
                            </button>
                        </div>
                    </div>

                    <!-- AI治理 卡片 -->
                    <div class="feature-card">
                        <div class="card-header">
                            <span class="icon">🛡️</span>
                            <h3>AI治理与安全</h3>
                        </div>
                        <div class="card-body">
                            <div class="feature-list">
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>联邦学习隐私</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>模型水印</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>对抗攻击检测</span>
                                </div>
                                <div class="feature-item">
                                    <span class="check">✅</span>
                                    <span>内容安全审查</span>
                                </div>
                            </div>
                            <button class="action-btn" onclick="enhancedV2.checkGovernance()">
                                治理检查
                            </button>
                        </div>
                    </div>

                    <!-- 系统状态 卡片 -->
                    <div class="feature-card full-width">
                        <div class="card-header">
                            <span class="icon">📊</span>
                            <h3>系统状态监控</h3>
                        </div>
                        <div class="card-body">
                            <pre id="system-status-json" class="status-json">加载中...</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.addStyles();
    }

    renderInactiveState() {
        const container = document.getElementById('enhanced-v2-container');
        if (!container) return;

        container.innerHTML = `
            <div class="enhanced-v2-inactive">
                <div class="inactive-icon">⚠️</div>
                <h3>增强功能V2未激活</h3>
                <p>请检查后端服务是否正常运行</p>
                <button class="retry-btn" onclick="enhancedV2.initialize()">重新加载</button>
            </div>
        `;
    }

    addStyles() {
        if (document.getElementById('enhanced-v2-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'enhanced-v2-styles';
        styles.textContent = `
            .enhanced-v2-dashboard {
                padding: 20px;
                background: #f8fafc;
                border-radius: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }

            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
                padding-bottom: 16px;
                border-bottom: 2px solid #e2e8f0;
            }

            .dashboard-header h2 {
                margin: 0;
                color: #1e293b;
                font-size: 24px;
            }

            .status-badge {
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }

            .status-badge.active {
                background: #dcfce7;
                color: #166534;
            }

            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }

            .feature-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                overflow: hidden;
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .feature-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }

            .feature-card.full-width {
                grid-column: 1 / -1;
            }

            .card-header {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 16px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }

            .card-header .icon {
                font-size: 24px;
            }

            .card-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }

            .card-body {
                padding: 20px;
            }

            .feature-list {
                margin-bottom: 16px;
            }

            .feature-item {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 0;
                color: #475569;
                font-size: 14px;
            }

            .feature-item .check {
                color: #22c55e;
            }

            .stats-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
                margin-bottom: 16px;
                padding: 12px;
                background: #f1f5f9;
                border-radius: 8px;
            }

            .stat-item {
                text-align: center;
            }

            .stat-value {
                display: block;
                font-size: 24px;
                font-weight: 700;
                color: #3b82f6;
            }

            .stat-label {
                font-size: 12px;
                color: #64748b;
            }

            .action-btn {
                width: 100%;
                padding: 10px 16px;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: background 0.2s;
            }

            .action-btn:hover {
                background: #2563eb;
            }

            .status-json {
                background: #1e293b;
                color: #e2e8f0;
                padding: 16px;
                border-radius: 8px;
                font-size: 12px;
                overflow-x: auto;
                max-height: 300px;
                overflow-y: auto;
            }

            .enhanced-v2-inactive {
                text-align: center;
                padding: 60px 20px;
                background: #fef3c7;
                border-radius: 12px;
            }

            .inactive-icon {
                font-size: 48px;
                margin-bottom: 16px;
            }

            .retry-btn {
                margin-top: 16px;
                padding: 10px 24px;
                background: #f59e0b;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }
        `;
        document.head.appendChild(styles);
    }

    async startAutoRefresh() {
        // 立即更新一次
        await this.updateStats();
        
        // 每5秒更新一次
        this.refreshInterval = setInterval(() => {
            this.updateStats();
        }, 5000);
    }

    async updateStats() {
        try {
            const status = await this.checkStatus();
            
            if (status.status === 'active' && status.components) {
                // 更新模型服务统计
                if (status.components.model_serving) {
                    const ms = status.components.model_serving;
                    document.getElementById('model-replicas').textContent = 
                        ms.scheduler_stats?.running_batch_size || '-';
                    document.getElementById('model-throughput').textContent = 
                        ms.throughput_tokens_per_sec?.toFixed(1) || '-';
                    document.getElementById('model-latency').textContent = 
                        ms.average_latency_ms?.toFixed(0) || '-';
                }

                // 更新系统状态JSON
                const statusJson = document.getElementById('system-status-json');
                if (statusJson) {
                    statusJson.textContent = JSON.stringify(status, null, 2);
                }
            }
        } catch (error) {
            console.error('更新统计失败:', error);
        }
    }

    // ==================== 操作方法 ====================

    async createWorkflow() {
        const type = prompt('选择工作流类型 (react/plan_execute/approval):', 'react');
        if (!type) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/workflow/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: type,
                    config: { name: `Workflow_${Date.now()}` }
                })
            });
            const result = await response.json();
            alert(`工作流创建成功!\nID: ${result.workflow_id}`);
        } catch (error) {
            alert(`创建失败: ${error.message}`);
        }
    }

    openMultimodalChat() {
        alert('多模态对话功能开发中...\n支持: 文本、图像、3D点云、时间序列');
    }

    async createCollaborationSpace() {
        const name = prompt('输入协作空间名称:', '新项目');
        if (!name) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/collaboration/space/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    type: 'document',
                    creator_id: 'user_' + Date.now()
                })
            });
            const result = await response.json();
            alert(`协作空间创建成功!\nID: ${result.space_id}`);
        } catch (error) {
            alert(`创建失败: ${error.message}`);
        }
    }

    async checkGovernance() {
        const content = prompt('输入要检查的内容:', '测试内容');
        if (!content) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/governance/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: content,
                    type: 'input'
                })
            });
            const result = await response.json();
            alert(`治理检查结果:\n${JSON.stringify(result, null, 2)}`);
        } catch (error) {
            alert(`检查失败: ${error.message}`);
        }
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// 全局实例
const enhancedV2 = new EnhancedV2Dashboard();

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    enhancedV2.initialize();
});
