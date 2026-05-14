#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke test the compiled Go backend without using removed Flask monolith."""

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
GO_EXE = os.path.join(GO_DIR, "kaguya-go-backend.exe")


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def request(method, url, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
        return resp.status, ctype, body


def main():
    if not os.path.exists(GO_EXE):
        print(json.dumps({"success": False, "error": "go_backend_exe_missing", "path": GO_EXE}))
        return 1
    port = free_port()
    runtime_dir = tempfile.mkdtemp(prefix="kaguya-go-smoke-")
    proc = subprocess.Popen([
        GO_EXE,
        "--host", "127.0.0.1",
        "--port", str(port),
        "--runtime-dir", runtime_dir,
        "--app-dir", APP_DIR,
        "--static-dir", os.path.join(GO_DIR, "static"),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                request("GET", base + "/health")
                break
            except Exception:
                time.sleep(0.1)
        checks = [
            ("GET", "/", None, False),
            ("GET", "/health", None, True),
            ("GET", "/api/model-status", None, True),
            ("GET", "/api/device/info", None, True),
            ("POST", "/permissions/check", {"tool_name": "read_file"}, True),
            ("GET", "/security/status", None, True),
            ("POST", "/agent/run", {"message": "hello"}, False),
        ]
        results = []
        for method, path, payload, expect_json in checks:
            status, ctype, body = request(method, base + path, payload)
            ok = status < 500 and (not expect_json or "application/json" in ctype)
            results.append({"method": method, "path": path, "status": status, "content_type": ctype, "ok": ok})
        success = all(item["ok"] for item in results)
        print(json.dumps({"success": success, "results": results}, ensure_ascii=False))
        return 0 if success else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())

