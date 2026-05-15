import json
import os
import re
import subprocess
import sys
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
REPO_ROOT = os.path.abspath(os.path.join(APP_DIR, "..", "..", ".."))
GO_SERVER = os.path.join(ROOT_DIR, "resources", "go-backend", "server.go")
ROUTE_CONTRACT = os.path.join(ROOT_DIR, "resources", "go-backend", "route_contract_generated.go")
COVERAGE_SCRIPT = os.path.join(APP_DIR, "scripts", "go_route_coverage.py")


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        return handle.read()


class ApiContractTest(unittest.TestCase):
    def test_archived_route_contract_is_fully_covered_by_go(self):
        result = subprocess.run(
            [sys.executable, COVERAGE_SCRIPT, "--fail-under", "100"],
            cwd=ROOT_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["coverage_percent"], 100.0)
        self.assertEqual(payload["missing_count"], 0)

    def test_go_contract_catalog_and_server_do_not_reference_removed_monolith(self):
        text = read_text(GO_SERVER) + "\n" + read_text(ROUTE_CONTRACT)
        removed_names = ["qwen" + "3_web", "qwen" + "3", "QWEN" + "3", "qw" + "3", "QW" + "3"]
        for name in removed_names:
            self.assertNotIn(name, text)

    def test_removed_monolith_names_are_not_tracked(self):
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        forbidden = ["qwen" + "3_web", "qwen" + "3", "QWEN" + "3", "qw" + "3", "QW" + "3"]
        offenders = []
        self_file = os.path.relpath(__file__, REPO_ROOT).replace(os.sep, "/")
        for rel_path in result.stdout.splitlines():
            normalized = rel_path.replace("\\", "/")
            if normalized == self_file:
                continue
            lowered = normalized.lower()
            if any(token.lower() in lowered for token in forbidden):
                offenders.append(f"path:{normalized}")
                continue
            abs_path = os.path.join(REPO_ROOT, rel_path)
            if os.path.getsize(abs_path) > 5_000_000:
                continue
            try:
                with open(abs_path, "rb") as handle:
                    raw = handle.read()
                if b"\x00" in raw[:4096]:
                    continue
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if any(token in text for token in forbidden):
                offenders.append(f"content:{normalized}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
