import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

total_lines = len(content.split('\n'))
print(f"原始行数: {total_lines}")

changes = []

# ============================================================
# 1. 替换8个重复的updateXxxStatus函数为crudUpdate调用
# ============================================================
print("[1] 替换重复的updateXxxStatus函数...")

replacements = [
    (
        '''function updateProjectTaskStatus(id, status) {
            fetch(`/project/tasks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateProjectTaskStatus(id, status) { crudUpdate('/project/tasks', id, {status}); }'''
    ),
    (
        '''function updateRiskStatus(id, status) {
            fetch(`/project/risks/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateRiskStatus(id, status) { crudUpdate('/project/risks', id, {status}); }'''
    ),
    (
        '''function updateOpsCampaignStatus(id, status) {
            fetch(`/ops/campaigns/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateOpsCampaignStatus(id, status) { crudUpdate('/ops/campaigns', id, {status}); }'''
    ),
    (
        '''function updateReleaseStatus(id, status) {
            fetch(`/release/plans/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateReleaseStatus(id, status) { crudUpdate('/release/plans', id, {status}); }'''
    ),
    (
        '''function updateAlertRuleStatus(id, status) {
            fetch(`/alerts/rules/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateAlertRuleStatus(id, status) { crudUpdate('/alerts/rules', id, {status}); }'''
    ),
    (
        '''function updateAbStatus(id, status) {
            fetch(`/ab/experiments/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateAbStatus(id, status) { crudUpdate('/ab/experiments', id, {status}); }'''
    ),
    (
        '''function updateIntegrationStatus(id, status) {
            fetch(`/integrations/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateIntegrationStatus(id, status) { crudUpdate('/integrations', id, {status}); }'''
    ),
    (
        '''function updateMilestoneStatus(id, status, progress) {
            fetch(`/project/milestones/${id}/status`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({status, progress})
            }).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '更新失败');
                loadProjectCenter();
            });
        }''',
        '''function updateMilestoneStatus(id, status, progress) { crudUpdate('/project/milestones', id, {status, progress}); }'''
    ),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new, 1)
        fname = new.split('function ')[1].split('(')[0]
        changes.append(f"{fname}: 8行->1行 crudUpdate")

# ============================================================
# 2. 替换9个重复的deleteXxx函数为crudDelete调用
# ============================================================
print("[2] 替换重复的deleteXxx函数...")

delete_replacements = [
    (
        '''function deleteArtifact(id) {
            fetch(`/artifacts/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除产物');
                loadProjectCenter();
            });
        }''',
        '''function deleteArtifact(id) { crudDelete('/artifacts', id, () => showToast('已删除产物')); }'''
    ),
    (
        '''function deleteProjectTask(id) {
            fetch(`/project/tasks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除任务');
                loadProjectCenter();
            });
        }''',
        '''function deleteProjectTask(id) { crudDelete('/project/tasks', id, () => showToast('已删除任务')); }'''
    ),
    (
        '''function deleteMilestone(id) {
            fetch(`/project/milestones/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除里程碑');
                loadProjectCenter();
            });
        }''',
        '''function deleteMilestone(id) { crudDelete('/project/milestones', id, () => showToast('已删除里程碑')); }'''
    ),
    (
        '''function deleteRisk(id) {
            fetch(`/project/risks/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除风险');
                loadProjectCenter();
            });
        }''',
        '''function deleteRisk(id) { crudDelete('/project/risks', id, () => showToast('已删除风险')); }'''
    ),
    (
        '''function deleteOpsCampaign(id) {
            fetch(`/ops/campaigns/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除活动');
                loadProjectCenter();
            });
        }''',
        '''function deleteOpsCampaign(id) { crudDelete('/ops/campaigns', id, () => showToast('已删除活动')); }'''
    ),
    (
        '''function deleteReleasePlan(id) {
            fetch(`/release/plans/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除发布计划');
                loadProjectCenter();
            });
        }''',
        '''function deleteReleasePlan(id) { crudDelete('/release/plans', id, () => showToast('已删除发布计划')); }'''
    ),
    (
        '''function deleteAlertRule(id) {
            fetch(`/alerts/rules/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除告警规则');
                loadProjectCenter();
            });
        }''',
        '''function deleteAlertRule(id) { crudDelete('/alerts/rules', id, () => showToast('已删除告警规则')); }'''
    ),
    (
        '''function deleteAb(id) {
            fetch(`/ab/experiments/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除AB实验');
                loadProjectCenter();
            });
        }''',
        '''function deleteAb(id) { crudDelete('/ab/experiments', id, () => showToast('已删除AB实验')); }'''
    ),
    (
        '''function deleteIntegration(id) {
            fetch(`/integrations/${id}`, {method: 'DELETE'}).then(r => r.json()).then(data => {
                if (!data.success) return showToast(data.error || '删除失败');
                showToast('已删除集成');
                loadProjectCenter();
            });
        }''',
        '''function deleteIntegration(id) { crudDelete('/integrations', id, () => showToast('已删除集成')); }'''
    ),
]

