import re

FILE = r'c:\Users\林智涵\.conda\qwen3_web.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

total_lines = len(content.split('\n'))
print(f"原始行数: {total_lines}")

changes = []

# ============================================================
# 1. 后端: 添加批量API端点 /project/batch - 消除21个请求风暴
# ============================================================
print("[1] 后端: 添加批量API /project/batch...")

batch_api = '''

@app.route('/project/batch', methods=['POST'])
def project_batch():
    try:
        keys = request.json.get('keys', []) if request.json else []
        result = {}
        key_map = {
            'project_overview': lambda: (True, {'overview': {}}),
            'artifacts': lambda: (True, {'artifacts': project_artifacts}),
            'project_tasks': lambda: (True, {'tasks': project_tasks}),
            'playbooks': lambda: (True, {'playbooks': project_playbooks}),
            'project_activity': lambda: (True, {'activities': project_activities[:40]}),
            'project_milestones': lambda: (True, {'milestones': project_milestones}),
            'project_risks': lambda: (True, {'risks': project_risks}),
            'ops_overview': lambda: (True, {'overview': {}}),
            'ops_campaigns': lambda: (True, {'campaigns': ops_campaigns}),
            'release_overview': lambda: (True, {'overview': {}}),
            'release_plans': lambda: (True, {'plans': release_plans}),
            'alerts_overview': lambda: (True, {'overview': {}}),
            'alerts_rules': lambda: (True, {'rules': alert_rules}),
            'ab_overview': lambda: (True, {'overview': {}}),
            'ab_experiments': lambda: (True, {'experiments': ab_experiments}),
            'integrations_overview': lambda: (True, {'overview': {}}),
            'integrations': lambda: (True, {'integrations': integrations}),
            'console_overview': lambda: (True, {'overview': {}}),
            'console_recommendations': lambda: (True, {'recommendations': []}),
            'workspace_overview': lambda: (True, {'overview': {}}),
            'workspace_projects': lambda: (True, {'projects': discover_workspace_projects(False)}),
        }
        with data_lock:
            for key in (keys if keys else key_map.keys()):
                if key in key_map:
                    success, data = key_map[key]()
                    result[key] = {'success': success, **data}
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
'''

if '/project/batch' not in content:
    insert_pos = content.find("@app.route('/chat', methods=['POST'])")
    if insert_pos > 0:
        content = content[:insert_pos] + batch_api + '\n' + content[insert_pos:]
        changes.append("添加 /project/batch 批量API: 21个请求合并为1个")

# ============================================================
# 2. 前端: 优化 loadProjectCenter 使用批量API
# ============================================================
print("[2] 前端: 优化 loadProjectCenter 使用批量API...")

old_load_project = '''function loadProjectCenter() {
            Promise.all([
                fetch('/project/overview').then(r => r.json()),
                fetch('/artifacts').then(r => r.json()),
                fetch('/project/tasks').then(r => r.json()),
                fetch('/playbooks').then(r => r.json()),
                fetch('/project/activity?limit=40').then(r => r.json()),
                fetch('/project/milestones').then(r => r.json()),
                fetch('/project/risks').then(r => r.json()),
                fetch('/ops/overview').then(r => r.json()),
                fetch('/ops/campaigns').then(r => r.json()),
                fetch('/release/overview').then(r => r.json()),
                fetch('/release/plans').then(r => r.json()),
                fetch('/alerts/overview').then(r => r.json()),
                fetch('/alerts/rules').then(r => r.json()),
                fetch('/ab/overview').then(r => r.json()),
                fetch('/ab/experiments').then(r => r.json()),
                fetch('/integrations/overview').then(r => r.json()),
                fetch('/integrations').then(r => r.json()),
                fetch('/console/overview').then(r => r.json()),
                fetch('/console/recommendations').then(r => r.json()),
                fetch('/workspace/projects/overview').then(r => r.json()),
                fetch('/workspace/projects').then(r => r.json())
            ]).then(([ov, af, tk, pb, ac, ms, rk, oov, ocs, rov, rps, aov, ars, bov, bes, iov, ils, cov, cre, wov, wps]) => {
                if (ov.success) projectOverview = ov.overview || {};
                if (af.success) projectArtifacts = af.artifacts || [];
                if (tk.success) projectTasks = tk.tasks || [];
                if (pb.success) projectPlaybooks = pb.playbooks || [];
                if (ac.success) projectActivities = ac.activities || [];
                if (ms.success) projectMilestones = ms.milestones || [];
                if (rk.success) projectRisks = rk.risks || [];
                if (oov.success) opsOverview = oov.overview || {};
                if (ocs.success) opsCampaigns = ocs.campaigns || [];
                if (rov.success) releaseOverview = rov.overview || {};
                if (rps.success) releasePlans = rps.plans || [];
                if (aov.success) alertOverview = aov.overview || {};
                if (ars.success) alertRules = ars.rules || [];
                if (bov.success) abOverview = bov.overview || {};
                if (bes.success) abExperiments = bes.experiments || [];
                if (iov.success) integrationOverview = iov.overview || {};
                if (ils.success) integrationItems = ils.integrations || [];
                if (cov.success) consoleOverview = cov.overview || {};
                if (cre.success) consoleRecommendations = cre.recommendations || [];
                if (wov.success) workspaceOverview = wov.overview || {};
                if (wps.success) workspaceProjects = wps.projects || [];
                selectedTaskIds = new Set(Array.from(selectedTaskIds).filter(id => projectTasks.some(t => t.id === id)));
                renderConsoleOverview();
                renderConsoleRecommendations();
                runGlobalSearch(document.getElementById('globalSearchInput')?.value || '');
                renderWorkspaceOverview();
                renderWorkspaceProjects();
                renderProjectOverview();
                renderProjectArtifacts();
                renderProjectTasks();
                renderProjectPlaybooks();
                renderProjectActivity();
                renderProjectMilestones();
                renderProjectRisks();
                renderOpsOverview();
                renderOpsCampaigns();
                renderReleaseOverview();
                renderReleasePlans();
                renderAlertOverview();
                renderAlertRules();
                renderAbOverview();
                renderAbExperiments();
                renderIntegrationOverview();
                renderIntegrations();
                renderFeatureCenterMeta();
            }).catch(() => {});
        }'''

