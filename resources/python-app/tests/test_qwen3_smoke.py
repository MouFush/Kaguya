import json
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


class Qwen3SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def assert_json_api_ok(self, method, path, payload=None):
        if method == "GET":
            response = self.client.get(path)
        else:
            response = self.client.post(path, json=payload or {})
        self.assertNotEqual(response.status_code, 500, f"{method} {path} returned 500")
        self.assertTrue(response.is_json, f"{method} {path} did not return JSON")
        data = response.get_json()
        self.assertIsInstance(data, dict)
        body = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("Traceback", body)
        self.assertNotIn("NoneType", body)
        self.assertNotIn("object has no attribute", body)
        return response, data

    def test_homepage_loads_without_auth_redirect_when_disabled(self):
        response = self.client.get("/")
        self.assertNotEqual(response.status_code, 500)
        self.assertIn(response.status_code, (200, 302))
        if response.status_code == 302:
            self.assertNotIn("/auth/login", response.headers.get("Location", ""))

    def test_auth_enabled_json_api_returns_401_not_nameerror(self):
        old_is_auth_enabled = qwen3_web.is_auth_enabled
        old_is_authenticated = qwen3_web.is_authenticated
        try:
            qwen3_web.is_auth_enabled = lambda: True
            qwen3_web.is_authenticated = lambda: False
            response = self.client.get("/permissions/status", headers={"Accept": "application/json"})
            self.assertEqual(response.status_code, 401)
            self.assertTrue(response.is_json)
            self.assertTrue(response.get_json().get("auth_required"))
        finally:
            qwen3_web.is_auth_enabled = old_is_auth_enabled
            qwen3_web.is_authenticated = old_is_authenticated

    def test_chat_returns_structured_response_when_model_unavailable(self):
        response, data = self.assert_json_api_ok(
            "POST",
            "/chat",
            {"message": "hello", "history": []},
        )
        self.assertIn(response.status_code, (200, 503))
        self.assertTrue(any(key in data for key in ("response", "error", "success")))
        if data.get("success") is False:
            self.assertTrue(data.get("error") or data.get("reason"))

    def test_core_json_endpoints_do_not_500(self):
        for path in (
            "/agent/tasks",
            "/rag/documents",
            "/kaguya/features/flags",
            "/permissions/status",
            "/permissions/mode",
        ):
            with self.subTest(path=path):
                self.assert_json_api_ok("GET", path)

    def test_image_routes_do_not_404(self):
        for path in ("/header-img", "/hero-img", "/welcome-img", "/sidebar-icon", "/favicon.ico"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content_type.startswith(("image/", "text/html", "image/svg+xml")))
                response.get_data()
                response.close()

    def test_permissions_check_do_not_500(self):
        _, data = self.assert_json_api_ok(
            "POST",
            "/permissions/check",
            {"tool_name": "Read", "tool_input": {"path": "README.md"}, "session_id": "smoke-session"},
        )
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("tool_name"), "Read")
        self.assertIn("risk_level", data)
        self.assertIn("mode", data)
        self.assertIn("auto_approved", data)
        self.assertIn("reason", data)


if __name__ == "__main__":
    unittest.main()
