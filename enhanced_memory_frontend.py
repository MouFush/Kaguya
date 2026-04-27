#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜AI - 增强记忆系统前端界面
需要添加到主应用的HTML模板中
"""

# 增强记忆系统的HTML内容
ENHANCED_MEMORY_HTML = """
<!-- 增强记忆Tab -->
<div id="enhancedMemoryTab" class="tab-content">
    <div class="memory-header" style="padding:16px;border-bottom:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h3 style="margin:0;font-size:16px;color:var(--text-primary);">🧠 增强记忆系统</h3>
            <label class="memory-toggle" style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                <span style="font-size:12px;color:var(--text-secondary);">记忆模式</span>
                <input type="checkbox" id="memoryModeToggle" onchange="toggleMemoryMode()" style="width:auto;">
                <span class="toggle-slider" style="position:relative;width:44px;height:24px;background:var(--border);border-radius:12px;transition:all 0.3s;">
                    <span style="position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:all 0.3s;"></span>
                </span>
            </label>
        </div>
        <div class="memory-stats" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
            <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                <span id="emTotalMemories" style="display:block;font-size:20px;font-weight:700;color:var(--primary);">0</span>
                <span style="font-size:10px;color:var(--text-muted);">总记忆</span>
            </div>
            <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                <span id="emDistilledMemories" style="display:block;font-size:20px;font-weight:700;color:var(--secondary);">0</span>
                <span style="font-size:10px;color:var(--text-muted);">蒸馏记忆</span>
            </div>
            <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                <span id="emCacheSize" style="display:block;font-size:20px;font-weight:700;color:var(--accent);">0MB</span>
                <span style="font-size:10px;color:var(--text-muted);">缓存大小</span>
            </div>
        </div>
    </div>
    
    <div class="memory-content" style="padding:12px;flex:1;overflow-y:auto;">
        <!-- 记忆管理 -->
        <div class="memory-section" style="background:var(--bg-secondary);border-radius:12px;margin-bottom:12px;border:1px solid var(--border);overflow:hidden;">
            <div class="memory-section-header" onclick="toggleMemorySection('memory-management')" style="display:flex;align-items:center;padding:12px 16px;cursor:pointer;background:linear-gradient(135deg,rgba(255,255,255,0.6),rgba(255,255,255,0.4));">
                <span style="font-size:18px;margin-right:10px;">💾</span>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:13px;color:var(--text-primary);">记忆管理</div>
                    <div style="font-size:10px;color:var(--text-muted);">查看和管理本地缓存的记忆</div>
                </div>
                <span class="memory-toggle-icon" style="font-size:12px;color:var(--text-muted);transition:transform 0.3s;">▼</span>
            </div>
            <div id="memory-management-content" style="display:none;padding:12px;border-top:1px solid var(--border);background:rgba(0,0,0,0.02);">
                <div style="display:flex;gap:8px;margin-bottom:12px;">
                    <button class="quick-tool" onclick="loadMemories()" style="flex:1;justify-content:center;padding:8px 12px;background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">加载记忆</button>
                    <button class="quick-tool" onclick="loadDistilledMemories()" style="flex:1;justify-content:center;padding:8px 12px;background:var(--bg-primary);color:var(--text-primary);border:1px solid var(--border);border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">蒸馏记忆</button>
                </div>
                <div id="memoriesList" style="max-height:200px;overflow-y:auto;">
                    <div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">
                        点击"加载记忆"查看本地缓存
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 记忆设置 -->
        <div class="memory-section" style="background:var(--bg-secondary);border-radius:12px;margin-bottom:12px;border:1px solid var(--border);overflow:hidden;">
            <div class="memory-section-header" onclick="toggleMemorySection('memory-settings')" style="display:flex;align-items:center;padding:12px 16px;cursor:pointer;background:linear-gradient(135deg,rgba(255,255,255,0.6),rgba(255,255,255,0.4));">
                <span style="font-size:18px;margin-right:10px;">⚙️</span>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:13px;color:var(--text-primary);">记忆设置</div>
                    <div style="font-size:10px;color:var(--text-muted);">配置记忆缓存行为</div>
                </div>
                <span class="memory-toggle-icon" style="font-size:12px;color:var(--text-muted);transition:transform 0.3s;">▼</span>
            </div>
            <div id="memory-settings-content" style="display:none;padding:12px;border-top:1px solid var(--border);background:rgba(0,0,0,0.02);">
                <div style="margin-bottom:12px;">
                    <label style="display:block;font-size:11px;color:var(--text-secondary);margin-bottom:4px;">最大记忆数: <span id="maxMemoriesValue">1000</span></label>
                    <input type="range" min="100" max="5000" step="100" value="1000" oninput="document.getElementById('maxMemoriesValue').textContent=this.value" style="width:100%;margin-bottom:8px;">
                    
                    <label style="display:block;font-size:11px;color:var(--text-secondary);margin-bottom:4px;">保留天数: <span id="retentionDaysValue">30</span></label>
                    <input type="range" min="7" max="365" step="7" value="30" oninput="document.getElementById('retentionDaysValue').textContent=this.value" style="width:100%;margin-bottom:8px;">
                </div>
                <label style="display:flex;align-items:center;gap:6px;margin-bottom:8px;cursor:pointer;font-size:12px;">
                    <input type="checkbox" id="autoDistillCheck" checked style="width:auto;margin:0;"> 自动蒸馏对话
                </label>
                <label style="display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;">
                    <input type="checkbox" id="localCacheCheck" checked style="width:auto;margin:0;"> 本地缓存
                </label>
            </div>
        </div>
        
        <!-- 危险操作 -->
        <div class="memory-section" style="background:var(--bg-secondary);border-radius:12px;margin-bottom:12px;border:1px solid var(--border);overflow:hidden;">
            <div class="memory-section-header" onclick="toggleMemorySection('memory-danger')" style="display:flex;align-items:center;padding:12px 16px;cursor:pointer;background:linear-gradient(135deg,rgba(255,255,255,0.6),rgba(255,255,255,0.4));">
                <span style="font-size:18px;margin-right:10px;">⚠️</span>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:13px;color:var(--text-primary);">危险操作</div>
                    <div style="font-size:10px;color:var(--text-muted);">删除记忆和缓存</div>
                </div>
                <span class="memory-toggle-icon" style="font-size:12px;color:var(--text-muted);transition:transform 0.3s;">▼</span>
            </div>
            <div id="memory-danger-content" style="display:none;padding:12px;border-top:1px solid var(--border);background:rgba(0,0,0,0.02);">
                <div style="display:flex;flex-direction:column;gap:8px;">
                    <button class="quick-tool" onclick="clearAllMemories()" style="justify-content:center;padding:10px 12px;background:var(--warning);color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">清空所有记忆</button>
                    <button class="quick-tool" onclick="deleteDeviceCache()" style="justify-content:center;padding:10px 12px;background:var(--danger);color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">删除设备缓存</button>
                </div>
            </div>
        </div>
    </div>