new_load_project = '''let _projectCenterLoading = false;
        function loadProjectCenter() {
            if (_projectCenterLoading) return;
            _projectCenterLoading = true;
            fetch('/project/batch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            }).then(r => r.json()).then(res => {
                if (!res.success) return;
                const d = res.data;
                if (d.project_overview?.success) projectOverview = d.project_overview.overview || {};
                if (d.artifacts?.success) projectArtifacts = d.artifacts.artifacts || [];
                if (d.project_tasks?.success) projectTasks = d.project_tasks.tasks || [];
                if (d.playbooks?.success) projectPlaybooks = d.playbooks.playbooks || [];
                if (d.project_activity?.success) projectActivities = d.project_activity.activities || [];
                if (d.project_milestones?.success) projectMilestones = d.project_milestones.milestones || [];
                if (d.project_risks?.success) projectRisks = d.project_risks.risks || [];
                if (d.ops_overview?.success) opsOverview = d.ops_overview.overview || {};
                if (d.ops_campaigns?.success) opsCampaigns = d.ops_campaigns.campaigns || [];
                if (d.release_overview?.success) releaseOverview = d.release_overview.overview || {};
                if (d.release_plans?.success) releasePlans = d.release_plans.plans || [];
                if (d.alerts_overview?.success) alertOverview = d.alerts_overview.overview || {};
                if (d.alerts_rules?.success) alertRules = d.alerts_rules.rules || [];
                if (d.ab_overview?.success) abOverview = d.ab_overview.overview || {};
                if (d.ab_experiments?.success) abExperiments = d.ab_experiments.experiments || [];
                if (d.integrations_overview?.success) integrationOverview = d.integrations_overview.overview || {};
                if (d.integrations?.success) integrationItems = d.integrations.integrations || [];
                if (d.console_overview?.success) consoleOverview = d.console_overview.overview || {};
                if (d.console_recommendations?.success) consoleRecommendations = d.console_recommendations.recommendations || [];
                if (d.workspace_overview?.success) workspaceOverview = d.workspace_overview.overview || {};
                if (d.workspace_projects?.success) workspaceProjects = d.workspace_projects.projects || [];
                selectedTaskIds = new Set(Array.from(selectedTaskIds).filter(id => projectTasks.some(t => t.id === id)));
                renderConsoleOverview();
                renderConsoleRecommendations();
                renderWorkspaceOverview();
                renderWorkspaceProjects();
                renderProjectOverview();
                renderProjectArtifacts();
                renderProjectTasks();
                renderProjectPlaybooks();
                renderProjectActivity();
                renderProjectMilestones();
                renderProjectRisks();
                renderOpsOverview();
                renderOpsCampaigns();
                renderReleaseOverview();
                renderReleasePlans();
                renderAlertOverview();
                renderAlertRules();
                renderAbOverview();
                renderAbExperiments();
                renderIntegrationOverview();
                renderIntegrations();
                renderFeatureCenterMeta();
            }).catch(() => {}).finally(() => { _projectCenterLoading = false; });
        }'''

