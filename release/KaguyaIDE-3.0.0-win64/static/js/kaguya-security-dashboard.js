/**
 * 辉夜AI安全控制台
 * Kaguya AI Security Dashboard
 * 
 * 功能:
 * - 实时安全监控
 * - 威胁检测与告警
 * - 访问控制管理
 * - 安全审计日志
 * - WAF规则配置
 */

class KaguyaSecurityDashboard {
    constructor() {
        this.refreshInterval = null;
        this.currentTab = 'overview';
        this.securityStats = {
            threatsBlocked: 0,
            loginAttempts: 0,
            activeSessions: 0,
            apiCalls: 0
        };
        this.init();
    }

    init() {
        this.render();
        this.startRealtimeUpdates();
        this.attachEventListeners();
    }

    render() {
        const container = document.getElementById('security-dashboard');
        if (!container) return;

        container.innerHTML = `
            <div class="security-dashboard">
                <!-- 头部 -->
                <div class="security-header">
                    <div class="security-title">
                        <span class="security-icon">🔒</span>
                        <h2>安全控制台</h2>
                        <span class="security-badge" id="security-status">🟢 系统安全</span>
                    </div>
                    <div class="security-actions">
                        <button class="btn btn-secondary" onclick="securityDashboard.exportReport()">
                            📊 导出报告
                        </button>
                        <button class="btn btn-primary" onclick="securityDashboard.emergencyLockdown()">
                            🚨 紧急锁定
                        </button>
                    </div>
                </div>

                <!-- 安全概览卡片 -->
                <div class="security-overview">
                    <div class="security-card threat-level">
                        <div class="card-icon">🛡️</div>
                        <div class="card-content">
                            <div class="card-label">威胁等级</div>
                            <div class="card-value" id="threat-level">低风险</div>
                            <div class="card-trend" id="threat-trend">↓ 较昨日下降 15%</div>
                        </div>
                    </div>
                    <div class="security-card blocked-attacks">
                        <div class="card-icon">🚫</div>
                        <div class="card-content">
                            <div class="card-label">已拦截攻击</div>
                            <div class="card-value" id="blocked-count">0</div>
                            <div class="card-trend">今日累计</div>
                        </div>
                    </div>
                    <div class="security-card active-sessions">
                        <div class="card-icon">👥</div>
                        <div class="card-content">
                            <div class="card-label">活跃会话</div>
                            <div class="card-value" id="sessions-count">0</div>
                            <div class="card-trend">实时在线用户</div>
                        </div>
                    </div>
                    <div class="security-card security-score">
                        <div class="card-icon">⭐</div>
                        <div class="card-content">
                            <div class="card-label">安全评分</div>
                            <div class="card-value" id="security-score">98</div>
                            <div class="card-trend">优秀</div>
                        </div>
                    </div>
                </div>

                <!-- 标签页导航 -->
                <div class="security-tabs">
                    <button class="tab-btn active" data-tab="overview" onclick="securityDashboard.switchTab('overview')">
                        📊 安全概览
                    </button>
                    <button class="tab-btn" data-tab="threats" onclick="securityDashboard.switchTab('threats')">
                        ⚠️ 威胁检测
                        <span class="badge" id="threat-badge">0</span>
                    </button>
                    <button class="tab-btn" data-tab="access" onclick="securityDashboard.switchTab('access')">
                        🔐 访问控制
                    </button>
                    <button class="tab-btn" data-tab="audit" onclick="securityDashboard.switchTab('audit')">
                        📝 审计日志
                    </button>
                    <button class="tab-btn" data-tab="waf" onclick="securityDashboard.switchTab('waf')">
                        🛡️ WAF配置
                    </button>
                    <button class="tab-btn" data-tab="compliance" onclick="securityDashboard.switchTab('compliance')">
                        ✅ 合规检查
                    </button>
                </div>

                <!-- 标签页内容 -->
                <div class="tab-content active" id="tab-overview">
                    ${this.renderOverviewTab()}
                </div>
                <div class="tab-content" id="tab-threats">
                    ${this.renderThreatsTab()}
                </div>
                <div class="tab-content" id="tab-access">
                    ${this.renderAccessTab()}
                </div>
                <div class="tab-content" id="tab-audit">
                    ${this.renderAuditTab()}
                </div>
                <div class="tab-content" id="tab-waf">
                    ${this.renderWafTab()}
                </div>
                <div class="tab-content" id="tab-compliance">
                    ${this.renderComplianceTab()}
                </div>
            </div>
        `;

        this.initCharts();
    }

