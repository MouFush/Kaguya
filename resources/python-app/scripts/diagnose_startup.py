#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print backend startup diagnostics without claiming the app is healthy."""

import importlib.util
import json
import os
import sys


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))


def file_state(path):
    return {"path": path, "exists": os.path.exists(path), "size": os.path.getsize(path) if os.path.exists(path) else 0}


def main():
    qwen = os.path.join(APP_DIR, "qwen3_web.py")
    bootstrap = os.path.join(APP_DIR, "kaguya_bootstrap.py")
    permissions = os.path.join(APP_DIR, "kaguya_permissions.py")
    electron_main = os.path.join(ROOT_DIR, "resources", "app.asar.src", "electron", "main.js")
    electron_preload = os.path.join(ROOT_DIR, "resources", "app.asar.src", "electron", "preload.js")
    info = {
        "python": sys.executable,
        "cwd": os.getcwd(),
        "app_dir": APP_DIR,
        "files": {
            "qwen3_web": file_state(qwen),
            "kaguya_bootstrap": file_state(bootstrap),
            "kaguya_permissions": file_state(permissions),
            "electron_main": file_state(electron_main),
            "electron_preload": file_state(electron_preload),
        },
        "optional_modules": {
            "flask": importlib.util.find_spec("flask") is not None,
            "ollama": importlib.util.find_spec("ollama") is not None,
            "torch": importlib.util.find_spec("torch") is not None,
            "transformers": importlib.util.find_spec("transformers") is not None,
            "peft": importlib.util.find_spec("peft") is not None,
        },
        "env": {
            "KAGUYA_DESKTOP_MODE": os.environ.get("KAGUYA_DESKTOP_MODE", ""),
            "KAGUYA_ELECTRON": os.environ.get("KAGUYA_ELECTRON", ""),
            "KAGUYA_NGROK_TOKEN": "set" if os.environ.get("KAGUYA_NGROK_TOKEN") else "unset",
        },
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
