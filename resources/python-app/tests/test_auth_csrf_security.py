import os
import shutil
import sys
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("KAGUYA_DESKTOP_MODE", "1")
os.environ.setdefault("KAGUYA_ELECTRON", "1")
os.environ.setdefault("KAGUYA_DISABLE_NGROK", "1")

import qwen3_web  # noqa: E402


class AuthCsrfSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def setUp(self):
        self.old_auth = qwen3_web.is_auth_enabled
        qwen3_web.is_auth_enabled = lambda: False
        self.device_id = "auth_csrf_security_test"
        self.workspace = os.path.join(qwen3_web.IDE_WORKSPACE_ROOT, self.device_id)
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        qwen3_web._get_user_workspace(self.device_id)

    def tearDown(self):
        qwen3_web.is_auth_enabled = self.old_auth
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        qwen3_web._save_accounts()

    def test_auth_disabled_localhost_can_access_low_risk_endpoint(self):
        response = self.client.get("/permissions/status", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}, headers={"Host": "127.0.0.1:5000"})
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)

    def test_auth_disabled_remote_high_risk_endpoint_rejected(self):
        response = self.client.post(
            "/agent/write-file",
            json={"device_id": self.device_id, "path": "x.txt", "content": "x"},
            environ_overrides={"REMOTE_ADDR": "10.1.2.3"},
            headers={"Host": "192.168.1.10:5000"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.get_json().get("auth_required"))

    def test_remote_terminal_without_csrf_or_auth_is_rejected_before_execution(self):
        response = self.client.post(
            "/agent/terminal/exec",
            json={"device_id": self.device_id, "command": "python --version"},
            environ_overrides={"REMOTE_ADDR": "10.1.2.3"},
            headers={"Host": "192.168.1.10:5000"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json().get("error"), "remote_high_risk_blocked")

    def test_security_status_reflects_policy(self):
        response = self.client.get("/security/status")
        self.assertEqual(response.status_code, 200)
        status = response.get_json().get("status", {})
        self.assertIn("/agent/terminal/exec", status.get("high_risk_post_paths", []))
        self.assertEqual(status.get("remote_high_risk_policy"), "auth_or_reject")


if __name__ == "__main__":
    unittest.main()
