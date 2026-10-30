import json
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


class DeviceApiConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def setUp(self):
        self.device_id = "device_api_config_test"
        self.workspace = os.path.join(qwen3_web.IDE_WORKSPACE_ROOT, self.device_id)
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        qwen3_web._save_accounts()

    def tearDown(self):
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        qwen3_web._save_accounts()

    def test_device_bind_masks_key_and_persists(self):
        secret = "sk-test-secret-123456"
        response = self.client.post(
            "/api/device/bind",
            json={
                "device_id": self.device_id,
                "provider": "openai",
                "apiKey": secret,
                "apiUrl": "https://api.openai.com/v1",
                "model": "gpt-4o",
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertNotIn(secret, body)
        data = response.get_json()
        self.assertEqual(data.get("masked_api_key"), "sk-t****3456")

        saved = self.client.get(f"/api/account/saved-config?device_id={self.device_id}")
        self.assertEqual(saved.status_code, 200)
        saved_body = saved.get_data(as_text=True)
        self.assertNotIn(secret, saved_body)
        saved_data = saved.get_json()
        self.assertTrue(saved_data.get("has_config"))
        self.assertEqual(saved_data.get("provider"), "openai")
        self.assertEqual(saved_data.get("masked_api_key"), "sk-t****3456")

        qwen3_web.ide_user_registry = {}
        qwen3_web._load_accounts()
        reloaded = self.client.get(f"/api/account/saved-config?device_id={self.device_id}")
        reloaded_data = reloaded.get_json()
        self.assertTrue(reloaded_data.get("has_config"))
        self.assertEqual(reloaded_data.get("provider"), "openai")
        self.assertNotIn(secret, reloaded.get_data(as_text=True))

    def test_external_config_masked_roundtrip_does_not_clear_saved_key(self):
        secret = "sk-test-secret-kimi-123456"
        self.client.post(
            "/api/device/bind",
            json={
                "device_id": self.device_id,
                "provider": "kimi",
                "apiKey": secret,
                "apiUrl": "https://api.moonshot.ai/v1",
                "model": "kimi-k2.6",
            },
        )
        response = self.client.get(f"/external/config?device_id={self.device_id}")
        data = response.get_json()
        self.assertTrue(data["providers"]["kimi"]["_has_key"])
        self.assertNotIn(secret, response.get_data(as_text=True))

        masked_providers = data["providers"]
        save_response = self.client.post(
            "/external/config",
            json={"device_id": self.device_id, "active_provider": "kimi", "providers": masked_providers},
        )
        self.assertEqual(save_response.status_code, 200)

        saved = self.client.get(f"/api/account/saved-config?device_id={self.device_id}")
        saved_data = saved.get_json()
        self.assertTrue(saved_data.get("has_config"))
        self.assertEqual(saved_data.get("provider"), "kimi")
        self.assertEqual(saved_data.get("model"), "kimi-k2.6")

        status = self.client.post(
            "/api/model-status",
            json={"device_id": self.device_id, "external_api": {"provider": "kimi", "apiUrl": "https://api.moonshot.ai/v1", "model": "kimi-k2.6", "hasSavedKey": True}},
        )
        self.assertEqual(status.status_code, 200)
        status_data = status.get_json()
        self.assertTrue(status_data.get("available"))
        self.assertEqual(status_data.get("provider"), "kimi")

    def test_device_unbind_removes_saved_config(self):
        self.client.post(
            "/api/device/bind",
            json={"device_id": self.device_id, "provider": "deepseek", "api_key": "sk-test-secret-abcdef", "model": "deepseek-chat"},
        )
        response = self.client.post("/api/device/unbind", json={"device_id": self.device_id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json().get("success"))

        saved = self.client.get(f"/api/account/saved-config?device_id={self.device_id}")
        data = saved.get_json()
        self.assertFalse(data.get("has_config"))
        self.assertNotIn("sk-test-secret-abcdef", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
