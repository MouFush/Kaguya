import os
import re
import sys
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))


def find_project_file(*names):
    candidates = [
        os.path.join(APP_DIR, *names),
        os.path.join(ROOT_DIR, *names),
        os.path.join(ROOT_DIR, "resources", "app.asar.src", *names),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def normalize_call_path(path):
    if not path or not path.startswith("/"):
        return None
    if "${" in path or "+" in path:
        return None
    if path.endswith("/"):
        return None
    return path.split("?")[0]


def route_to_regex(route):
    escaped = re.escape(route)
    escaped = re.sub(r"\\<[^>]+\\>", r"[^/]+", escaped)
    return re.compile("^" + escaped + "$")


class ApiContractTest(unittest.TestCase):
    def test_frontend_paths_have_flask_routes_or_compat_shims(self):
        backend_files = [
            find_project_file("qwen3_web.py"),
            find_project_file("kaguya_bootstrap.py"),
        ]
        backend_text = "\n".join(read_text(path) for path in backend_files if path)
        route_pattern = re.compile(r"@app\.route\(\s*['\"]([^'\"]+)['\"]")
        routes = set(route_pattern.findall(backend_text))
        route_regexes = [route_to_regex(route) for route in routes]

        frontend_files = [
            find_project_file("qwen3_web.py"),
            find_project_file("kaguya_frontend.py"),
            find_project_file("electron", "main.js"),
            find_project_file("electron", "preload.js"),
        ]
        call_patterns = [
            re.compile(r"fetch\(\s*['\"]([^'\"]+)['\"]"),
            re.compile(r"axios\.[a-z]+\(\s*['\"]([^'\"]+)['\"]"),
            re.compile(r"https?\.request\(\s*([^,\n]+)"),
        ]
        calls = set()
        for path in frontend_files:
            if not path:
                continue
            text = read_text(path)
            for pattern in call_patterns[:2]:
                for match in pattern.findall(text):
                    normalized = normalize_call_path(match)
                    if normalized:
                        calls.add(normalized)
            for literal in ("/api/model-status", "/models", "/api/chat", "/api/config", "/chat/completions"):
                if literal in text:
                    calls.add(literal)

        allowed = {
            "/favicon.ico",
            "/static",
            "/assets",
        }
        missing = []
        for call in sorted(calls):
            if any(call == item or call.startswith(item + "/") for item in allowed):
                continue
            if not any(regex.match(call) for regex in route_regexes):
                missing.append(call)
        self.assertFalse(missing, "Frontend calls without Flask route: " + ", ".join(missing[:50]))


if __name__ == "__main__":
    unittest.main()
