#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kaguya IDE local server launcher."""

import argparse
import os
import runpy
import sys
import traceback


KAGUYA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KAGUYA_DIR)


def parse_args():
    parser = argparse.ArgumentParser(description="Start Kaguya IDE Flask backend")
    parser.add_argument("--port", type=int, default=int(os.environ.get("KAGUYA_PORT", 5000)))
    parser.add_argument("--host", default=os.environ.get("KAGUYA_HOST", "127.0.0.1"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--localhost-only", action="store_true")
    parser.add_argument("--backend", choices=("qwen3", "bootstrap"), default="qwen3")
    return parser.parse_args()


def run_qwen3(args):
    script = os.path.join(KAGUYA_DIR, "qwen3_web.py")
    if not os.path.exists(script):
        raise FileNotFoundError(f"qwen3_web.py not found at {script}")
    argv = ["qwen3_web.py", "--port", str(args.port), "--host", args.host]
    if args.localhost_only or args.host in ("127.0.0.1", "localhost"):
        argv.append("--localhost-only")
    if args.debug:
        os.environ["FLASK_DEBUG"] = "1"
    old_argv = sys.argv[:]
    try:
        sys.argv = argv
        runpy.run_path(script, run_name="__main__")
    finally:
        sys.argv = old_argv


def run_bootstrap(args):
    from kaguya_bootstrap import run_kaguya_server

    run_kaguya_server(host=args.host, port=args.port, debug=args.debug)


def main():
    args = parse_args()
    try:
        if args.backend == "bootstrap":
            run_bootstrap(args)
        else:
            run_qwen3(args)
    except Exception as exc:
        print(f"[STARTUP ERROR] Failed to start Kaguya backend: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
