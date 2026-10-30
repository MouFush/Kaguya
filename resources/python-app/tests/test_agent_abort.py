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


class _DummyAgentLoop:
    def run(self, *args, **kwargs):
        yield json.dumps({"type": "assistant", "content": "ok", "done": True})

    def run_with_external_api(self, *args, **kwargs):
        yield from self.run(*args, **kwargs)


class AgentAbortTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qwen3_web.app.config["TESTING"] = True
        cls.client = qwen3_web.app.test_client()

    def test_abort_empty_payload(self):
        response = self.client.post("/agent/abort", json={})
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error"), "missing_run_id")

    def test_abort_unknown_run_id(self):
        response = self.client.post("/agent/abort", json={"run_id": "missing"})
        self.assertNotEqual(response.status_code, 500)
        self.assertTrue(response.is_json)
        data = response.get_json()
        self.assertFalse(data.get("success"))
        self.assertFalse(data.get("aborted"))
        self.assertEqual(data.get("error"), "run_not_found")

    def test_abort_known_run_id_sets_event(self):
        evt = qwen3_web.threading.Event()
        qwen3_web._agent_abort_events["known-run"] = evt
        try:
            response = self.client.post("/agent/abort", json={"run_id": "known-run"})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("aborted"))
            self.assertTrue(evt.is_set())
        finally:
            qwen3_web._agent_abort_events.pop("known-run", None)

    def test_agent_run_first_frame_contains_run_id(self):
        old_loop = qwen3_web.agent_loop
        qwen3_web.agent_loop = _DummyAgentLoop()
        try:
            response = self.client.post("/agent/run", json={"message": "hello"}, buffered=False)
            first = next(response.response).decode("utf-8")
            self.assertIn("data: ", first)
            payload = json.loads(first.split("data: ", 1)[1].strip())
            self.assertEqual(payload.get("type"), "run_started")
            self.assertTrue(payload.get("run_id"))
            rest = b"".join(response.response).decode("utf-8")
            self.assertIn('"type": "assistant"', rest)
        finally:
            qwen3_web.agent_loop = old_loop


if __name__ == "__main__":
    unittest.main()