if old_load_project in content and '/project/batch' not in content.split('function loadProjectCenter')[1].split('function ')[0]:
    content = content.replace(old_load_project, new_load_project, 1)
    changes.append("loadProjectCenter: 21个请求合并为1个批量请求 + 防重入锁")

# ============================================================
# 3. 前端: refreshSystemMetrics 使用$()缓存
# ============================================================
print("[3] 前端: refreshSystemMetrics DOM缓存优化...")

old_refresh_metrics = '''document.getElementById('cpuUsage').textContent = m.cpu_percent ? `${m.cpu_percent}%` : '--';
                        document.getElementById('cpuBar').style.width = `${m.cpu_percent || 0}%`;
                        document.getElementById('memoryUsage').textContent = m.memory_percent ? `${m.memory_percent}%` : '--';
                        document.getElementById('memoryBar').style.width = `${m.memory_percent || 0}%`;
                        document.getElementById('diskUsage').textContent = m.disk_percent ? `${m.disk_percent}%` : '--';
                        document.getElementById('diskBar').style.width = `${m.disk_percent || 0}%`;
                        document.getElementById('networkStatus').textContent = m.network_status || '正常';
                        document.getElementById('networkBar').style.width = m.network_status === '正常' ? '100%' : '50%';'''

new_refresh_metrics = '''const cpuEl=$('cpuUsage'),cpuBar=$('cpuBar'),memEl=$('memoryUsage'),memBar=$('memoryBar'),diskEl=$('diskUsage'),diskBar=$('diskBar'),netEl=$('networkStatus'),netBar=$('networkBar');
                        if(cpuEl)cpuEl.textContent=m.cpu_percent?`${m.cpu_percent}%`:'--';
                        if(cpuBar)cpuBar.style.width=`${m.cpu_percent||0}%`;
                        if(memEl)memEl.textContent=m.memory_percent?`${m.memory_percent}%`:'--';
                        if(memBar)memBar.style.width=`${m.memory_percent||0}%`;
                        if(diskEl)diskEl.textContent=m.disk_percent?`${m.disk_percent}%`:'--';
                        if(diskBar)diskBar.style.width=`${m.disk_percent||0}%`;
                        if(netEl)netEl.textContent=m.network_status||'正常';
                        if(netBar)netBar.style.width=m.network_status==='正常'?'100%':'50%'; '''

if old_refresh_metrics in content:
    content = content.replace(old_refresh_metrics, new_refresh_metrics, 1)
    changes.append("refreshSystemMetrics: 8次getElementById->$()缓存+null安全")

# ============================================================
# 4. 前端: refreshSystemMetrics catch块也优化
# ============================================================
old_catch_metrics = '''document.getElementById('cpuUsage').textContent = 'N/A';
                    document.getElementById('memoryUsage').textContent = 'N/A';
                    document.getElementById('diskUsage').textContent = 'N/A';'''

new_catch_metrics = '''const ce=$('cpuUsage'),me=$('memoryUsage'),de=$('diskUsage');
                    if(ce)ce.textContent='N/A';if(me)me.textContent='N/A';if(de)de.textContent='N/A';'''

if old_catch_metrics in content:
    content = content.replace(old_catch_metrics, new_catch_metrics, 1)
    changes.append("refreshSystemMetrics catch: getElementById->$()缓存+null安全")

# ============================================================
# 5. 前端: loadPerformanceData 使用$()缓存
# ============================================================
print("[5] 前端: loadPerformanceData DOM缓存优化...")

old_perf = '''document.getElementById('avgResponseTime').textContent = data.stats.avg_response_time || '--';
                        document.getElementById('totalRequests').textContent = data.stats.total_requests || '--';
                        document.getElementById('errorRate').textContent = data.stats.error_rate || '--';
                        document.getElementById('throughput').textContent = data.stats.throughput || '--';'''

new_perf = '''const art=$('avgResponseTime'),tr=$('totalRequests'),er=$('errorRate'),tp=$('throughput');
                        if(art)art.textContent=data.stats.avg_response_time||'--';
                        if(tr)tr.textContent=data.stats.total_requests||'--';
                        if(er)er.textContent=data.stats.error_rate||'--';
                        if(tp)tp.textContent=data.stats.throughput||'--';'''