    renderOverviewTab() {
        return `
            <div class="overview-grid">
                <!-- 实时攻击图 -->
                <div class="overview-section attack-map">
                    <h3>🌍 实时攻击地图</h3>
                    <div class="attack-map-container" id="attack-map">
                        <div class="map-placeholder">
                            <div class="attack-stats">
                                <div class="stat-item">
                                    <span class="stat-value" id="total-attacks">0</span>
                                    <span class="stat-label">总攻击数</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="unique-ips">0</span>
                                    <span class="stat-label">攻击IP数</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-value" id="top-attack-type">-</span>
                                    <span class="stat-label">主要攻击类型</span>
                                </div>
                            </div>
                            <div class="attack-list" id="recent-attacks">
                                <!-- 动态填充 -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 安全趋势图 -->
                <div class="overview-section security-trends">
                    <h3>📈 安全趋势 (7天)</h3>
                    <div class="chart-container" id="security-trend-chart">
                        <canvas id="trendCanvas"></canvas>
                    </div>
                </div>

                <!-- 攻击类型分布 -->
                <div class="overview-section attack-types">
                    <h3>🎯 攻击类型分布</h3>
                    <div class="chart-container" id="attack-type-chart">
                        <canvas id="typeCanvas"></canvas>
                    </div>
                </div>

                <!-- 最近安全事件 -->
                <div class="overview-section recent-events">
                    <h3>🔔 最近安全事件</h3>
                    <div class="events-list" id="security-events">
                        <div class="event-item info">
                            <span class="event-time">刚刚</span>
                            <span class="event-type">系统启动</span>
                            <span class="event-desc">安全监控系统正常运行</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderThreatsTab() {
        return `
            <div class="threats-container">
                <!-- 威胁统计 -->
                <div class="threat-stats">
                    <div class="threat-stat-card critical">
                        <div class="stat-icon">🔴</div>
                        <div class="stat-info">
                            <div class="stat-number" id="critical-count">0</div>
                            <div class="stat-label">严重威胁</div>
                        </div>
                    </div>
                    <div class="threat-stat-card high">
                        <div class="stat-icon">🟠</div>
                        <div class="stat-info">
                            <div class="stat-number" id="high-count">0</div>
                            <div class="stat-label">高危威胁</div>
                        </div>
                    </div>
                    <div class="threat-stat-card medium">
                        <div class="stat-icon">🟡</div>
                        <div class="stat-info">
                            <div class="stat-number" id="medium-count">0</div>
                            <div class="stat-label">中危威胁</div>
                        </div>
                    </div>
                    <div class="threat-stat-card low">
                        <div class="stat-icon">🟢</div>
                        <div class="stat-info">
                            <div class="stat-number" id="low-count">0</div>
                            <div class="stat-label">低危威胁</div>
                        </div>
                    </div>
                </div>

                <!-- 威胁列表 -->
                <div class="threats-list-section">
                    <div class="section-header">
                        <h3>🚨 威胁列表</h3>
                        <div class="filter-controls">
                            <select id="threat-severity-filter" onchange="securityDashboard.filterThreats()">
                                <option value="all">全部等级</option>
                                <option value="critical">严重</option>
                                <option value="high">高危</option>
                                <option value="medium">中危</option>
                                <option value="low">低危</option>
                            </select>
                            <select id="threat-type-filter" onchange="securityDashboard.filterThreats()">
                                <option value="all">全部类型</option>
                                <option value="sql_injection">SQL注入</option>
                                <option value="xss">XSS攻击</option>
                                <option value="path_traversal">路径遍历</option>
                                <option value="brute_force">暴力破解</option>
                                <option value="rate_limit">速率超限</option>
                            </select>
                            <button class="btn btn-secondary" onclick="securityDashboard.clearAllThreats()">
                                清除全部
                            </button>
                        </div>
                    </div>
                    <div class="threats-table-container">
                        <table class="threats-table">
                            <thead>
                                <tr>
                                    <th>时间</th>
                                    <th>等级</th>
                                    <th>类型</th>
                                    <th>来源IP</th>
                                    <th>目标</th>
                                    <th>详情</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="threats-tbody">
                                <!-- 动态填充 -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 被封禁IP -->
                <div class="blocked-ips-section">
                    <div class="section-header">
                        <h3>🚫 被封禁IP</h3>
                        <button class="btn btn-secondary" onclick="securityDashboard.showBlockIPDialog()">
                            手动封禁IP
                        </button>
                    </div>
                    <div class="blocked-ips-list" id="blocked-ips">
                        <!-- 动态填充 -->
                    </div>
                </div>
            </div>
        `;
    }

    renderAccessTab() {
        return `
            <div class="access-container">
                <!-- 用户管理 -->
                <div class="access-section">
                    <div class="section-header">
                        <h3>👤 用户管理</h3>
                        <button class="btn btn-primary" onclick="securityDashboard.showAddUserDialog()">
                            + 添加用户
                        </button>
                    </div>
                    <div class="users-table-container">
                        <table class="users-table">
                            <thead>
                                <tr>
                                    <th>用户ID</th>
                                    <th>角色</th>
                                    <th>状态</th>
                                    <th>最后登录</th>
                                    <th>MFA</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="users-tbody">
                                <tr>
                                    <td>admin</td>
                                    <td><span class="role-badge super-admin">超级管理员</span></td>
                                    <td><span class="status-badge online">在线</span></td>
                                    <td>2024-01-15 10:30:00</td>
                                    <td>✅ 已启用</td>
                                    <td>
                                        <button class="btn-icon" onclick="securityDashboard.editUser('admin')">✏️</button>
                                        <button class="btn-icon" onclick="securityDashboard.resetPassword('admin')">🔑</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 角色权限 -->
                <div class="access-section">
                    <div class="section-header">
                        <h3>🔑 角色权限</h3>
                        <button class="btn btn-secondary" onclick="securityDashboard.showAddRoleDialog()">
                            + 自定义角色
                        </button>
                    </div>
                    <div class="roles-grid" id="roles-grid">
                        <div class="role-card">
                            <div class="role-header">
                                <span class="role-name">超级管理员</span>
                                <span class="role-badge system">系统</span>
                            </div>
                            <div class="role-permissions">
                                <span class="perm-tag">所有权限</span>
                            </div>
                            <div class="role-users">用户: 1</div>
                        </div>
                        <div class="role-card">
                            <div class="role-header">
                                <span class="role-name">管理员</span>
                                <span class="role-badge system">系统</span>
                            </div>
                            <div class="role-permissions">
                                <span class="perm-tag">用户管理</span>
                                <span class="perm-tag">系统设置</span>
                                <span class="perm-tag">审计查看</span>
                                <span class="perm-tag">+15</span>
                            </div>
                            <div class="role-users">用户: 3</div>
                        </div>
                        <div class="role-card">
                            <div class="role-header">
                                <span class="role-name">普通用户</span>
                                <span class="role-badge system">系统</span>
                            </div>
                            <div class="role-permissions">
                                <span class="perm-tag">对话</span>
                                <span class="perm-tag">模型使用</span>
                                <span class="perm-tag">知识库读取</span>
                            </div>
                            <div class="role-users">用户: 25</div>
                        </div>
                    </div>
                </div>

                <!-- API密钥管理 -->
                <div class="access-section">
                    <div class="section-header">
                        <h3>🔐 API密钥管理</h3>
                        <button class="btn btn-primary" onclick="securityDashboard.createAPIKey()">
                            + 创建密钥
                        </button>
                    </div>
                    <div class="api-keys-list" id="api-keys">
                        <!-- 动态填充 -->
                    </div>
                </div>

                <!-- 活跃会话 -->
                <div class="access-section">
                    <div class="section-header">
                        <h3>💻 活跃会话</h3>
                        <button class="btn btn-danger" onclick="securityDashboard.terminateAllSessions()">
                            终止所有会话
                        </button>
                    </div>
                    <div class="sessions-list" id="active-sessions">
                        <!-- 动态填充 -->
                    </div>
                </div>
            </div>
        `;
    }

    renderAuditTab() {
        return `
            <div class="audit-container">
                <!-- 审计统计 -->
                <div class="audit-stats">
                    <div class="audit-stat">
                        <div class="stat-value" id="audit-total">0</div>
                        <div class="stat-label">总事件数</div>
                    </div>
                    <div class="audit-stat">
                        <div class="stat-value" id="audit-users">0</div>
                        <div class="stat-label">活跃用户</div>
                    </div>
                    <div class="audit-stat">
                        <div class="stat-value" id="audit-errors">0</div>
                        <div class="stat-label">错误事件</div>
                    </div>
                    <div class="audit-stat">
                        <div class="stat-value" id="audit-critical">0</div>
                        <div class="stat-label">关键事件</div>
                    </div>
                </div>

                <!-- 审计日志筛选 -->
                <div class="audit-filters">
                    <div class="filter-group">
                        <label>事件类型</label>
                        <select id="audit-event-type" onchange="securityDashboard.filterAudit()">
                            <option value="all">全部</option>
                            <option value="login">登录</option>
                            <option value="logout">登出</option>
                            <option value="data_access">数据访问</option>
                            <option value="permission_change">权限变更</option>
                            <option value="security_alert">安全告警</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>严重程度</label>
                        <select id="audit-severity" onchange="securityDashboard.filterAudit()">
                            <option value="all">全部</option>
                            <option value="critical">严重</option>
                            <option value="error">错误</option>
                            <option value="warning">警告</option>
                            <option value="info">信息</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>时间范围</label>
                        <select id="audit-time-range" onchange="securityDashboard.filterAudit()">
                            <option value="1h">最近1小时</option>
                            <option value="24h">最近24小时</option>
                            <option value="7d">最近7天</option>
                            <option value="30d">最近30天</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>用户</label>
                        <input type="text" id="audit-user" placeholder="输入用户ID" onchange="securityDashboard.filterAudit()">
                    </div>
                    <button class="btn btn-primary" onclick="securityDashboard.exportAudit()">
                        📥 导出日志
                    </button>
                </div>

                <!-- 审计日志表格 -->
                <div class="audit-table-container">
                    <table class="audit-table">
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>事件类型</th>
                                <th>用户</th>
                                <th>IP地址</th>
                                <th>操作</th>
                                <th>状态</th>
                                <th>详情</th>
                            </tr>
                        </thead>
                        <tbody id="audit-tbody">
                            <!-- 动态填充 -->
                        </tbody>
                    </table>
                </div>

                <!-- 分页 -->
                <div class="pagination">
                    <button class="btn btn-secondary" onclick="securityDashboard.prevPage()">上一页</button>
                    <span id="page-info">第 1 页</span>
                    <button class="btn btn-secondary" onclick="securityDashboard.nextPage()">下一页</button>
                </div>
            </div>
        `;
    }

    renderWafTab() {
        return `
            <div class="waf-container">
                <!-- WAF状态 -->
                <div class="waf-status-section">
                    <div class="waf-status-card">
                        <div class="status-header">
                            <h3>🛡️ WAF状态</h3>
                            <label class="switch">
                                <input type="checkbox" id="waf-toggle" checked onchange="securityDashboard.toggleWAF()">
                                <span class="slider"></span>
                            </label>
                        </div>
                        <div class="status-metrics">
                            <div class="metric">
                                <span class="metric-label">运行时间</span>
                                <span class="metric-value" id="waf-uptime">99.9%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">处理请求</span>
                                <span class="metric-value" id="waf-requests">1,234,567</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">拦截率</span>
                                <span class="metric-value" id="waf-block-rate">0.15%</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 防护规则 -->
                <div class="waf-rules-section">
                    <div class="section-header">
                        <h3>📋 防护规则</h3>
                        <button class="btn btn-primary" onclick="securityDashboard.addWAFRule()">
                            + 添加规则
                        </button>
                    </div>
                    <div class="rules-list" id="waf-rules">
                        <div class="rule-item enabled">
                            <div class="rule-info">
                                <div class="rule-name">SQL注入防护</div>
                                <div class="rule-desc">检测并阻止SQL注入攻击</div>
                                <div class="rule-tags">
                                    <span class="tag high">高危</span>
                                    <span class="tag">系统规则</span>
                                </div>
                            </div>
                            <div class="rule-stats">
                                <div class="stat">拦截: 1,234</div>
                                <div class="stat">误报: 0.01%</div>
                            </div>
                            <div class="rule-actions">
                                <label class="switch small">
                                    <input type="checkbox" checked onchange="securityDashboard.toggleRule('sql-injection')">
                                    <span class="slider"></span>
                                </label>
                                <button class="btn-icon" onclick="securityDashboard.editRule('sql-injection')">✏️</button>
                            </div>
                        </div>
                        <div class="rule-item enabled">
                            <div class="rule-info">
                                <div class="rule-name">XSS攻击防护</div>
                                <div class="rule-desc">检测并阻止跨站脚本攻击</div>
                                <div class="rule-tags">
                                    <span class="tag high">高危</span>
                                    <span class="tag">系统规则</span>
                                </div>
                            </div>
                            <div class="rule-stats">
                                <div class="stat">拦截: 567</div>
                                <div class="stat">误报: 0.02%</div>
                            </div>
                            <div class="rule-actions">
                                <label class="switch small">
                                    <input type="checkbox" checked onchange="securityDashboard.toggleRule('xss')">
                                    <span class="slider"></span>
                                </label>
                                <button class="btn-icon" onclick="securityDashboard.editRule('xss')">✏️</button>
                            </div>
                        </div>
                        <div class="rule-item enabled">
                            <div class="rule-info">
                                <div class="rule-name">路径遍历防护</div>
                                <div class="rule-desc">阻止目录遍历攻击</div>
                                <div class="rule-tags">
                                    <span class="tag medium">中危</span>
                                    <span class="tag">系统规则</span>
                                </div>
                            </div>
                            <div class="rule-stats">
                                <div class="stat">拦截: 89</div>
                                <div class="stat">误报: 0%</div>
                            </div>
                            <div class="rule-actions">
                                <label class="switch small">
                                    <input type="checkbox" checked onchange="securityDashboard.toggleRule('path-traversal')">
                                    <span class="slider"></span>
                                </label>
                                <button class="btn-icon" onclick="securityDashboard.editRule('path-traversal')">✏️</button>
                            </div>
                        </div>
                        <div class="rule-item enabled">
                            <div class="rule-info">
                                <div class="rule-name">敏感文件访问防护</div>
                                <div class="rule-desc">阻止访问敏感配置文件</div>
                                <div class="rule-tags">
                                    <span class="tag medium">中危</span>
                                    <span class="tag">系统规则</span>
                                </div>
                            </div>
                            <div class="rule-stats">
                                <div class="stat">拦截: 234</div>
                                <div class="stat">误报: 0%</div>
                            </div>
                            <div class="rule-actions">
                                <label class="switch small">
                                    <input type="checkbox" checked onchange="securityDashboard.toggleRule('sensitive-file')">
                                    <span class="slider"></span>
                                </label>
                                <button class="btn-icon" onclick="securityDashboard.editRule('sensitive-file')">✏️</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- IP白名单/黑名单 -->
                <div class="waf-ip-lists">
                    <div class="ip-list-section">
                        <h4>✅ IP白名单</h4>
                        <div class="ip-list" id="whitelist-ips">
                            <div class="ip-item">
                                <span class="ip">127.0.0.1</span>
                                <span class="ip-desc">本地主机</span>
                                <button class="btn-icon" onclick="securityDashboard.removeIP('whitelist', '127.0.0.1')">❌</button>
                            </div>
                        </div>
                        <button class="btn btn-secondary" onclick="securityDashboard.addIP('whitelist')">
                            + 添加IP
                        </button>
                    </div>
                    <div class="ip-list-section">
                        <h4>❌ IP黑名单</h4>
                        <div class="ip-list" id="blacklist-ips">
                            <!-- 动态填充 -->
                        </div>
                        <button class="btn btn-secondary" onclick="securityDashboard.addIP('blacklist')">
                            + 添加IP
                        </button>
                    </div>
                </div>

                <!-- 速率限制配置 -->
                <div class="rate-limit-section">
                    <h3>⏱️ 速率限制</h3>
                    <div class="rate-limit-config">
                        <div class="config-item">
                            <label>每分钟请求限制</label>
                            <input type="number" id="rate-limit-requests" value="100" onchange="securityDashboard.updateRateLimit()">
                        </div>
                        <div class="config-item">
                            <label>封禁时长（分钟）</label>
                            <input type="number" id="rate-limit-block-duration" value="60" onchange="securityDashboard.updateRateLimit()">
                        </div>
                        <div class="config-item">
                            <label>白名单IP豁免</label>
                            <label class="switch">
                                <input type="checkbox" id="whitelist-exempt" checked onchange="securityDashboard.updateRateLimit()">
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderComplianceTab() {
        return `
            <div class="compliance-container">
                <!-- 合规概览 -->
                <div class="compliance-overview">
                    <div class="compliance-score-card">
                        <div class="score-circle">
                            <svg viewBox="0 0 100 100">
                                <circle class="score-bg" cx="50" cy="50" r="45"/>
                                <circle class="score-progress" cx="50" cy="50" r="45" 
                                        stroke-dasharray="283" stroke-dashoffset="14"/>
                            </svg>
                            <div class="score-value">95%</div>
                        </div>
                        <div class="score-label">整体合规评分</div>
                    </div>
                    <div class="compliance-standards">
                        <div class="standard-item compliant">
                            <span class="standard-icon">✅</span>
                            <span class="standard-name">OWASP Top 10</span>
                            <span class="standard-status">合规</span>
                        </div>
                        <div class="standard-item compliant">
                            <span class="standard-icon">✅</span>
                            <span class="standard-name">SOC 2 Type II</span>
                            <span class="standard-status">合规</span>
                        </div>
                        <div class="standard-item warning">
                            <span class="standard-icon">⚠️</span>
                            <span class="standard-name">GDPR Article 32</span>
                            <span class="standard-status">需改进</span>
                        </div>
                        <div class="standard-item compliant">
                            <span class="standard-icon">✅</span>
                            <span class="standard-name">ISO 27001</span>
                            <span class="standard-status">合规</span>
                        </div>
                    </div>
                </div>

                <!-- 安全检查清单 -->
                <div class="compliance-checklist">
                    <h3>✅ 安全检查清单</h3>
                    <div class="checklist-categories">
                        <div class="checklist-category">
                            <h4>🔐 认证与访问控制</h4>
                            <div class="checklist-items">
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">强密码策略已启用</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">多因素认证(MFA)已配置</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">会话超时机制已启用</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">账户锁定策略已启用</span>
                                </div>
                                <div class="checklist-item warning">
                                    <span class="check-icon">!</span>
                                    <span class="item-text">定期密码更换策略</span>
                                    <span class="item-action">建议配置</span>
                                </div>
                            </div>
                        </div>
                        <div class="checklist-category">
                            <h4>🛡️ 数据保护</h4>
                            <div class="checklist-items">
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">敏感数据加密存储</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">传输层加密(TLS)</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">PII数据掩码处理</span>
                                </div>
                                <div class="checklist-item warning">
                                    <span class="check-icon">!</span>
                                    <span class="item-text">数据备份加密</span>
                                    <span class="item-action">建议配置</span>
                                </div>
                            </div>
                        </div>
                        <div class="checklist-category">
                            <h4>📝 审计与监控</h4>
                            <div class="checklist-items">
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">安全事件日志记录</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">用户行为审计</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">实时威胁监控</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">日志防篡改保护</span>
                                </div>
                            </div>
                        </div>
                        <div class="checklist-category">
                            <h4>🌐 网络安全</h4>
                            <div class="checklist-items">
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">WAF已启用</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">DDoS防护</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">速率限制已配置</span>
                                </div>
                                <div class="checklist-item checked">
                                    <span class="check-icon">✓</span>
                                    <span class="item-text">IP黑白名单</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 合规报告 -->
                <div class="compliance-reports">
                    <h3>📊 合规报告</h3>
                    <div class="reports-list">
                        <div class="report-item">
                            <div class="report-info">
                                <div class="report-name">月度安全评估报告</div>
                                <div class="report-date">生成时间: 2024-01-15</div>
                            </div>
                            <button class="btn btn-secondary" onclick="securityDashboard.downloadReport('monthly')">
                                下载
                            </button>
                        </div>
                        <div class="report-item">
                            <div class="report-info">
                                <div class="report-name">SOC 2 合规报告</div>
                                <div class="report-date">生成时间: 2024-01-01</div>
                            </div>
                            <button class="btn btn-secondary" onclick="securityDashboard.downloadReport('soc2')">
                                下载
                            </button>
                        </div>
                        <div class="report-item">
                            <div class="report-info">
                                <div class="report-name">GDPR 数据处理记录</div>
                                <div class="report-date">生成时间: 2024-01-10</div>
                            </div>
                            <button class="btn btn-secondary" onclick="securityDashboard.downloadReport('gdpr')">
                                下载
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // ==================== 交互方法 ====================

    switchTab(tabName) {
        // 更新按钮状态
        document.querySelectorAll('.security-tabs .tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });

        // 更新内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`tab-${tabName}`).classList.add('active');

        this.currentTab = tabName;

        // 初始化图表
        if (tabName === 'overview') {
            this.initCharts();
        }
    }

    initCharts() {
        // 安全趋势图
        const trendCanvas = document.getElementById('trendCanvas');
        if (trendCanvas && typeof Chart !== 'undefined') {
            const ctx = trendCanvas.getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
                    datasets: [{
                        label: '拦截攻击',
                        data: [12, 19, 8, 15, 22, 10, 18],
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4
                    }, {
                        label: '正常请求',
                        data: [1200, 1350, 1100, 1450, 1600, 1300, 1500],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // 攻击类型饼图
        const typeCanvas = document.getElementById('typeCanvas');
        if (typeCanvas && typeof Chart !== 'undefined') {
            const ctx = typeCanvas.getContext('2d');
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['SQL注入', 'XSS攻击', '路径遍历', '暴力破解', '其他'],
                    datasets: [{
                        data: [35, 25, 15, 10, 15],
                        backgroundColor: [
                            '#ef4444',
                            '#f59e0b',
                            '#3b82f6',
                            '#8b5cf6',
                            '#6b7280'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }

    startRealtimeUpdates() {
        // 模拟实时数据更新
        this.refreshInterval = setInterval(() => {
            this.updateStats();
            this.simulateThreats();
        }, 3000);
    }

    updateStats() {
        // 更新统计数据
        this.securityStats.blockedAttacks += Math.floor(Math.random() * 3);
        this.securityStats.loginAttempts += Math.floor(Math.random() * 5);
        this.securityStats.activeSessions = 50 + Math.floor(Math.random() * 20);
        this.securityStats.apiCalls += Math.floor(Math.random() * 10);

        // 更新UI
        document.getElementById('blocked-count').textContent = this.securityStats.blockedAttacks;
        document.getElementById('sessions-count').textContent = this.securityStats.activeSessions;
    }

    simulateThreats() {
        // 模拟威胁事件
        const threatTypes = [
            { type: 'SQL注入', severity: 'high', ip: '192.168.1.' + Math.floor(Math.random() * 255) },
            { type: 'XSS攻击', severity: 'medium', ip: '10.0.0.' + Math.floor(Math.random() * 255) },
            { type: '路径遍历', severity: 'medium', ip: '172.16.0.' + Math.floor(Math.random() * 255) }
        ];

        if (Math.random() > 0.7) {
            const threat = threatTypes[Math.floor(Math.random() * threatTypes.length)];
            this.addSecurityEvent(threat);
        }
    }

    addSecurityEvent(threat) {
        const eventsList = document.getElementById('security-events');
        if (!eventsList) return;

        const eventItem = document.createElement('div');
        eventItem.className = `event-item ${threat.severity}`;
        eventItem.innerHTML = `
            <span class="event-time">${new Date().toLocaleTimeString()}</span>
            <span class="event-type">${threat.type}</span>
            <span class="event-desc">来自 ${threat.ip} 的攻击已被拦截</span>
        `;

        eventsList.insertBefore(eventItem, eventsList.firstChild);

        // 保持最多10条记录
        while (eventsList.children.length > 10) {
            eventsList.removeChild(eventsList.lastChild);
        }

        // 更新威胁计数
        const badge = document.getElementById('threat-badge');
        if (badge) {
            badge.textContent = parseInt(badge.textContent) + 1;
        }
    }

    // ==================== 操作方法 ====================

    emergencyLockdown() {
        if (confirm('⚠️ 确定要启动紧急锁定模式吗？这将阻止所有外部访问！')) {
            alert('🚨 紧急锁定模式已启动！\n\n所有外部访问已被阻止，仅允许本地管理访问。');
            document.getElementById('security-status').textContent = '🔴 紧急锁定';
            document.getElementById('security-status').className = 'security-badge danger';
        }
    }

    exportReport() {
        alert('📊 安全报告已生成并开始下载');
    }

    filterThreats() {
        // 实现威胁筛选逻辑
        console.log('筛选威胁...');
    }

    clearAllThreats() {
        if (confirm('确定要清除所有威胁记录吗？')) {
            document.getElementById('threats-tbody').innerHTML = '';
            document.getElementById('threat-badge').textContent = '0';
        }
    }

    showBlockIPDialog() {
        const ip = prompt('输入要封禁的IP地址:');
        if (ip) {
            alert(`IP ${ip} 已被添加到黑名单`);
        }
    }

    showAddUserDialog() {
        alert('打开添加用户对话框');
    }

    editUser(userId) {
        alert(`编辑用户: ${userId}`);
    }

    resetPassword(userId) {
        if (confirm(`确定要重置用户 ${userId} 的密码吗？`)) {
            alert('密码重置链接已发送');
        }
    }

    createAPIKey() {
        const name = prompt('输入API密钥名称:');
        if (name) {
            alert(`API密钥 "${name}" 已创建\n\n密钥: kag_xxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx\n\n请妥善保存，此密钥只显示一次！`);
        }
    }

    terminateAllSessions() {
        if (confirm('确定要终止所有用户会话吗？所有用户将被登出。')) {
            alert('所有会话已终止');
        }
    }

    exportAudit() {
        alert('审计日志导出中...');
    }

    filterAudit() {
        console.log('筛选审计日志...');
    }

    prevPage() {
        console.log('上一页');
    }

    nextPage() {
        console.log('下一页');
    }

    toggleWAF() {
        const enabled = document.getElementById('waf-toggle').checked;
        alert(enabled ? 'WAF已启用' : 'WAF已禁用');
    }

    toggleRule(ruleId) {
        console.log(`切换规则: ${ruleId}`);
    }

    editRule(ruleId) {
        alert(`编辑规则: ${ruleId}`);
    }

    addWAFRule() {
        alert('添加自定义WAF规则');
    }

    addIP(listType) {
        const ip = prompt(`输入要添加到${listType === 'whitelist' ? '白名单' : '黑名单'}的IP:`);
        if (ip) {
            alert(`IP ${ip} 已添加到${listType === 'whitelist' ? '白名单' : '黑名单'}`);
        }
    }

    removeIP(listType, ip) {
        if (confirm(`确定要从${listType === 'whitelist' ? '白名单' : '黑名单'}中移除 ${ip} 吗？`)) {
            alert(`IP ${ip} 已移除`);
        }
    }

    updateRateLimit() {
        console.log('更新速率限制配置');
    }

    downloadReport(type) {
        alert(`正在下载 ${type} 报告...`);
    }

    attachEventListeners() {
        // 绑定事件监听器
        console.log('安全控制台事件监听器已绑定');
    }
}

// 初始化
let securityDashboard;
document.addEventListener('DOMContentLoaded', () => {
    securityDashboard = new KaguyaSecurityDashboard();
});

// 导出供其他模块使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KaguyaSecurityDashboard;
}