</div>
"""

# 增强记忆系统的JavaScript
ENHANCED_MEMORY_JS = """
<script>
// ==================== 增强记忆系统 ====================

// 设备ID（从本地存储获取或生成）
function getDeviceId() {
    let deviceId = localStorage.getItem('kaguya_device_id');
    if (!deviceId) {
        deviceId = 'device_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('kaguya_device_id', deviceId);
    }
    return deviceId;
}

// 切换记忆模式
function toggleMemoryMode() {
    const checkbox = document.getElementById('memoryModeToggle');
    const enabled = checkbox.checked;
    
    fetch('/memory/device/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            device_id: getDeviceId(),
            enabled: enabled
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showNotification('记忆模式已' + (enabled ? '开启' : '关闭'), 'success');
            updateMemoryStats();
        } else {
            showNotification('切换失败: ' + data.error, 'error');
            checkbox.checked = !enabled;
        }
    })
    .catch(e => {
        showNotification('网络错误', 'error');
        checkbox.checked = !enabled;
    });
}

// 加载记忆列表
function loadMemories() {
    fetch('/memory/device/memories?device_id=' + getDeviceId())
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const list = document.getElementById('memoriesList');
            if (data.memories.length === 0) {
                list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">暂无记忆</div>';
                return;
            }
            
            list.innerHTML = data.memories.map(m => `
                <div style="background:var(--bg-primary);border-radius:8px;padding:10px;margin-bottom:8px;border:1px solid var(--border);">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
                        <span style="font-size:10px;padding:2px 6px;background:rgba(102,126,234,0.1);color:var(--primary);border-radius:4px;">${m.type}</span>
                        <button onclick="deleteMemory('${m.id}')" style="background:none;border:none;color:var(--danger);cursor:pointer;font-size:12px;padding:0;">🗑️</button>
                    </div>
                    <div style="font-size:12px;color:var(--text-primary);margin-bottom:4px;">${m.content.substring(0, 100)}${m.content.length > 100 ? '...' : ''}</div>
                    <div style="font-size:10px;color:var(--text-muted);">访问: ${m.access_count}次 | ${new Date(m.created_at).toLocaleDateString()}</div>
                </div>
            `).join('');
        }
    });
}

