import json
import os
import sys
import unittest


APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from kaguya_worker_adapter import (  # noqa: E402
    build_model_status,
    build_saved_config_response,
    mask_api_key,
    normalize_external_api_payload,
    structured_unavailable,
)


class WorkerAdapterTest(unittest.TestCase):
    def test_normalize_accepts_camel_case_and_kimi_defaults(self):
        cfg = normalize_external_api_payload({
            "provider": "KIMI",
            "apiKey": "  sk-kimi-secret-123456  ",
            "apiUrl": "",
        })

        self.assertEqual(cfg["provider"], "kimi")
        self.assertEqual(cfg["api_key"], "sk-kimi-secret-123456")
        self.assertEqual(cfg["api_url"], "https://api.moonshot.ai/v1")
        self.assertEqual(cfg["model"], "kimi-k2.6")
        self.assertTrue(cfg["enabled"])

    def test_normalize_accepts_snake_case(self):
        cfg = normalize_external_api_payload({
            "provider": "openai",
            "api_key": " sk-openai-secret-abcdef ",
            "api_url": " https://api.openai.com/v1 ",
            "model": " gpt-4o-mini ",
        })

        self.assertEqual(cfg["api_key"], "sk-openai-secret-abcdef")
        self.assertEqual(cfg["api_url"], "https://api.openai.com/v1")
        self.assertEqual(cfg["model"], "gpt-4o-mini")
        self.assertTrue(cfg["enabled"])

    def test_mask_api_key_never_returns_full_secret(self):
        secret = "sk-test-secret-123456"
        masked = mask_api_key(secret)

        self.assertEqual(masked, "sk-t****3456")
        self.assertNotEqual(masked, secret)
        self.assertNotIn("secret", masked)
        self.assertEqual(mask_api_key("short"), "****")
        self.assertEqual(mask_api_key(""), "")

    def test_saved_config_response_does_not_leak_plaintext_key(self):
        secret = "sk-test-secret-kimi-123456"
        response = build_saved_config_response({
            "provider": "kimi",
            "apiKey": secret,
            "apiUrl": "",
        })
        body = json.dumps(response, ensure_ascii=False)

        self.assertTrue(response["has_config"])
        self.assertEqual(response["provider"], "kimi")
        self.assertEqual(response["api_url"], "https://api.moonshot.ai/v1")
        self.assertEqual(response["model"], "kimi-k2.6")
        self.assertEqual(response["masked_api_key"], "sk-t****3456")
        self.assertNotIn(secret, body)

    def test_model_status_supports_saved_key_without_leaking_it(self):
        response = build_model_status({
            "provider": "kimi",
            "apiUrl": "https://api.moonshot.ai/v1",
            "model": "kimi-k2.6",
            "hasSavedKey": True,
        })
        body = json.dumps(response, ensure_ascii=False)

        self.assertTrue(response["available"])
        self.assertTrue(response["external_provider_configured"])
        self.assertEqual(response["reason"], None)
        self.assertNotIn("api_key", body)
        self.assertNotIn("apiKey", body)

    def test_structured_unavailable_payload_is_json_ready(self):
        payload = structured_unavailable(detail="offline")

        self.assertFalse(payload["success"])
        self.assertFalse(payload["available"])
        self.assertEqual(payload["provider"], "ollama")
        self.assertEqual(payload["model"], "qwen3.5:4b")
        self.assertEqual(payload["reason"], "ollama_unavailable")
        self.assertEqual(payload["detail"], "offline")


if __name__ == "__main__":
    unittest.main()
