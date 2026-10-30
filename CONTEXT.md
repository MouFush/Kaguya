# KaguyaIDE Domain Model

Shared vocabulary for KaguyaIDE's architecture. Use these terms consistently across code, docs, and PRs.

## Architecture

**Desktop Shell**: Electron main process handling window management, device vault, auto-update, and process orchestration.
_Avoid_: main process, bootstrap, launcher

**Go Backend**: Primary HTTP server providing all business APIs on port 8766.
_Avoid_: server, API layer, backend service

**Python Worker**: Minimal compatibility layer retaining only the Ollama adapter for model inference.
_Avoid_: legacy backend, old server

**Device Vault**: AES-256-GCM encrypted local device configuration storing API keys and provider config.
_Avoid_: config store, credentials, secrets

**Workspace**: User project directory protected by path authorization and permission checks.
_Avoid_: project dir, working dir, folder

**Agent Run**: Single AI agent execution instance with run ID, abort control, and SSE stream.
_Avoid_: task, job, execution

**Provider**: OpenAI-compatible API provider (Kimi, DeepSeek, OpenAI, etc.).
_Avoid_: model, API, service

## Migration Gates

**Route Contract**: Catalog of legacy HTTP routes tracked for deletion gate.
_Avoid_: route list, API catalog

**Symbol Catalog**: Catalog of legacy Python symbols tracked for deletion gate.
_Avoid_: symbol list, function catalog

**Legacy Contract**: Combined route + symbol catalogs that gate deletion of retired code.
_Avoid_: migration tracker, safety check

## Backend Services

**Auth Service**: Local desktop accounts, sessions, tokens.
_Avoid_: user manager, login system

**Provider Chat**: OpenAI-compatible provider client for chat completions.
_Avoid_: API client, model proxy

**Agent Runtime**: Agent run registry with abort and SSE frame management.
_Avoid_: agent manager, run tracker

**Workspace Project**: Workspace path authorization and file operations.
_Avoid_: file manager, project service

**Terminal Permission**: Command risk classification and permission decisions.
_Avoid_: command filter, security check

**Knowledge RAG**: Local KB/RAG document library.
_Avoid_: document store, knowledge base

**Security Privacy**: Loopback policy and privacy settings.
_Avoid_: privacy manager, security config
