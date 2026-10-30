# Go Backend as Primary Service

Go was chosen for its concurrency model, single-binary distribution, and strong typing. The Go backend is the primary HTTP server; Electron launches it directly. Python worker is only used for model inference.

## Status
Accepted

## Consequences
- All business logic lives in Go
- Electron no longer spawns Python Flask process
- Startup chain: Electron → Go backend → (optional) Python worker