for old, new in delete_replacements:
    if old in content:
        content = content.replace(old, new, 1)
        fname = new.split('function ')[1].split('(')[0]
        changes.append(f"{fname}: 6行->1行 crudDelete")

# ============================================================
# 3. 后端: 为全局列表操作添加线程锁保护
# ============================================================
print("[3] 后端: 全局列表操作线程锁...")

# 为 project_artifacts.append 添加锁
old_append_artifact = 'project_artifacts.append(artifact)'
new_append_artifact = '''with data_lock:
            project_artifacts.append(artifact)'''
if old_append_artifact in content and content.count('with data_lock:') < 5:
    content = content.replace(old_append_artifact, new_append_artifact, 1)
    changes.append("project_artifacts.append 添加线程锁")

# 为 project_artifacts 列表推导添加锁
old_filter_artifact = 'project_artifacts = [a for a in project_artifacts if a.get(\'id\') != artifact_id]'
new_filter_artifact = '''with data_lock:
                project_artifacts = [a for a in project_artifacts if a.get('id') != artifact_id]'''
if old_filter_artifact in content:
    content = content.replace(old_filter_artifact, new_filter_artifact, 1)
    changes.append("project_artifacts 删除操作添加线程锁")

# ============================================================
# 4. 前端: 更多getElementById替换为$()
# ============================================================
print("[4] 前端: 更多DOM缓存优化...")

# toggleRag
old_toggle = "ragEnabled = document.getElementById('ragToggle').checked;"
new_toggle = "const ragToggle=$('ragToggle'); ragEnabled = ragToggle ? ragToggle.checked : false;"
if old_toggle in content:
    content = content.replace(old_toggle, new_toggle, 1)
    changes.append("toggleRag: getElementById->$()缓存")

# filterLogs
old_filter = "const level = document.getElementById('logLevelFilter').value;"
new_filter = "const logLevelFilter=$('logLevelFilter'); const level = logLevelFilter ? logLevelFilter.value : 'all';"
if old_filter in content:
    content = content.replace(old_filter, new_filter, 1)
    changes.append("filterLogs: getElementById->$()缓存")

# clearLogs
old_clear = "document.getElementById('logViewer').innerHTML"
new_clear = "const logViewer=$('logViewer'); if(logViewer) logViewer.innerHTML"
if old_clear in content:
    content = content.replace(old_clear, new_clear, 1)
    changes.append("clearLogs: getElementById->$()缓存")

# exportLogs
old_export = "const logs = document.getElementById('logViewer').innerText;"
new_export = "const logV=$('logViewer'); const logs = logV ? logV.innerText : '';"
if old_export in content:
    content = content.replace(old_export, new_export, 1)
    changes.append("exportLogs: getElementById->$()缓存")

# addLogEntry
old_addlog = "const viewer = document.getElementById('logViewer');"
new_addlog = "const viewer = $('logViewer');"
if old_addlog in content:
    content = content.replace(old_addlog, new_addlog, 1)
    changes.append("addLogEntry: getElementById->$()缓存")

# ============================================================
# 5. 前端: renderScheduledTasks 使用$()缓存
# ============================================================
print("[5] 前端: renderScheduledTasks DOM缓存...")

