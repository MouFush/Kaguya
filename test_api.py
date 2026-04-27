import urllib.request
import json

endpoints = [
    ('/', '主页'),
    ('/api/roles', '角色列表'),
    ('/api/prompts', '模板列表'),
    ('/rag/stats', 'RAG 统计'),
    ('/rag/analysis', 'RAG 分析'),
    ('/console/overview', '控制台概览'),
    ('/console/recommendations', '控制台建议'),
    ('/system/metrics', '系统指标'),
    ('/performance/stats', '性能统计'),
    ('/services/health-check', '服务健康检查'),
    ('/dependencies/analyze', '依赖分析'),
    ('/git/status', 'Git 状态'),
    ('/scheduler/tasks', '定时任务'),
    ('/templates/analysis', '模板分析'),
    ('/dataflow/stats', '数据流统计'),
    ('/workflows', '工作流列表'),
    ('/memory/stats', '记忆统计'),
]

print('=' * 60)
print('辉夜项目前端 API 端点测试')
print('=' * 60)

success_count = 0
fail_count = 0

for endpoint, name in endpoints:
    try:
        url = 'http://127.0.0.1:5000' + endpoint
        r = urllib.request.urlopen(url, timeout=5)
        if endpoint == '/':
            print(f'[OK] {name} ({endpoint}) - 状态码: {r.status}')
        else:
            data = json.loads(r.read().decode('utf-8'))
            success_val = data.get('success', 'N/A')
            print(f'[OK] {name} ({endpoint}) - success: {success_val}')
        success_count += 1
    except Exception as e:
        error_msg = str(e)[:50]
        print(f'[FAIL] {name} ({endpoint}) - 错误: {error_msg}')
        fail_count += 1

print('=' * 60)
print(f'测试结果: 成功 {success_count}/{len(endpoints)}, 失败 {fail_count}/{len(endpoints)}')
print('=' * 60)
