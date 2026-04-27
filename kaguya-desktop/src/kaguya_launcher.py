#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辉夜IDE 桌面启动器 (简化版)
直接启动Flask服务器并在浏览器中打开
"""

import os
import sys
import threading
import time
import webbrowser
import subprocess
import signal

APP_NAME = "Kaguya IDE"
APP_VERSION = "3.1.0"
DEFAULT_PORT = 58000


def find_free_port():
    import socket
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except OSError:
            continue
    return DEFAULT_PORT


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main():
    import argparse

    parser = argparse.ArgumentParser(description=f"{APP_NAME} Desktop")
    parser.add_argument("--port", type=int, default=0, help="Server port (0=auto)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    port = args.port if args.port > 0 else find_free_port()
    app_dir = get_app_dir()

    print(f"{'=' * 50}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print(f"{'=' * 50}")
    print(f"  App Dir: {app_dir}")
    print(f"  Server: http://127.0.0.1:{port}")
    print(f"{'=' * 50}")

    sys.path.insert(0, app_dir)
    os.chdir(app_dir)

    try:
        from qwen3_web import app
    except ImportError as e:
        print(f"[ERROR] Failed to import Flask app: {e}")
        print(f"[INFO] sys.path: {sys.path[:3]}")
        input("Press Enter to exit...")
        sys.exit(1)

    def run_server():
        app.run(
            host="127.0.0.1",
            port=port,
            threaded=True,
            debug=args.debug,
            use_reloader=False,
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    for _ in range(50):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://127.0.0.1:{port}/")
            print(f"[OK] Server ready at http://127.0.0.1:{port}/")
            break
        except Exception:
            time.sleep(0.2)
    else:
        print("[WARN] Server may not be ready yet...")

    if not args.no_browser:
        print(f"[INFO] Opening browser...")
        webbrowser.open(f"http://127.0.0.1:{port}")

    print("")
    print("[INFO] Press Ctrl+C to stop the server")
    print("")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")


if __name__ == "__main__":
    main()
