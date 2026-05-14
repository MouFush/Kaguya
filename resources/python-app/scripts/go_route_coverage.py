#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare legacy Flask routes with Go backend handlers.

This is a migration gate, not a smoke test. Deleting the legacy monolith is
allowed only after Go owns the same externally visible route surface or each
gap has an explicit migration note.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
QWEN_FILE = os.path.join(APP_DIR, "qwen3_web.py")
GO_SERVER = os.path.join(ROOT_DIR, "resources", "go-backend", "server.go")


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def flask_routes() -> set[str]:
    if not os.path.exists(QWEN_FILE):
        return set()
    text = read(QWEN_FILE)
    return set(re.findall(r"@app\.route\(\s*['\"]([^'\"]+)['\"]", text))


def go_routes() -> set[str]:
    if not os.path.exists(GO_SERVER):
        return set()
    text = read(GO_SERVER)
    return set(re.findall(r"mux\.HandleFunc\(\s*['\"]([^'\"]+)['\"]", text))


def route_covered(route: str, go: set[str]) -> bool:
    if route in go:
        return True
    for prefix in go:
        if prefix == "/":
            continue
        if prefix.endswith("/") and route.startswith(prefix):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-under", type=float, default=100.0, help="minimum coverage percentage")
    args = parser.parse_args()
    legacy = flask_routes()
    go = go_routes()
    missing = sorted(route for route in legacy if not route_covered(route, go))
    covered = len(legacy) - len(missing)
    percent = 100.0 if not legacy else round(covered * 100.0 / len(legacy), 2)
    payload = {
        "success": percent >= args.fail_under,
        "legacy_route_count": len(legacy),
        "go_handler_count": len(go),
        "covered_count": covered,
        "missing_count": len(missing),
        "coverage_percent": percent,
        "missing_sample": missing[:80],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
