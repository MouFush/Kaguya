#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a minimal Flask test_client smoke check without starting a public server."""

import json
import os
import sys


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("KAGUYA_DESKTOP_MODE", "1")
os.environ.setdefault("KAGUYA_ELECTRON", "1")
os.environ.setdefault("KAGUYA_DISABLE_NGROK", "1")

import qwen3_web  # noqa: E402


def main():
    app = qwen3_web.app
    app.config["TESTING"] = True
    client = app.test_client()
    checks = [
        ("GET", "/", None),
        ("POST", "/chat", {"message": "hello", "history": []}),
        ("GET", "/agent/tasks", None),
        ("GET", "/rag/documents", None),
        ("GET", "/kaguya/features/flags", None),
        ("GET", "/permissions/status", None),
        ("GET", "/permissions/mode", None),
        ("POST", "/permissions/check", {"tool_name": "Read", "tool_input": {"path": "README.md"}}),
        ("GET", "/api/model-status", None),
        ("GET", "/models", None),
        ("GET", "/api/config", None),
        ("POST", "/chat/completions", {"messages": [{"role": "user", "content": "hello"}]}),
    ]
    failures = []
    for method, path, payload in checks:
        response = client.get(path) if method == "GET" else client.post(path, json=payload or {})
        is_json = response.is_json
        line = {"method": method, "path": path, "status": response.status_code, "json": is_json}
        print(json.dumps(line, ensure_ascii=False))
        if response.status_code == 500:
            failures.append(f"{method} {path} returned 500")
        if path != "/" and not is_json:
            failures.append(f"{method} {path} did not return JSON")
    if failures:
        print(json.dumps({"success": False, "failures": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"success": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
