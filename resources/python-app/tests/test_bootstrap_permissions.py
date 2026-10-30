import os
import sys
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("KAGUYA_DESKTOP_MODE", "1")
os.environ.setdefault("KAGUYA_ELECTRON", "1")
os.environ.setdefault("KAGUYA_DISABLE_NGROK", "1")

import qwen3_web  # noqa: E402


class BootstrapPermissionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def post_check(self, payload):
        response = self.client.post("/permissions/check", json=payload)
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(response.is_json)
        return response, response.get_json()

    def test_normal_input(self):
        response, data = self.post_check({
            "tool_name": "Read",
            "tool_input": {"path": "README.md"},
            "session_id": "perm-normal",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertTrue(data["auto_approved"])

    def test_empty_input(self):
        response, data = self.post_check({})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(data["success"])
        self.assertIn("tool_name", data["error"])

    def test_unknown_tool(self):
        response, data = self.post_check({
            "tool_name": "UnknownTool",
            "tool_input": {},
            "session_id": "perm-unknown",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["tool_name"], "UnknownTool")
        self.assertFalse(data["auto_approved"])

    def test_missing_session_id_uses_default_session(self):
        response, data = self.post_check({
            "tool_name": "Read",
            "tool_input": {"path": "README.md"},
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertTrue(data["session_id"])


if __name__ == "__main__":
    unittest.main()
