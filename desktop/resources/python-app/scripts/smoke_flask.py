#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a local HTTP smoke check against the Go backend.

The old Flask monolith has been removed from the public tree. This script keeps
the historical filename because build automation calls it, but it now starts the
Go backend on 127.0.0.1 and validates the same minimum API surface.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
GO_DIR = os.path.join(ROOT_DIR, "resources", "go-backend")
GO_EXE = os.environ.get(
    "KAGUYA_GO_BACKEND",
    os.path.join(GO_DIR, "kaguya-go-backend.exe" if os.name == "nt" else "kaguya-go-backend"),
)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def request(method: str, port: int, path: str, payload: dict | None = None) -> tuple[int, str, str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, exc.headers.get("Content-Type", ""), body


def main() -> int:
    if not os.path.exists(GO_EXE):
        print(json.dumps({"success": False, "error": "go_backend_missing", "path": GO_EXE}, ensure_ascii=False))
        return 1
    port = free_port()
    runtime_dir = tempfile.mkdtemp(prefix="kaguya-go-smoke-")
    proc = subprocess.Popen(
        [
            GO_EXE,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--runtime-dir",
            runtime_dir,
            "--app-dir",
            APP_DIR,
            "--static-dir",
            os.path.join(GO_DIR, "static"),
        ],
        cwd=GO_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                status, _, _ = request("GET", port, "/health")
                if status < 500:
                    break
            except Exception:
                pass
            time.sleep(0.25)
        else:
            _, stderr = proc.communicate(timeout=1)
            print(json.dumps({"success": False, "error": "backend_start_timeout", "stderr": stderr[-2000:]}, ensure_ascii=False))
            return 1

        checks = [
            ("GET", "/", None, False),
            ("GET", "/static/agent_ide.html", None, False),
            ("GET", "/static/js/kaguya-api-client.js", None, False),
            ("GET", "/static/js/kaguya-agent.js", None, False),
            ("GET", "/static/js/kaguya-file-upload.js", None, False),
            ("GET", "/static/js/kaguya-stream.js", None, False),
            ("GET", "/static/js/kaguya-app-data.js", None, False),
            ("GET", "/static/js/kaguya-main.js", None, False),
            ("GET", "/static/js/kaguya-ui-utils.js", None, False),
            ("GET", "/static/js/kaguya-provider-config.js", None, False),
            ("GET", "/static/js/kaguya-scene-config.js", None, False),
            ("GET", "/static/css/kaguya-main.css", None, False),
            ("GET", "/header-img", None, False),
            ("GET", "/hero-img", None, False),
            ("GET", "/welcome-img", None, False),
            ("GET", "/sidebar-icon", None, False),
            ("GET", "/deepseek-icon", None, False),
            ("GET", "/favicon.ico", None, False),
            ("POST", "/chat", {"message": "hello", "history": []}, True),
            ("GET", "/agent/tasks", None, True),
            ("GET", "/rag/documents", None, True),
            ("GET", "/kaguya/features/flags", None, True),
            ("GET", "/permissions/status", None, True),
            ("GET", "/permissions/mode", None, True),
            ("POST", "/permissions/check", {"tool_name": "read_file", "tool_input": {"path": "README.md"}}, True),
            ("GET", "/api/model-status", None, True),
            ("GET", "/models", None, True),
            ("GET", "/api/config", None, True),
            ("POST", "/chat/completions", {"messages": [{"role": "user", "content": "hello"}]}, True),
        ]
        failures: list[str] = []
        for method, path, payload, expect_json in checks:
            status, content_type, body = request(method, port, path, payload)
            is_json = "application/json" in content_type
            print(json.dumps({"method": method, "path": path, "status": status, "json": is_json}, ensure_ascii=False))
            if status == 500:
                failures.append(f"{method} {path} returned 500")
            if status == 404:
                failures.append(f"{method} {path} returned 404")
            if expect_json and not is_json:
                failures.append(f"{method} {path} did not return JSON: {body[:120]}")
        if failures:
            print(json.dumps({"success": False, "failures": failures}, ensure_ascii=False))
            return 1
        print(json.dumps({"success": True}, ensure_ascii=False))
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
