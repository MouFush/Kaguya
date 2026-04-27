#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加增强记忆系统前端到HTML模板
"""

def add_memory_tab_to_html():
    """添加记忆Tab到HTML"""
    
    # 读取文件
    with open('qwen3_web_final.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在sidebar-tabs中添加新的tab按钮
    tab_button = '<button class="sidebar-tab" onclick="switchTab(\'enhancedMemory\', this)">🧠记忆</button>'
    
    # 找到最后一个tab按钮
    last_tab_pattern = "<button class=\"sidebar-tab\" onclick=\"switchTab('rag', this)\">RAG</button>"
    if last_tab_pattern in content:
        content = content.replace(
            last_tab_pattern,
            last_tab_pattern + '\n                ' + tab_button
        )
    
    # 2. 在ragTab后面添加增强记忆Tab内容
    memory_tab_html = '''
            <div id="enhancedMemoryTab" class="tab-content">
                <div class="memory-header" style="padding:16px;border-bottom:1px solid var(--border);">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <h3 style="margin:0;font-size:16px;color:var(--text-primary);">🧠 增强记忆</h3>
                        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                            <span style="font-size:12px;color:var(--text-secondary);">记忆模式</span>
                            <input type="checkbox" id="memoryModeToggle" onchange="toggleMemoryMode()" style="width:auto;">
                        </label>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
                        <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                            <span id="emTotalMemories" style="display:block;font-size:18px;font-weight:700;color:var(--primary);">0</span>
                            <span style="font-size:10px;color:var(--text-muted);">总记忆</span>
                        </div>
                        <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                            <span id="emDistilledMemories" style="display:block;font-size:18px;font-weight:700;color:var(--secondary);">0</span>
                            <span style="font-size:10px;color:var(--text-muted);">蒸馏记忆</span>
                        </div>
                        <div style="text-align:center;padding:10px;background:var(--bg-secondary);border-radius:8px;border:1px solid var(--border);">
                            <span id="emCacheSize" style="display:block;font-size:18px;font-weight:700;color:var(--accent);">0MB</span>
                            <span style="font-size:10px;color:var(--text-muted);">缓存大小</span>
                        </div>
                    </div>
                </div>
                <div style="padding:12px;flex:1;overflow-y:auto;">
                    <div style="display:flex;gap:8px;margin-bottom:12px;">
                        <button class="quick-tool" onclick="loadMemories()" style="flex:1;justify-content:center;padding:8px 12px;background:linear-gradient(135deg,var(--primary),var(--secondary));color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">加载记忆</button>
                        <button class="quick-tool" onclick="loadDistilledMemories()" style="flex:1;justify-content:center;padding:8px 12px;background:var(--bg-primary);color:var(--text-primary);border:1px solid var(--border);border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">蒸馏记忆</button>
                    </div>
                    <div id="memoriesList" style="max-height:300px;overflow-y:auto;">
                        <div style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">点击"加载记忆"查看本地缓存</div>
                    </div>
                    <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px;">
                        <button class="quick-tool" onclick="clearAllMemories()" style="justify-content:center;padding:10px 12px;background:var(--warning);color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">清空所有记忆</button>
                        <button class="quick-tool" onclick="deleteDeviceCache()" style="justify-content:center;padding:10px 12px;background:var(--danger);color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">删除设备缓存</button>
                    </div>
                </div>
            </div>
'''
    
    # 找到ragTab的结束位置
    rag_tab_end = '</div>\n            <div class="sidebar-footer">'
    if rag_tab_end in content:
        content = content.replace(
            rag_tab_end,
            '</div>' + memory_tab_html + '\n            <div class="sidebar-footer">'
        )
    
    # 3. 添加JavaScript函数
    memory_js = '''

        // ==================== 增强记忆系统 ====================
        function getDeviceId() {
            let deviceId = localStorage.getItem('kaguya_device_id');
            if (!deviceId) {
                deviceId = 'device_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('kaguya_device_id', deviceId);
            }
            return deviceId;
        }

        function toggleMemoryMode() {
            const checkbox = document.getElementById('memoryModeToggle');
            const enabled = checkbox.checked;
            fetch('/memory/device/toggle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({device_id: getDeviceId(), enabled: enabled})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showNotification('记忆模式已' + (enabled ? '开启' : '关闭'), 'success');
                    updateMemoryStats();
                } else {
                    checkbox.checked = !enabled;
                }
            });
        }

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

        function deleteMemory(memoryId) {
            if (!confirm('确定要删除这条记忆吗？')) return;
            fetch('/memory/device/delete/' + memoryId + '?device_id=' + getDeviceId(), {method: 'DELETE'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showNotification('记忆已删除', 'success');
                    loadMemories();
                    updateMemoryStats();
                }
            });
        }

        function clearAllMemories() {
            if (!confirm('确定要清空所有记忆吗？此操作不可恢复！')) return;
            fetch('/memory/device/clear', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({device_id: getDeviceId(), include_distilled: true})
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

        function updateMemoryStats() {
            fetch('/memory/device/status?device_id=' + getDeviceId())
            .then(r => r.json())
            .then(data => {
                if (data.success && data.stats) {
                    document.getElementById('emTotalMemories').textContent = data.stats.total_memories || 0;
                    document.getElementById('emDistilledMemories').textContent = data.stats.distilled_memories || 0;
                    document.getElementById('emCacheSize').textContent = (data.stats.cache_size_mb || 0) + 'MB';
                    document.getElementById('memoryModeToggle').checked = data.stats.memory_mode_enabled;
                }
            })
            .catch(() => {});
        }

        function initEnhancedMemory() {
            fetch('/memory/device/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({device_id: getDeviceId(), enable_memory: false})
            })
            .then(() => updateMemoryStats());
            setInterval(updateMemoryStats, 10000);
        }

        document.addEventListener('DOMContentLoaded', initEnhancedMemory);
'''
    
    # 在</script>前添加JavaScript
    script_end = '</script>\n</body>'
    if script_end in content:
        content = content.replace(script_end, memory_js + '\n    </script>\n</body>')
    
    # 保存
    with open('qwen3_web_final.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 前端界面集成完成")

if __name__ == "__main__":
    print("=" * 60)
    print("🎨 添加增强记忆系统前端")
    print("=" * 60)
    add_memory_tab_to_html()
    print("=" * 60)
    print("✅ 前端集成完成!")
    print("=" * 60)
