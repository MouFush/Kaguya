# KaguyaIDE Agent Instructions

## Project Overview

KaguyaIDE is an Electron desktop IDE with a Go HTTP backend. The Python monolith has been retired; only ollama_adapter.py remains for model inference.

## Architecture

- Desktop Shell: Electron main process (resources/app.asar.src/electron/main.js)
- Go Backend: HTTP server on port 8766 (resources/go-backend/)
- Python Worker: Minimal Ollama adapter (resources/python-app/)
- Frontend: Static HTML/CSS/JS served by Go (resources/go-backend/static/)

## Key Conventions

- Go backend uses per-domain handler files (handler_*.go)
- Helper functions in domain files: vault.go, workspace.go, security.go, collection.go, http_helpers.go
- Frontend JS split into domain modules loaded via script tags in index.html
- All JS uses vanilla JS (no build system); global scope for shared state
- Device vault uses AES-256-GCM encryption (see vault.go)
- Workspace paths must pass safeJoin authorization check

## Build and Test

cd resources/go-backend
go build ./...
go test ./...
node --check resources/go-backend/static/js/*.js
node --check resources/app.asar.src/electron/main.js

## Domain Model

See CONTEXT.md for shared vocabulary. See docs/adr/ for architectural decisions.

## Non-Goals

- No Python Flask monolith (retired)
- No build system for frontend JS (vanilla JS only)
- No external database (local file storage)
