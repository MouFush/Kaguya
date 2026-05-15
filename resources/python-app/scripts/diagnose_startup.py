#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print startup diagnostics for the Go backend package."""

import json
import os
import sys


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))


def file_state(path):
    return {"path": path, "exists": os.path.exists(path), "size": os.path.getsize(path) if os.path.exists(path) else 0}


def main():
    go_dir = os.path.join(ROOT_DIR, "resources", "go-backend")
    go_exe = os.path.join(go_dir, "kaguya-go-backend.exe")
    electron_main = os.path.join(ROOT_DIR, "resources", "app.asar.src", "electron", "main.js")
    electron_preload = os.path.join(ROOT_DIR, "resources", "app.asar.src", "electron", "preload.js")
    info = {
        "python": sys.executable,
        "cwd": os.getcwd(),
        "app_dir": APP_DIR,
        "go_backend_dir": go_dir,
        "files": {
            "go_backend_exe": file_state(go_exe),
            "go_backend_static_index": file_state(os.path.join(go_dir, "static", "index.html")),
            "electron_main": file_state(electron_main),
            "electron_preload": file_state(electron_preload),
            "python_worker_adapter": file_state(os.path.join(APP_DIR, "kaguya_worker_adapter.py")),
        },
        "env": {
            "KAGUYA_DESKTOP_MODE": os.environ.get("KAGUYA_DESKTOP_MODE", ""),
            "KAGUYA_ELECTRON": os.environ.get("KAGUYA_ELECTRON", ""),
            "KAGUYA_GO_BACKEND": os.environ.get("KAGUYA_GO_BACKEND", ""),
        },
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