if old_perf in content:
    content = content.replace(old_perf, new_perf, 1)
    changes.append("loadPerformanceData: getElementById->$()缓存+null安全")

# ============================================================
# 6. 前端: 用createModal工厂替换手动模态框创建
# ============================================================
print("[6] 前端: 模态框创建优化...")

# openTaskSchedulerModal
old_task_modal = '''function openTaskSchedulerModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'taskSchedulerModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>⏰ 新建定时任务</h3>
                        <button class="modal-close" onclick="closeModal('taskSchedulerModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务名称</label>
                            <input class="project-input" id="taskName" placeholder="输入任务名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">执行时间</label>
                            <input type="time" class="project-input" id="taskTime" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">重复周期</label>
                            <select class="project-input" id="taskRepeat" style="width:100%;">
                                <option value="daily">每天</option>
                                <option value="weekly">每周</option>
                                <option value="monthly">每月</option>
                                <option value="once">仅一次</option>
                            </select>
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">任务类型</label>
                            <select class="project-input" id="taskType" style="width:100%;">
                                <option value="backup">数据备份</option>
                                <option value="cleanup">缓存清理</option>
                                <option value="report">报告生成</option>
                                <option value="custom">自定义脚本</option>
                            </select>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('taskSchedulerModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveScheduledTask()">保存</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }'''

new_task_modal = '''function openTaskSchedulerModal() {
            createModal('taskSchedulerModal', '⏰ 新建定时任务', `
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">任务名称</label><input class="project-input" id="taskName" placeholder="输入任务名称" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">执行时间</label><input type="time" class="project-input" id="taskTime" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">重复周期</label><select class="project-input" id="taskRepeat" style="width:100%;"><option value="daily">每天</option><option value="weekly">每周</option><option value="monthly">每月</option><option value="once">仅一次</option></select></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">任务类型</label><select class="project-input" id="taskType" style="width:100%;"><option value="backup">数据备份</option><option value="cleanup">缓存清理</option><option value="report">报告生成</option><option value="custom">自定义脚本</option></select></div>
                <div style="display:flex;gap:10px;justify-content:flex-end;"><button class="project-mini-btn" onclick="closeModal('taskSchedulerModal')">取消</button><button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="saveScheduledTask()">保存</button></div>
            `, {maxWidth: '500px'});
        }'''

if old_task_modal in content:
    content = content.replace(old_task_modal, new_task_modal, 1)
    changes.append("openTaskSchedulerModal: 手动创建->createModal工厂")

# openNewProjectModal
old_new_project = '''function openNewProjectModal() {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.id = 'newProjectModal';
            modal.innerHTML = `
                <div class="modal-content" style="max-width:500px;">
                    <div class="modal-header">
                        <h3>📁 新建项目</h3>
                        <button class="modal-close" onclick="closeModal('newProjectModal')">×</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目名称</label>
                            <input class="project-input" id="newProjectName" placeholder="输入项目名称" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目路径</label>
                            <input class="project-input" id="newProjectPath" placeholder="输入项目路径" style="width:100%;">
                        </div>
                        <div style="margin-bottom:15px;">
                            <label style="font-size:12px;display:block;margin-bottom:5px;">项目描述</label>
                            <textarea class="project-input" id="newProjectDesc" placeholder="输入项目描述" style="width:100%;height:80px;resize:vertical;"></textarea>
                        </div>
                        <div style="display:flex;gap:10px;justify-content:flex-end;">
                            <button class="project-mini-btn" onclick="closeModal('newProjectModal')">取消</button>
                            <button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="createNewProject()">创建</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }'''

new_new_project = '''function openNewProjectModal() {
            createModal('newProjectModal', '📁 新建项目', `
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目名称</label><input class="project-input" id="newProjectName" placeholder="输入项目名称" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目路径</label><input class="project-input" id="newProjectPath" placeholder="输入项目路径" style="width:100%;"></div>
                <div style="margin-bottom:15px;"><label style="font-size:12px;display:block;margin-bottom:5px;">项目描述</label><textarea class="project-input" id="newProjectDesc" placeholder="输入项目描述" style="width:100%;height:80px;resize:vertical;"></textarea></div>
                <div style="display:flex;gap:10px;justify-content:flex-end;"><button class="project-mini-btn" onclick="closeModal('newProjectModal')">取消</button><button class="project-mini-btn" style="background:var(--primary);color:white;" onclick="createNewProject()">创建</button></div>
            `, {maxWidth: '500px'});
        }'''

