#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility launcher for the Go backend.

The legacy Flask monolith has been removed. This script exists only so old
shortcuts that call resources/python-app/start_server.py fail toward the new
backend instead of trying to resurrect removed Flask monolith.
"""

import argparse
import os
import subprocess
import sys


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
GO_BACKEND = os.path.join(ROOT_DIR, "resources", "go-backend", "kaguya-go-backend.exe")
GO_STATIC = os.path.join(ROOT_DIR, "resources", "go-backend", "static")


def parse_args():
    parser = argparse.ArgumentParser(description="Start Kaguya IDE Go backend")
    parser.add_argument("--port", type=int, default=int(os.environ.get("KAGUYA_PORT", 5000)))
    parser.add_argument("--host", default=os.environ.get("KAGUYA_HOST", "127.0.0.1"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--localhost-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(GO_BACKEND):
        print(f"[STARTUP ERROR] Go backend binary not found: {GO_BACKEND}", file=sys.stderr)
        print("Build it with: cd resources/go-backend && go build -o kaguya-go-backend.exe .", file=sys.stderr)
        return 1
    host = "127.0.0.1" if args.localhost_only else args.host
    cmd = [
        GO_BACKEND,
        "--host", host,
        "--port", str(args.port),
        "--runtime-dir", os.path.join(os.environ.get("APPDATA", ROOT_DIR), "KaguyaIDE", "go-backend"),
        "--app-dir", APP_DIR,
        "--static-dir", GO_STATIC,
    ]
    if args.debug:
        print("[STARTUP] " + " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())

