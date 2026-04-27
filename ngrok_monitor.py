#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ngrok 访问监控工具
用于监控通过 ngrok 访问的网站访问情况
"""

from flask import Flask, request, jsonify, render_template_string
import json
import time
import threading
from datetime import datetime
import requests

app = Flask(__name__)

# 访问日志存储
access_logs = []
max_logs = 1000  # 最多保存1000条记录

# 统计信息
stats = {
    'total_visits': 0,
    'unique_ips': set(),
    'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'online_users': 0,
    'last_visit': None
}

# 实时监控数据
realtime_data = {
    'visits_per_minute': [],
    'device_types': {},
    'locations': {},
    'referrers': {}
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ngrok 访问监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
        }
        .logs-section {
            background: rgba(255,255,255,0.95);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        .logs-title {
            font-size: 1.5em;
            color: #333;
        }
        .refresh-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(102,126,234,0.4);
        }
        .log-entry {
            display: grid;
            grid-template-columns: 180px 120px 200px 1fr 100px;
            gap: 15px;
            padding: 12px;
            border-bottom: 1px solid #eee;
            align-items: center;
            font-size: 13px;
        }
        .log-entry:hover {
            background: #f8f9fa;
            border-radius: 8px;
        }
        .log-time {
            color: #667eea;
            font-weight: 500;
        }
        .log-ip {
            font-family: monospace;
            background: #f0f0f0;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .log-location {
            color: #666;
        }
        .log-device {
            color: #888;
            font-size: 12px;
        }
        .log-status {
            text-align: center;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }
        .status-success {
            background: #d4edda;
            color: #155724;
        }
        .status-error {
            background: #f8d7da;
            color: #721c24;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .online-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #d4edda;
            color: #155724;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }
        .online-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #666;
            font-size: 14px;
        }
        .auto-refresh input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .chart-container {
            height: 200px;
            margin-top: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
        }
        @media (max-width: 768px) {
            .log-entry {
                grid-template-columns: 1fr;
                gap: 5px;
            }
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Ngrok 访问监控</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">总访问量</div>
                <div class="stat-value" id="totalVisits">0</div>
                <div class="online-indicator">
                    <span class="online-dot"></span>
                    <span>监控中</span>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-label">独立IP数</div>
                <div class="stat-value" id="uniqueIps">0</div>
                <div class="stat-label">不同设备</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">在线用户</div>
                <div class="stat-value" id="onlineUsers">0</div>
                <div class="stat-label">当前活跃</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">监控时长</div>
                <div class="stat-value" id="monitorTime" style="font-size: 1.5em;">-</div>
                <div class="stat-label" id="startTime">启动于: -</div>
            </div>
        </div>
        
        <div class="logs-section">
            <div class="logs-header">
                <h2 class="logs-title">📝 访问日志</h2>
                <div style="display: flex; gap: 15px; align-items: center;">
                    <label class="auto-refresh">
                        <input type="checkbox" id="autoRefresh" checked>
                        自动刷新 (5秒)
                    </label>
                    <button class="refresh-btn" onclick="refreshData()">🔄 立即刷新</button>
                </div>
            </div>
            <div id="logsContainer">
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div>暂无访问记录</div>
                    <div style="font-size: 0.9em; margin-top: 10px;">等待用户访问 https://unsmoothly-hypokalemic-courtney.ngrok-free.dev</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let autoRefreshInterval;
        
        function formatTime(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleString('zh-CN');
        }
        
        function getTimeDiff(startTime) {
            const start = new Date(startTime);
            const now = new Date();
            const diff = Math.floor((now - start) / 1000);
            
            const hours = Math.floor(diff / 3600);
            const minutes = Math.floor((diff % 3600) / 60);
            const seconds = diff % 60;
            
            if (hours > 0) return `${hours}小时${minutes}分`;
            if (minutes > 0) return `${minutes}分${seconds}秒`;
            return `${seconds}秒`;
        }
        
        async function refreshData() {
            try {
                // 从主应用获取访问日志
                const response = await fetch('http://127.0.0.1:5000/api/access_logs');
                const data = await response.json();
                
                if (data.success) {
                    // 更新统计数据
                    document.getElementById('totalVisits').textContent = data.total_visits;
                    document.getElementById('uniqueIps').textContent = data.unique_ips;
                    document.getElementById('onlineUsers').textContent = Math.min(data.unique_ips, 5); // 估算在线用户
                    
                    // 更新日志列表
                    const logsContainer = document.getElementById('logsContainer');
                    if (data.logs && data.logs.length > 0) {
                        logsContainer.innerHTML = data.logs.map(log => `
                            <div class="log-entry">
                                <div class="log-time">${formatTime(log.time)}</div>
                                <div class="log-ip">${log.ip}</div>
                                <div class="log-location">${log.referrer || '直接访问'}</div>
                                <div class="log-device">${log.user_agent || '未知设备'}</div>
                                <div class="log-status status-success">${log.status}</div>
                            </div>
                        `).join('');
                    } else {
                        logsContainer.innerHTML = `
                            <div class="empty-state">
                                <div class="empty-state-icon">📭</div>
                                <div>暂无访问记录</div>
                                <div style="font-size: 0.9em; margin-top: 10px;">等待用户访问 https://unsmoothly-hypokalemic-courtney.ngrok-free.dev</div>
                            </div>
                        `;
                    }
                }
            } catch (error) {
                console.error('刷新数据失败:', error);
                document.getElementById('logsContainer').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">⚠️</div>
                        <div>无法连接到主应用</div>
                        <div style="font-size: 0.9em; margin-top: 10px;">请确保主应用正在运行 (http://127.0.0.1:5000)</div>
                    </div>
                `;
            }
        }
        
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            if (checkbox.checked) {
                autoRefreshInterval = setInterval(refreshData, 5000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }
        
        // 初始化
        document.getElementById('autoRefresh').addEventListener('change', toggleAutoRefresh);
        refreshData();
        toggleAutoRefresh();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """监控主页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    return jsonify({
        'total_visits': stats['total_visits'],
        'unique_ips': len(stats['unique_ips']),
        'online_users': stats['online_users'],
        'start_time': stats['start_time'],
        'last_visit': stats['last_visit'],
        'logs': access_logs[-50:]  # 返回最近50条日志
    })