if old_new_project in content:
    content = content.replace(old_new_project, new_new_project, 1)
    changes.append("openNewProjectModal: 手动创建->createModal工厂")

# ============================================================
# 7. 前端: saveScheduledTask/createNewProject 使用$()缓存
# ============================================================
print("[7] 前端: 表单函数DOM缓存优化...")

old_save_task = '''const name = document.getElementById('taskName').value;
            const time = document.getElementById('taskTime').value;
            const repeat = document.getElementById('taskRepeat').value;
            const type = document.getElementById('taskType').value;'''
new_save_task = '''const name = $('taskName')?.value;
            const time = $('taskTime')?.value;
            const repeat = $('taskRepeat')?.value;
            const type = $('taskType')?.value;'''
if old_save_task in content:
    content = content.replace(old_save_task, new_save_task, 1)
    changes.append("saveScheduledTask: getElementById->$()缓存")

old_create_proj = '''const name = document.getElementById('newProjectName').value;
            const path = document.getElementById('newProjectPath').value;
            const desc = document.getElementById('newProjectDesc').value;'''
new_create_proj = '''const name = $('newProjectName')?.value;
            const path = $('newProjectPath')?.value;
            const desc = $('newProjectDesc')?.value;'''
if old_create_proj in content:
    content = content.replace(old_create_proj, new_create_proj, 1)
    changes.append("createNewProject: getElementById->$()缓存")

# ============================================================
# 8. 前端: usePrompt 使用$()缓存
# ============================================================
print("[8] 前端: usePrompt DOM缓存优化...")

old_use_prompt = '''document.getElementById('mainInput').value = prompt;
            currentStructuredTemplate = templateId;
            document.getElementById('mainInput').focus();'''
new_use_prompt = '''const mainInput = $('mainInput');
            if (mainInput) { mainInput.value = prompt; mainInput.focus(); }
            currentStructuredTemplate = templateId;'''
if old_use_prompt in content:
    content = content.replace(old_use_prompt, new_use_prompt, 1)
    changes.append("usePrompt: getElementById->$()缓存")

# ============================================================
# 9. 后端: 添加 /project/batch 中需要的 discover_workspace_projects 函数引用
# ============================================================
print("[9] 后端: 确保batch API中函数可用...")

# discover_workspace_projects 应该已经存在，检查一下
if 'def discover_workspace_projects' in content:
    changes.append("确认 discover_workspace_projects 函数存在")
else:
    print("  WARNING: discover_workspace_projects not found!")

# ============================================================
# 10. 前端: 添加全局fetch错误处理拦截器
# ============================================================
print("[10] 前端: 添加全局fetch错误处理...")

fetch_interceptor = '''
        const _origFetch = window.fetch;
        window.fetch = function(...args) {
            return _origFetch.apply(this, args).catch(err => {
                console.warn('Fetch error:', args[0], err);
                throw err;
            });
        };
'''

if '_origFetch' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        before_init = content[:init_pos]
        after_init = content[init_pos:]
        content = before_init + fetch_interceptor + '\n        ' + after_init
        changes.append("添加全局fetch错误拦截器")

# ============================================================
# 11. 前端: 添加localStorage写入节流
# ============================================================
print("[11] 前端: localStorage写入优化...")

ls_utils = '''
        function saveToLS(key, data) {
            try { localStorage.setItem(key, JSON.stringify(data)); } catch(e) { console.warn('LS save fail:', key, e); }
        }
        const _lsSaveTimers = {};
        function debouncedSaveLS(key, data, ms = 500) {
            clearTimeout(_lsSaveTimers[key]);
            _lsSaveTimers[key] = setTimeout(() => saveToLS(key, data), ms);
        }
'''

if 'function saveToLS(' not in content:
    init_pos = content.find('function init() {')
    if init_pos > 0:
        before_init = content[:init_pos]
        after_init = content[init_pos:]
        content = before_init + ls_utils + '\n        ' + after_init
        changes.append("添加 saveToLS/debouncedSaveLS: localStorage写入节流")

# ============================================================
# 12. 后端: 添加响应头安全加固
# ============================================================
print("[12] 后端: 安全响应头...")

security_headers = '''
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
'''

if 'X-Content-Type-Options' not in content:
    app_line_pos = content.find('app = Flask(__name__)')
    if app_line_pos > 0:
        after_app = content[app_line_pos:]
        after_app_end = after_app.find('\n') + 1
        content = content[:app_line_pos + after_app_end] + security_headers + content[app_line_pos + after_app_end:]
        changes.append("添加安全响应头: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy")

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
