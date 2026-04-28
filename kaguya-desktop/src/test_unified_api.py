"""
Kaguya Unified API 测试用例
============================
验证通用API适配器的通用性和稳定性

运行方式: python test_unified_api.py
"""

import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kaguya_unified_api import (
    UnifiedAPIClient, Message, ToolSchema, StreamChunk, ChatResponse,
    APIError, AuthError, RateLimitError, TimeoutError, ModelError,
    create_adapter, get_available_providers, register_provider,
    PROVIDER_REGISTRY, ProviderConfig, ProviderType,
    OpenAICompatibleAdapter, AnthropicAdapter, GeminiAdapter,
    call_external_provider_unified, test_external_api_unified
)


class TestRunner:
    """简易测试运行器"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_true(self, condition, msg=""):
        if not condition:
            raise AssertionError(msg or "Expected True, got False")

    def assert_equal(self, a, b, msg=""):
        if a != b:
            raise AssertionError(msg or f"Expected {b!r}, got {a!r}")

    def assert_in(self, item, container, msg=""):
        if item not in container:
            raise AssertionError(msg or f"Expected {item!r} in {container!r}")

    def assert_is_not_none(self, obj, msg=""):
        if obj is None:
            raise AssertionError(msg or "Expected not None")

    def assert_is_instance(self, obj, cls, msg=""):
        if not isinstance(obj, cls):
            raise AssertionError(msg or f"Expected instance of {cls}, got {type(obj)}")

    def assert_raises(self, exc_cls, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exc_cls.__name__} to be raised")
        except exc_cls:
            pass

    def run_test(self, name, func):
        try:
            func()
            self.passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            self.failed += 1
            self.errors.append((name, e))
            print(f"  FAIL: {name} - {e}")

    def report(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"测试运行完成: {total} 个测试")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print("=" * 60)
        if self.errors:
            print("\n失败详情:")
            for name, err in self.errors:
                print(f"  - {name}: {err}")
        return self.failed == 0


def run_all_tests():
    runner = TestRunner()
    a = runner.assert_equal
    t = runner.assert_true
    inn = runner.assert_in
    nn = runner.assert_is_not_none
    isa = runner.assert_is_instance
    ar = runner.assert_raises

    print("\n[TestProviderConfig] 厂商配置测试")

    def test_default_providers_count():
        providers = get_available_providers()
        t(len(providers) >= 10, f"应至少支持10个厂商,实际{len(providers)}")
    runner.run_test("test_default_providers_count", test_default_providers_count)

    def test_all_providers_have_required_fields():
        for p in get_available_providers():
            inn(p.get("id"), "missing id")
            nn(p.get("name"), "missing name")
            nn(p.get("base_url"), "missing base_url")
            nn(p.get("default_model"), "missing default_model")
    runner.run_test("test_all_providers_have_required_fields", test_all_providers_have_required_fields)

    def test_provider_registry_keys():
        expected = {"deepseek", "openai", "claude", "kimi", "glm", "gemini",
                    "mistral", "groq", "xai", "ollama"}
        actual = set(PROVIDER_REGISTRY.keys())
        t(expected.issubset(actual), f"缺少厂商: {expected - actual}")
    runner.run_test("test_provider_registry_keys", test_provider_registry_keys)

    print("\n[TestAdapterFactory] 适配器工厂测试")

    def test_create_openai_compatible_adapter():
        adapter = create_adapter("deepseek")
        isa(adapter, OpenAICompatibleAdapter)
        a(adapter.config.provider_id, "deepseek")
    runner.run_test("test_create_openai_compatible_adapter", test_create_openai_compatible_adapter)

    def test_create_claude_adapter():
        adapter = create_adapter("claude")
        isa(adapter, AnthropicAdapter)
        a(adapter.config.provider_id, "claude")
    runner.run_test("test_create_claude_adapter", test_create_claude_adapter)

    def test_create_gemini_adapter():
        adapter = create_adapter("gemini")
        isa(adapter, GeminiAdapter)
        a(adapter.config.provider_id, "gemini")
    runner.run_test("test_create_gemini_adapter", test_create_gemini_adapter)

    def test_create_adapter_with_custom_config():
        adapter = create_adapter("openai", {"base_url": "https://custom.api.com/v1"})
        a(adapter.config.base_url, "https://custom.api.com/v1")
    runner.run_test("test_create_adapter_with_custom_config", test_create_adapter_with_custom_config)

    def test_create_unknown_provider_raises():
        ar(ValueError, create_adapter, "unknown_provider")
    runner.run_test("test_create_unknown_provider_raises", test_create_unknown_provider_raises)

    print("\n[TestMessageAndToolSchema] 消息和工具Schema测试")

    def test_message_to_dict():
        m = Message(role="user", content="Hello")
        d = m.to_dict()
        a(d["role"], "user")
        a(d["content"], "Hello")
    runner.run_test("test_message_to_dict", test_message_to_dict)

    def test_message_with_tool_calls():
        m = Message(role="assistant", content="", tool_calls=[{"id": "1", "name": "test"}])
        d = m.to_dict()
        a(d["tool_calls"][0]["name"], "test")
    runner.run_test("test_message_with_tool_calls", test_message_with_tool_calls)

    def test_tool_schema_to_openai():
        ts = ToolSchema(name="read_file", description="Read a file",
                        parameters={"type": "object", "properties": {"path": {"type": "string"}}})
        oai = ts.to_openai()
        a(oai["type"], "function")
        a(oai["function"]["name"], "read_file")
    runner.run_test("test_tool_schema_to_openai", test_tool_schema_to_openai)

    def test_tool_schema_to_anthropic():
        ts = ToolSchema(name="read_file", description="Read a file",
                        parameters={"type": "object", "properties": {"path": {"type": "string"}}})
        ant = ts.to_anthropic()
        a(ant["name"], "read_file")
        a(ant["input_schema"]["type"], "object")
    runner.run_test("test_tool_schema_to_anthropic", test_tool_schema_to_anthropic)

    print("\n[TestErrorHandling] 错误处理测试")

    def test_api_error_to_dict():
        err = APIError("Test error", "test_code", 500, "raw")
        d = err.to_dict()
        t(d["error"])
        a(d["code"], "test_code")
        a(d["status_code"], 500)
    runner.run_test("test_api_error_to_dict", test_api_error_to_dict)

    def test_auth_error():
        err = AuthError("Invalid key", 401, "Unauthorized")
        a(err.code, "auth_error")
        a(err.status_code, 401)
    runner.run_test("test_auth_error", test_auth_error)

    def test_rate_limit_error():
        err = RateLimitError("Too many requests")
        a(err.code, "rate_limit")
        a(err.status_code, 429)
    runner.run_test("test_rate_limit_error", test_rate_limit_error)

    def test_timeout_error():
        err = TimeoutError("Request timeout")
        a(err.code, "timeout")
    runner.run_test("test_timeout_error", test_timeout_error)

    print("\n[TestOpenAICompatibleAdapter] OpenAI兼容适配器测试")

    def test_build_request():
        adapter = create_adapter("deepseek")
        messages = [Message(role="user", content="Hello")]
        url, data, headers = adapter.build_request(messages)
        t("chat/completions" in url)
        payload = json.loads(data)
        a(payload["model"], "deepseek-chat")
        a(payload["messages"][0]["role"], "user")
        t(payload["stream"])
    runner.run_test("test_build_request", test_build_request)

    def test_build_request_with_tools():
        adapter = create_adapter("deepseek")
        messages = [Message(role="user", content="Hello")]
        tools = [ToolSchema(name="test", description="test", parameters={})]
        url, data, headers = adapter.build_request(messages, tools=tools)
        payload = json.loads(data)
        t("tools" in payload)
    runner.run_test("test_build_request_with_tools", test_build_request_with_tools)

    def test_parse_stream_chunk_content():
        adapter = create_adapter("deepseek")
        line = '{"choices": [{"delta": {"content": "Hello"}, "finish_reason": null}]}'
        chunk = adapter.parse_stream_chunk("data: " + line)
        nn(chunk)
        a(chunk.content, "Hello")
    runner.run_test("test_parse_stream_chunk_content", test_parse_stream_chunk_content)

    def test_parse_stream_chunk_tool_calls():
        adapter = create_adapter("deepseek")
        line = '{"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "read_file", "arguments": "{\\"path\\": \\"test.txt\\"}"}}]}, "finish_reason": null}]}'
        chunk = adapter.parse_stream_chunk("data: " + line)
        nn(chunk)
        nn(chunk.tool_calls)
    runner.run_test("test_parse_stream_chunk_tool_calls", test_parse_stream_chunk_tool_calls)

    def test_parse_stream_chunk_done():
        adapter = create_adapter("deepseek")
        chunk = adapter.parse_stream_chunk("data: [DONE]")
        nn(chunk)
        a(chunk.finish_reason, "stop")
    runner.run_test("test_parse_stream_chunk_done", test_parse_stream_chunk_done)

    def test_parse_stream_chunk_invalid():
        adapter = create_adapter("deepseek")
        chunk = adapter.parse_stream_chunk("not data: format")
        t(chunk is None)
    runner.run_test("test_parse_stream_chunk_invalid", test_parse_stream_chunk_invalid)

    def test_parse_response():
        adapter = create_adapter("deepseek")
        raw = json.dumps({
            "choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "deepseek-chat"
        }).encode()
        resp = adapter.parse_response(raw)
        a(resp.content, "Hello")
        a(resp.usage["prompt_tokens"], 10)
    runner.run_test("test_parse_response", test_parse_response)

    print("\n[TestAnthropicAdapter] Anthropic适配器测试")

    def test_build_request_claude():
        adapter = create_adapter("claude")
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello")
        ]
        url, data, headers = adapter.build_request(messages)
        t("/v1/messages" in url)
        payload = json.loads(data)
        a(payload["system"], "You are helpful")
        roles = [m["role"] for m in payload["messages"]]
        t("system" not in roles)
    runner.run_test("test_build_request_claude", test_build_request_claude)

    def test_build_request_claude_no_system():
        adapter = create_adapter("claude")
        messages = [Message(role="user", content="Hello")]
        url, data, headers = adapter.build_request(messages)
        payload = json.loads(data)
        t("system" not in payload)
    runner.run_test("test_build_request_claude_no_system", test_build_request_claude_no_system)

    def test_parse_stream_chunk_claude():
        adapter = create_adapter("claude")
        line = '{"type": "content_block_delta", "delta": {"text": "Hello"}}'
        chunk = adapter.parse_stream_chunk("data: " + line)
        nn(chunk)
        a(chunk.content, "Hello")
    runner.run_test("test_parse_stream_chunk_claude", test_parse_stream_chunk_claude)

    def test_parse_stream_chunk_claude_stop():
        adapter = create_adapter("claude")
        line = '{"type": "message_stop"}'
        chunk = adapter.parse_stream_chunk("data: " + line)
        nn(chunk)
        a(chunk.finish_reason, "stop")
    runner.run_test("test_parse_stream_chunk_claude_stop", test_parse_stream_chunk_claude_stop)

    print("\n[TestUnifiedAPIClient] 统一API客户端测试")

    def test_init():
        client = UnifiedAPIClient("deepseek", "test-key", "https://api.test.com", "test-model")
        a(client.provider_id, "deepseek")
        a(client.api_key, "test-key")
        a(client.model, "test-model")
    runner.run_test("test_init", test_init)

    def test_init_defaults():
        client = UnifiedAPIClient("openai", "test-key")
        a(client.adapter.config.base_url, "https://api.openai.com/v1")
        a(client.adapter.config.default_model, "gpt-4o")
    runner.run_test("test_init_defaults", test_init_defaults)

    print("\n[TestProviderRegistration] 厂商注册扩展测试")

    def test_register_new_provider():
        config = ProviderConfig(
            provider_id="custom_test",
            display_name="Custom Test API",
            provider_type=ProviderType.OPENAI_COMPATIBLE,
            base_url="https://api.custom.com/v1",
            default_model="custom-model"
        )
        register_provider(config)
        t("custom_test" in PROVIDER_REGISTRY)
        adapter = create_adapter("custom_test")
        a(adapter.config.base_url, "https://api.custom.com/v1")
    runner.run_test("test_register_new_provider", test_register_new_provider)

    print("\n[TestIntegration] 集成测试")

    def test_full_message_chain():
        messages = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="2+2=4"),
            Message(role="user", content="What about 3+3?")
        ]
        adapter = create_adapter("deepseek")
        url, data, headers = adapter.build_request(messages)
        payload = json.loads(data)
        a(len(payload["messages"]), 4)
        a(payload["messages"][0]["role"], "system")
    runner.run_test("test_full_message_chain", test_full_message_chain)

    def test_multiple_tool_schemas():
        tools = [
            ToolSchema(name="read_file", description="Read file", parameters={"type": "object", "properties": {}}),
            ToolSchema(name="write_file", description="Write file", parameters={"type": "object", "properties": {}}),
            ToolSchema(name="execute_command", description="Run command", parameters={"type": "object", "properties": {}})
        ]
        adapter = create_adapter("openai")
        url, data, headers = adapter.build_request([Message(role="user", content="test")], tools=tools)
        payload = json.loads(data)
        a(len(payload["tools"]), 3)
    runner.run_test("test_multiple_tool_schemas", test_multiple_tool_schemas)

    print("\n[TestEdgeCases] 边界情况测试")

    def test_empty_message_content():
        m = Message(role="user", content="")
        a(m.to_dict()["content"], "")
    runner.run_test("test_empty_message_content", test_empty_message_content)

    def test_very_long_message():
        long_content = "A" * 100000
        m = Message(role="user", content=long_content)
        a(len(m.to_dict()["content"]), 100000)
    runner.run_test("test_very_long_message", test_very_long_message)

    def test_special_characters_in_message():
        content = "Hello \n\t \\ \" 中文 emoji"
        m = Message(role="user", content=content)
        d = m.to_dict()
        a(d["content"], content)
    runner.run_test("test_special_characters_in_message", test_special_characters_in_message)

    def test_unicode_model_name():
        adapter = create_adapter("deepseek")
        messages = [Message(role="user", content="test")]
        url, data, headers = adapter.build_request(messages, model="model-测试")
        payload = json.loads(data)
        a(payload["model"], "model-测试")
    runner.run_test("test_unicode_model_name", test_unicode_model_name)

    return runner.report()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
