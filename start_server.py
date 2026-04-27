#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 启动脚本
用法: python start_server.py [--port 5000] [--host 127.0.0.1] [--debug]
"""

import os
import sys

KAGUYA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KAGUYA_DIR)

def main():
    try:
        from kaguya_bootstrap import run_kaguya_server
        run_kaguya_server()
    except ImportError as e:
        print(f"[ERROR] Cannot import kaguya_bootstrap: {e}")
        print("\nFalling back to qwen3_web.py direct launch...")
        try:
            import importlib
            spec = importlib.util.spec_from_file_location("qwen3_web",
                os.path.join(KAGUYA_DIR, "qwen3_web.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            print("[WARN] Running in legacy mode (no ACP/Agents/Skills/Accounts)")
        except Exception as e2:
            print(f"[ERROR] Fallback failed: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
