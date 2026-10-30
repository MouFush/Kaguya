# Python Monolith Retirement

The Python Flask monolith (qwen3_web.py, 31K lines) was replaced by the Go backend. Delete all Python files covered by Go services; retain only ollama_adapter.py and kaguya_core/ as a thin compatibility layer.

## Status
Accepted

## Consequences
- Removes ~50K lines of dead code
- Go backend becomes the sole business logic provider
- Python worker reduced to model inference only