@app.route('/api/log', methods=['POST'])
def log_access():
    """记录访问日志"""
    data = request.json
    
    log_entry = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': data.get('ip', request.remote_addr),
        'user_agent': data.get('user_agent', '')[:100],
        'location': data.get('location', ''),
        'referrer': data.get('referrer', ''),
        'status': data.get('status', '200'),
        'path': data.get('path', '/')
    }
    
    access_logs.append(log_entry)
    
    # 限制日志数量
    if len(access_logs) > max_logs:
        access_logs.pop(0)
    
    # 更新统计
    stats['total_visits'] += 1
    stats['unique_ips'].add(log_entry['ip'])
    stats['last_visit'] = log_entry['time']
    
    return jsonify({'success': True})

@app.route('/api/track')
def track_visit():
    """追踪访问（通过图片请求）"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    referrer = request.headers.get('Referer', '')
    
    log_entry = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': ip.split(',')[0].strip() if ',' in ip else ip,
        'user_agent': user_agent[:100],
        'location': '',
        'referrer': referrer,
        'status': '200',
        'path': request.args.get('path', '/')
    }
    
    access_logs.append(log_entry)
    
    if len(access_logs) > max_logs:
        access_logs.pop(0)
    
    stats['total_visits'] += 1
    stats['unique_ips'].add(log_entry['ip'])
    stats['last_visit'] = log_entry['time']
    
    # 返回1x1透明像素
    return 'GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', 200, {'Content-Type': 'image/gif'}

if __name__ == '__main__':
    print("=" * 60)
    print("Ngrok 访问监控工具")
    print("=" * 60)
    print(f"监控地址: https://unsmoothly-hypokalemic-courtney.ngrok-free.dev")
    print(f"监控面板: http://127.0.0.1:8080")
    print("=" * 60)
    print("功能说明:")
    print("- 实时显示访问日志")
    print("- 统计独立IP数")
    print("- 显示在线用户数")
    print("- 自动刷新 (5秒)")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=False)
