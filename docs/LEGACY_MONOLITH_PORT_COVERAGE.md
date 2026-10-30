# Legacy Monolith To Go Port Coverage

更新时间：2026-05-15

这个文档只记录迁移事实，不宣称旧 Python 单体已经可以删除。

## 当前数据

- Legacy Flask route count: 241
- Go route handler patterns: 145
- Go route surface coverage: 241 / 241 = 100%
- Missing static Flask routes: 0
- Go source line count: > 30,000 after generated route and symbol catalogs

## 这代表什么

代表 Go 后端已经拥有旧 HTTP route surface 的入口映射和删除门禁契约。

不代表这些能力已经全部行为等价。以下能力仍有 structured unavailable 或 compatibility worker 路径：

- 深度 RAG 分析和索引构建
- Agent 真实工具循环
- workflow/MCP 执行
- 多模态、finetune、TTS
- 部分项目运行和部署能力

## 删除门禁

旧 Python 单体只能在这些条件都满足后删除：

1. `python resources\python-app\scripts\go_route_coverage.py --fail-under 100` 通过。
2. `go test ./...` 通过。
3. `python -m unittest discover -s resources\python-app\tests -v` 通过。
4. `node --check resources\app.asar.src\electron\main.js` 通过。
5. `node --check resources\app.asar.src\electron\preload.js` 通过。
6. 旧 symbol catalog 中的 high/critical symbol 都被 Go service 测试覆盖或明确退役。
7. Electron 默认启动 Go 后端，不再把旧 Python 单体作为主 HTTP 入口。

## 命名规则

新 Go 架构不再使用旧文件名作为模块名、变量名或服务名。

允许在迁移脚本中通过 `KAGUYA_LEGACY_MONOLITH` 指向旧文件；这只是过渡读取源，不是新架构命名。
