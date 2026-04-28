import io
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


class IdeUploadTest(unittest.TestCase):
    device_id = "upload_smoke_device"

    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def setUp(self):
        self._known_accounts = set(qwen3_web.ide_user_registry.keys())

    def tearDown(self):
        cleanup_ids = (set(qwen3_web.ide_user_registry.keys()) - self._known_accounts) | {self.device_id}
        for account_id in cleanup_ids:
            user_info = qwen3_web.ide_user_registry.get(account_id)
            if not user_info:
                continue
            workspace = user_info.get("workspace")
            if workspace and os.path.abspath(workspace).startswith(os.path.abspath(qwen3_web.IDE_WORKSPACE_ROOT)):
                shutil.rmtree(workspace, ignore_errors=True)
            qwen3_web.ide_user_registry.pop(account_id, None)
        qwen3_web._save_accounts()

    def test_upload_nested_files_batch(self):
        files = [
            (io.BytesIO(f"content-{i}".encode("utf-8")), f"folder/sub/file-{i}.txt")
            for i in range(150)
        ]
        response = self.client.post(
            "/agent/upload-device-files",
            data={"device_id": self.device_id, "files": files},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertFalse(data.get("error"))
        self.assertEqual(len(data.get("imported", [])), 150)
        self.assertEqual(data.get("errors"), [])
        first_path = os.path.join(data["workspace"], "folder", "sub", "file-0.txt")
        self.assertTrue(os.path.exists(first_path))


if __name__ == "__main__":
    unittest.main()
