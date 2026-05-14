import os
import shutil
import tempfile
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
import sys
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

os.environ.setdefault("KAGUYA_DESKTOP_MODE", "1")
os.environ.setdefault("KAGUYA_ELECTRON", "1")
os.environ.setdefault("KAGUYA_DISABLE_NGROK", "1")

import qwen3_web  # noqa: E402
from kaguya_workspace_security import WorkspaceAuthorizationError, add_imported_root, authorize_path  # noqa: E402


class WorkspaceSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def setUp(self):
        self.device_id = "workspace_security_test"
        self.tempdir = tempfile.mkdtemp(prefix="kaguya-ws-sec-")
        self.outside = os.path.join(self.tempdir, "outside")
        self.imported = os.path.join(self.tempdir, "imported")
        self.prefix_sibling = os.path.join(self.tempdir, "imported2")
        os.makedirs(self.outside)
        os.makedirs(self.imported)
        os.makedirs(self.prefix_sibling)
        with open(os.path.join(self.outside, "secret.txt"), "w", encoding="utf-8") as handle:
            handle.write("secret")
        with open(os.path.join(self.imported, "allowed.txt"), "w", encoding="utf-8") as handle:
            handle.write("allowed")
        with open(os.path.join(self.prefix_sibling, "sibling.txt"), "w", encoding="utf-8") as handle:
            handle.write("sibling")
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        self.workspace = os.path.join(qwen3_web.IDE_WORKSPACE_ROOT, self.device_id)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        self.user_info = qwen3_web._get_user_workspace(self.device_id)

    def tearDown(self):
        qwen3_web.ide_user_registry.pop(self.device_id, None)
        if os.path.isdir(self.workspace):
            shutil.rmtree(self.workspace)
        shutil.rmtree(self.tempdir, ignore_errors=True)
        qwen3_web._save_accounts()

    def test_desktop_mode_cannot_read_outside_workspace(self):
        response = self.client.post("/agent/read-file", json={"device_id": self.device_id, "path": os.path.join(self.outside, "secret.txt")})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.get_json().get("error", ""))

    def test_desktop_mode_cannot_write_outside_workspace(self):
        target = os.path.join(self.outside, "write.txt")
        response = self.client.post("/agent/write-file", json={"device_id": self.device_id, "path": target, "content": "blocked"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(os.path.exists(target))

    def test_imported_path_allows_child_not_prefix_sibling(self):
        add_imported_root(self.user_info, self.imported)
        self.assertTrue(authorize_path(os.path.join(self.imported, "allowed.txt"), self.workspace, self.user_info))
        with self.assertRaises(WorkspaceAuthorizationError):
            authorize_path(os.path.join(self.prefix_sibling, "sibling.txt"), self.workspace, self.user_info)

    def test_dotdot_path_traversal_fails(self):
        traversal = os.path.join(self.workspace, "..", "..", "outside.txt")
        with self.assertRaises(WorkspaceAuthorizationError):
            authorize_path(traversal, self.workspace, self.user_info)

    def test_symlink_escape_fails_when_supported(self):
        link_path = os.path.join(self.workspace, "linked-secret.txt")
        try:
            os.symlink(os.path.join(self.outside, "secret.txt"), link_path)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable on this platform: {exc}")
        response = self.client.post("/agent/read-file", json={"device_id": self.device_id, "path": link_path})
        self.assertEqual(response.status_code, 403)

    def test_open_project_does_not_auto_trust_external_path(self):
        response = self.client.post("/agent/open-project", json={"device_id": self.device_id, "path": self.imported})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data.get("trusted"))
        self.assertTrue(data.get("requires_confirmation"))
        self.assertFalse(qwen3_web._validate_path_in_workspace(os.path.join(self.imported, "allowed.txt"), self.workspace, self.user_info))


if __name__ == "__main__":
    unittest.main()