old_render_sched = "const el = document.getElementById('scheduledTasksList');"
new_render_sched = "const el = $('scheduledTasksList');"
if old_render_sched in content:
    content = content.replace(old_render_sched, new_render_sched, 1)
    changes.append("renderScheduledTasks: getElementById->$()缓存")

# ============================================================
# 6. 前端: renderServiceHealth 使用$()缓存
# ============================================================
print("[6] 前端: renderServiceHealth DOM缓存...")

old_service = "const el = document.getElementById('serviceHealthGrid');"
new_service = "const el = $('serviceHealthGrid');"
if old_service in content:
    content = content.replace(old_service, new_service, 1)
    changes.append("renderServiceHealth: getElementById->$()缓存")

# ============================================================
# 7. 前端: renderGitStatus 使用$()缓存
# ============================================================
print("[7] 前端: renderGitStatus DOM缓存...")

old_git = "const el = document.getElementById('gitStatusGrid');"
new_git = "const el = $('gitStatusGrid');"
if old_git in content:
    content = content.replace(old_git, new_git, 1)
    changes.append("renderGitStatus: getElementById->$()缓存")

# ============================================================
# 8. 前端: analyzeAllDependencies 使用$()缓存
# ============================================================
print("[8] 前端: analyzeAllDependencies DOM缓存...")

old_deps = '''document.getElementById('totalDeps').textContent = data.summary.total;
                        document.getElementById('outdatedDeps').textContent = data.summary.outdated;
                        document.getElementById('vulnerableDeps').textContent = data.summary.vulnerable;'''
new_deps = '''const td=$('totalDeps'),od=$('outdatedDeps'),vd=$('vulnerableDeps');
                        if(td)td.textContent=data.summary.total;if(od)od.textContent=data.summary.outdated;if(vd)vd.textContent=data.summary.vulnerable;'''
if old_deps in content:
    content = content.replace(old_deps, new_deps, 1)
    changes.append("analyzeAllDependencies: getElementById->$()缓存+null安全")

# ============================================================
# 9. 后端: 优化 access_logs 大小限制
# ============================================================
print("[9] 后端: access_logs大小限制...")

# 查找 access_logs 的写入位置并添加大小限制
old_log_append = 'access_logs.append'
if 'access_logs = access_logs[-' not in content:
    # 在 access_logs.append 后添加限制
    content = content.replace(
        'access_logs.append(log_entry)',
        'access_logs.append(log_entry)\n        if len(access_logs) > 500: access_logs = access_logs[-300:]',
        1
    )
    changes.append("access_logs 添加大小限制: 最多500条")

# ============================================================
# 10. 前端: 优化 sendMessage 中的 DOM 操作
# ============================================================
print("[10] 前端: sendMessage DOM优化...")

# 替换 sendMessage 中的 getElementById
old_send_msg_ids = [
    ("document.getElementById('mainInput')", "$('mainInput')"),
    ("document.getElementById('messagesContainer')", "$('messagesContainer')"),
    ("document.getElementById('stopBtn')", "$('stopBtn')"),
    ("document.getElementById('sendBtn')", "$('sendBtn')"),
]

# 只替换 sendMessage 函数内的
send_msg_start = content.find('function sendMessage(')
if send_msg_start > 0:
    # 找到 sendMessage 函数的结束位置（下一个顶层 function）
    after_send = content[send_msg_start:]
    # 找下一个顶层function
    next_func = re.search(r'\n        function ', after_send[10:])
    if next_func:
        send_msg_end = send_msg_start + 10 + next_func.start()
        send_msg_body = content[send_msg_start:send_msg_end]
        
        for old_id, new_id in old_send_msg_ids:
            count = send_msg_body.count(old_id)
            if count > 0:
                send_msg_body = send_msg_body.replace(old_id, new_id)
                changes.append(f"sendMessage: {count}x {old_id}->{new_id}")
        
        content = content[:send_msg_start] + send_msg_body + content[send_msg_end:]

# ============================================================
# 保存文件
# ============================================================
new_lines = content.split('\n')
print(f"\n优化后行数: {len(new_lines)}")
print(f"行数变化: {len(new_lines) - total_lines:+d}")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone! {FILE}")
print(f"\nTotal {len(changes)} optimizations:")
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