// 加载蒸馏记忆
function loadDistilledMemories() {
    fetch('/memory/device/distilled?device_id=' + getDeviceId())
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const list = document.getElementById('memoriesList');
            if (data.distilled_memories.length === 0) {
                list.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">暂无蒸馏记忆</div>';
                return;
            }
            
            list.innerHTML = data.distilled_memories.map(m => `
                <div style="background:var(--bg-primary);border-radius:8px;padding:10px;margin-bottom:8px;border:1px solid var(--border);">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span style="font-size:10px;padding:2px 6px;background:rgba(118,75,162,0.1);color:var(--secondary);border-radius:4px;">蒸馏</span>
                        <span style="font-size:10px;color:var(--text-muted);">重要性: ${(m.importance_score * 100).toFixed(0)}%</span>
                    </div>
                    <div style="font-size:12px;color:var(--text-primary);margin-bottom:6px;">${m.distilled_content.substring(0, 100)}${m.distilled_content.length > 100 ? '...' : ''}</div>
                    ${m.key_facts.length > 0 ? `<div style="font-size:10px;color:var(--text-secondary);margin-bottom:2px;">📌 ${m.key_facts.join(', ')}</div>` : ''}
                    ${m.user_preferences.length > 0 ? `<div style="font-size:10px;color:var(--text-secondary);margin-bottom:2px;">❤️ ${m.user_preferences.join(', ')}</div>` : ''}
                </div>
            `).join('');
        }
    });
}

// 删除单条记忆
function deleteMemory(memoryId) {
    if (!confirm('确定要删除这条记忆吗？')) return;
    
    fetch('/memory/device/delete/' + memoryId + '?device_id=' + getDeviceId(), {
        method: 'DELETE'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showNotification('记忆已删除', 'success');
            loadMemories();
            updateMemoryStats();
        }
    });
}

// 清空所有记忆
function clearAllMemories() {
    if (!confirm('确定要清空所有记忆吗？此操作不可恢复！')) return;
    
    fetch('/memory/device/clear', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            device_id: getDeviceId(),
            include_distilled: true
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showNotification('已清空 ' + data.deleted_count + ' 条记忆', 'success');
            loadMemories();
            updateMemoryStats();
        }
    });
}

// 删除设备缓存
function deleteDeviceCache() {
    if (!confirm('确定要删除设备缓存吗？这将删除所有配置和记忆！')) return;
    
    fetch('/memory/device/delete_cache', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({device_id: getDeviceId()})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showNotification('设备缓存已删除', 'success');
            localStorage.removeItem('kaguya_device_id');
            location.reload();
        }
    });
}

// 更新记忆统计
function updateMemoryStats() {
    fetch('/memory/device/status?device_id=' + getDeviceId())
    .then(r => r.json())
    .then(data => {
        if (data.success && data.stats) {
            document.getElementById('emTotalMemories').textContent = data.stats.total_memories || 0;
            document.getElementById('emDistilledMemories').textContent = data.stats.distilled_memories || 0;
            document.getElementById('emCacheSize').textContent = (data.stats.cache_size_mb || 0) + 'MB';
            
            // 更新开关状态
            document.getElementById('memoryModeToggle').checked = data.stats.memory_mode_enabled;
        }
    })
    .catch(() => {});
}

// 切换记忆区块
function toggleMemorySection(sectionId) {
    const content = document.getElementById(sectionId + '-content');
    const section = content.closest('.memory-section');
    const toggle = section.querySelector('.memory-toggle-icon');
    
    if (content.style.display === 'none') {
        content.style.display = 'block';
        section.classList.add('expanded');
        toggle.textContent = '▲';
    } else {
        content.style.display = 'none';
        section.classList.remove('expanded');
        toggle.textContent = '▼';
    }
}

// 初始化增强记忆系统
function initEnhancedMemory() {
    // 注册设备
    fetch('/memory/device/register', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            device_id: getDeviceId(),
            enable_memory: false
        })
    })
    .then(() => updateMemoryStats());
    
    // 定期更新统计
    setInterval(updateMemoryStats, 10000);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initEnhancedMemory);
</script>
"""

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 辉夜AI - 增强记忆系统前端模块")
    print("=" * 60)
    print()
    print("使用方法:")
    print("1. 将 ENHANCED_MEMORY_HTML 添加到HTML模板的tab-content区域")
    print("2. 将 ENHANCED_MEMORY_JS 添加到HTML模板的</body>前")
    print("3. 在sidebar-tabs中添加新的tab按钮")
    print()
    print("功能特性:")
    print("  - 记忆模式开关控制")
    print("  - 本地记忆缓存查看")
    print("  - 蒸馏记忆管理")
    print("  - 记忆删除和清理")
    print("  - 设备缓存管理")
    print("=" * 60)
