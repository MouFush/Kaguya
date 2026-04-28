import os
import shutil
import sys
import tempfile
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("KAGUYA_DESKTOP_MODE", "1")
os.environ.setdefault("KAGUYA_ELECTRON", "1")
os.environ.setdefault("KAGUYA_DISABLE_NGROK", "1")

import qwen3_web  # noqa: E402
import kaguya_terminal_service  # noqa: E402
import kaguya_tool_executor  # noqa: E402
from kaguya_api_permissions import PermissionResult  # noqa: E402


class TerminalSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def setUp(self):
        self.device_id = "terminal_security_test"
        self.workspace = os.path.join(qwen3_web.IDE_WORKSPACE_ROOT, self.device_id)
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        qwen3_web._get_user_workspace(self.device_id)
        self.outside = tempfile.mkdtemp(prefix="kaguya-term-outside-")

    def tearDown(self):
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        shutil.rmtree(self.outside, ignore_errors=True)
        qwen3_web._save_accounts()

    def test_dangerous_command_is_denied(self):
        response = self.client.post("/agent/terminal/exec", json={"device_id": self.device_id, "command": "rm -rf /"})
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data.get("error"), "permission_denied")
        self.assertEqual(data.get("permission", {}).get("risk_level"), "critical")

    def test_high_risk_script_without_permission_does_not_execute(self):
        marker = os.path.join(self.workspace, "marker.txt")
        script = os.path.join(self.workspace, "write_marker.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(f"open({marker!r}, 'w').write('ran')\n")
        response = self.client.post("/agent/terminal/exec", json={"device_id": self.device_id, "command": f"python {script}"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(os.path.exists(marker))

    def test_shell_mode_is_not_default_execution_path(self):
        response = self.client.post("/agent/terminal/exec", json={"device_id": self.device_id, "command": "python --version"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("args", data)
        self.assertFalse(data.get("permission", {}).get("requires_confirmation"))

    def test_working_dir_outside_workspace_is_denied(self):
        response = self.client.post(
            "/agent/terminal/exec",
            json={"device_id": self.device_id, "command": "python --version", "working_dir": self.outside},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json().get("error"), "working_dir_outside_workspace")

    def test_timeout_returns_deterministic_result(self):
        old_check = kaguya_terminal_service.permission_service.check
        kaguya_terminal_service.permission_service.check = lambda *args, **kwargs: PermissionResult(True, "test override", "low", False)
        command = 'python -c "import time; time.sleep(2)"'
        try:
            response = self.client.post(
                "/agent/terminal/exec",
                json={"device_id": self.device_id, "command": command, "timeout": 1},
            )
        finally:
            kaguya_terminal_service.permission_service.check = old_check
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("exit_code"), -1)
        self.assertTrue(data.get("timed_out"))

    def test_audit_log_written_for_allowed_and_denied(self):
        before = qwen3_web.audit_logger.get_stats().get("total", 0)
        self.client.post("/agent/terminal/exec", json={"device_id": self.device_id, "command": "python --version"})
        self.client.post("/agent/terminal/exec", json={"device_id": self.device_id, "command": "rm -rf /"})
        after = qwen3_web.audit_logger.get_stats().get("total", 0)
        self.assertGreaterEqual(after, before + 2)

    def test_run_project_requires_permission_before_execution(self):
        project = os.path.join(self.workspace, "project")
        os.makedirs(project, exist_ok=True)
        marker = os.path.join(project, "ran.txt")
        script = os.path.join(project, "main.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(f"open({marker!r}, 'w').write('ran')\n")
        response = self.client.post(
            "/agent/run-project",
            json={"device_id": self.device_id, "path": project, "start_command": f"python {script}"},
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data.get("error"), "permission_denied")
        self.assertTrue(data.get("permission", {}).get("requires_confirmation"))
        self.assertFalse(os.path.exists(marker))

    def test_compile_requires_permission_before_execution(self):
        marker = os.path.join(self.workspace, "compiled.txt")
        response = self.client.post(
            "/agent/compile",
            json={"device_id": self.device_id, "language": "python", "code": f"open({marker!r}, 'w').write('ran')"},
        )
        self.assertEqual(response.status_code, 403)
        data = response.get_json()
        self.assertEqual(data.get("error"), "permission_denied")
        self.assertTrue(data.get("permission", {}).get("requires_confirmation"))
        self.assertFalse(os.path.exists(marker))

    def test_tool_executor_bash_fails_closed_without_permission(self):
        marker = os.path.join(self.workspace, "tool_executor_marker.txt")
        script = os.path.join(self.workspace, "tool_executor_script.py")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(f"open({marker!r}, 'w').write('ran')\n")
        executor = kaguya_tool_executor.StreamingToolExecutor(max_workers=1)
        task_id = executor.submit(
            "Bash",
            {"command": f"python {script}", "working_dir": self.workspace},
            session_id="terminal_security_test",
            max_retries=0,
        )
        result = executor.wait_for(task_id, timeout=5)
        executor.stop()
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("Permission denied", result.error or "")
        self.assertFalse(os.path.exists(marker))


if __name__ == "__main__":
    unittest.main()
