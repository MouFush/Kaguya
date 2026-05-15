#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kaguya IDE local server launcher."""

import argparse
import os
import sys
import traceback


KAGUYA_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KAGUYA_DIR)


def parse_args():
    parser = argparse.ArgumentParser(description="Start Kaguya IDE Python compatibility worker")
    parser.add_argument("--port", type=int, default=int(os.environ.get("KAGUYA_PORT", 5000)))
    parser.add_argument("--host", default=os.environ.get("KAGUYA_HOST", "127.0.0.1"))
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--localhost-only", action="store_true")
    parser.add_argument("--backend", choices=("bootstrap",), default="bootstrap")
    return parser.parse_args()


def run_bootstrap(args):
    from kaguya_bootstrap import run_kaguya_server

    run_kaguya_server(host=args.host, port=args.port, debug=args.debug)


def main():
    args = parse_args()
    try:
        run_bootstrap(args)
    except Exception as exc:
        print(f"[STARTUP ERROR] Failed to start Kaguya backend: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
