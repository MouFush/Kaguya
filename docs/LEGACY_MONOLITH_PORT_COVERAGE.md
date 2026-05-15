# Legacy Monolith Port Coverage

Updated: 2026-05-15

The former Python HTTP monolith has been physically removed from this repository. Its externally visible route surface is preserved as a generated Go contract in `desktop/resources/go-backend/route_contract_generated.go`.

## Current Gate Data

- Archived legacy route count: 241
- Go handler patterns: 155
- Covered routes: 241
- Missing routes: 0
- Coverage: 100%
- Go source line count: more than 30,000 lines, including generated route and symbol catalogs

## What This Means

This proves route-surface ownership by Go. It does not mean every historical behavior is fully reimplemented. Some deep capabilities intentionally return structured unavailable responses until dedicated Go services are implemented.

Examples of remaining compatibility areas:

- Advanced multimodal workers
- Fine-tuning workers
- Some workflow/MCP execution paths
- Some deployment integrations

## Validation Commands

```powershell
python desktop\resources\python-app\scripts\go_route_coverage.py --fail-under 100
C:\Users\Lanzao\Downloads\KaguyaIDE-3.1.0-win64-Desktop\.tools\go\bin\go.exe test ./...
python -m unittest discover -s desktop\resources\python-app\tests -v
node --check desktop\resources\app.asar.src\electron\main.js
node --check desktop\resources\app.asar.src\electron\preload.js
```

## Deletion Status

- Old Python HTTP monolith: deleted.
- Electron default backend: Go.
- Python worker mode: optional, via `start_server.py --backend bootstrap`.
- Route contract source: checked-in generated Go catalog.

