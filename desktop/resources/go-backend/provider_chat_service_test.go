package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestProviderChatNormalizeDefaults(t *testing.T) {
	key := "sk-kimi-secret-123456"
	cfg := pcsNormalizeExternalProviderConfig(map[string]any{
		"provider": "moonshot",
		"apiKey":   key,
	}, deviceConfig{})
	if cfg.Provider != "moonshot" {
		t.Fatalf("provider changed unexpectedly: %#v", cfg)
	}
	if cfg.APIURL != "https://api.moonshot.ai/v1" {
		t.Fatalf("moonshot default api url missing: %#v", cfg)
	}
	if cfg.Model != "kimi-k2.6" {
		t.Fatalf("kimi default model missing: %#v", cfg)
	}
	masked := pcsMaskedProviderConfig(cfg)
	rendered := mustJSON(t, masked)
	if strings.Contains(rendered, key) {
		t.Fatalf("masked config leaked key: %s", rendered)
	}

	cfg = pcsNormalizeExternalProviderConfig(map[string]any{"provider": "deepseek", "api_key": key}, deviceConfig{})
	if cfg.APIURL != "https://api.deepseek.com/v1" || cfg.Model != "deepseek-chat" {
		t.Fatalf("deepseek defaults missing: %#v", cfg)
	}
	cfg = pcsNormalizeExternalProviderConfig(map[string]any{"provider": "openai", "api_key": key}, deviceConfig{})
	if cfg.APIURL != "https://api.openai.com/v1" || cfg.Model == "" {
		t.Fatalf("openai defaults missing: %#v", cfg)
	}
}

func TestProviderChatUsesOpenAICompatibleUpstreamAndDoesNotLeakKey(t *testing.T) {
	key := "sk-provider-secret-abcdef"
	var gotPath, gotAuth string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload["api_key"] != nil || payload["apiKey"] != nil || payload["api_url"] != nil || payload["provider"] != nil {
			t.Fatalf("upstream payload leaked config fields: %#v", payload)
		}
		if payload["model"] != "kimi-k2.6" {
			t.Fatalf("model default not applied: %#v", payload)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"cmpl-test","choices":[{"message":{"role":"assistant","content":"pong"}}],"metadata":{"echo":"` + key + `"}}`))
	}))
	defer upstream.Close()

	service := newProviderChatService(upstream.Client())
	cfg := deviceConfig{Provider: "kimi", APIURL: upstream.URL + "/v1", APIKey: key, Model: "kimi-k2.6"}
	result, err := service.complete(context.Background(), cfg, map[string]any{
		"message": "ping",
		"api_key": key,
		"apiUrl":  "https://should-not-forward.example/v1",
	}, providerChatOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if result.StatusCode != http.StatusOK {
		t.Fatalf("status=%d json=%#v", result.StatusCode, result.JSON)
	}
	if gotPath != "/v1/chat/completions" || gotAuth != "Bearer "+key {
		t.Fatalf("upstream path/auth mismatch path=%s auth=%s", gotPath, gotAuth)
	}
	rendered := mustJSON(t, result.JSON)
	if strings.Contains(rendered, key) {
		t.Fatalf("provider response leaked key: %s", rendered)
	}
	if result.JSON["response"] != "pong" {
		t.Fatalf("assistant content not adapted: %#v", result.JSON)
	}
}

func TestProviderChatKimiK26PayloadDisablesThinking(t *testing.T) {
	key := "sk-kimi-secret-abcdef"
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload["max_tokens"] != nil {
			t.Fatalf("kimi k2 payload must not use max_tokens: %#v", payload)
		}
		if payload["max_completion_tokens"] != float64(1234) {
			t.Fatalf("kimi k2 max_completion_tokens missing: %#v", payload)
		}
		thinking, _ := payload["thinking"].(map[string]any)
		if thinking == nil || thinking["type"] != "disabled" {
			t.Fatalf("kimi k2 thinking must be disabled: %#v", payload)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"role":"assistant","content":"kimi ok"}}]}`))
	}))
	defer upstream.Close()

	service := newProviderChatService(upstream.Client())
	cfg := deviceConfig{Provider: "kimi", APIURL: upstream.URL, APIKey: key, Model: "kimi-k2.6"}
	result, err := service.complete(context.Background(), cfg, map[string]any{"message": "hello", "max_tokens": 1234, "thinking": map[string]any{"type": "enabled"}}, providerChatOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if result.StatusCode != http.StatusOK || result.JSON["response"] != "kimi ok" {
		t.Fatalf("unexpected kimi response: status=%d json=%#v", result.StatusCode, result.JSON)
	}
}

func TestProviderChatOpenAICompatibleResponse(t *testing.T) {
	key := "sk-openai-secret"
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"cmpl-raw","object":"chat.completion","choices":[{"message":{"role":"assistant","content":"raw pong"}}]}`))
	}))
	defer upstream.Close()

	service := newProviderChatService(upstream.Client())
	cfg := deviceConfig{Provider: "openai", APIURL: upstream.URL, APIKey: key, Model: "gpt-test"}
	result, err := service.complete(context.Background(), cfg, map[string]any{"messages": []any{map[string]any{"role": "user", "content": "hello"}}}, providerChatOptions{OpenAICompatibleResponse: true})
	if err != nil {
		t.Fatal(err)
	}
	if result.JSON["id"] != "cmpl-raw" || result.JSON["success"] != nil {
		t.Fatalf("expected raw OpenAI-compatible JSON, got %#v", result.JSON)
	}
	if strings.Contains(mustJSON(t, result.JSON), key) {
		t.Fatalf("raw response leaked key: %#v", result.JSON)
	}
}

func TestProviderChatErrorBodyIsStructuredAndRedacted(t *testing.T) {
	key := "sk-error-secret-abcdef"
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"error":"bad key","api_key":"` + key + `","message":"Authorization Bearer ` + key + `"}`))
	}))
	defer upstream.Close()

	service := newProviderChatService(upstream.Client())
	cfg := deviceConfig{Provider: "deepseek", APIURL: upstream.URL, APIKey: key, Model: "deepseek-chat"}
	result, err := service.complete(context.Background(), cfg, map[string]any{"message": "hello"}, providerChatOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if result.StatusCode != http.StatusUnauthorized {
		t.Fatalf("status=%d json=%#v", result.StatusCode, result.JSON)
	}
	rendered := mustJSON(t, result.JSON)
	if strings.Contains(rendered, key) || strings.Contains(rendered, `"api_key":"`+key+`"`) {
		t.Fatalf("error response leaked key: %s", rendered)
	}
	if result.JSON["success"] != false || result.JSON["error"] != "provider_error" {
		t.Fatalf("error response not structured: %#v", result.JSON)
	}
}

func TestProviderChatSSEAdapterAndRedaction(t *testing.T) {
	key := "sk-stream-secret-abcdef"
	var streamRequested bool
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		streamRequested, _ = payload["stream"].(bool)
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"hel\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"lo\"}}],\"api_key\":\"" + key + "\"}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer upstream.Close()

	service := newProviderChatService(upstream.Client())
	cfg := deviceConfig{Provider: "kimi", APIURL: upstream.URL, APIKey: key, Model: "kimi-k2.6"}
	result, err := service.complete(context.Background(), cfg, map[string]any{"message": "hello"}, providerChatOptions{Stream: true})
	if err != nil {
		t.Fatal(err)
	}
	if !streamRequested {
		t.Fatalf("upstream stream flag was not set")
	}
	if len(result.Events) != 3 {
		t.Fatalf("expected 3 SSE events, got %#v", result.Events)
	}
	if result.Events[0]["delta"] != "hel" || result.Events[1]["delta"] != "lo" || result.Events[2]["type"] != "done" {
		t.Fatalf("unexpected SSE adaptation: %#v", result.Events)
	}
	rendered := mustJSON(t, result.Events)
	if strings.Contains(rendered, key) {
		t.Fatalf("SSE events leaked key: %s", rendered)
	}
}

func TestProviderChatMissingConfigAndMessageAreStructured(t *testing.T) {
	service := newProviderChatService(nil)
	result, err := service.complete(context.Background(), deviceConfig{Provider: "kimi", Model: "kimi-k2.6"}, map[string]any{"message": "hello"}, providerChatOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if result.StatusCode != http.StatusServiceUnavailable || result.JSON["error"] != "missing_api_key" {
		t.Fatalf("missing key response not structured: %#v", result.JSON)
	}

	result, err = service.complete(context.Background(), deviceConfig{Provider: "kimi", APIURL: "https://api.moonshot.ai/v1", APIKey: "sk-test", Model: "kimi-k2.6"}, map[string]any{}, providerChatOptions{})
	if err != nil {
		t.Fatal(err)
	}
	if result.StatusCode != http.StatusBadRequest || result.JSON["error"] != "invalid_payload" {
		t.Fatalf("missing message response not structured: %#v", result.JSON)
	}
}

func TestProviderAPIURLValidationBlocksLocalAndPrivateTargets(t *testing.T) {
	for _, rawURL := range []string{
		"http://127.0.0.1:11434/v1",
		"http://localhost:11434/v1",
		"http://10.0.0.2/v1",
		"http://172.16.0.2/v1",
		"http://192.168.1.2/v1",
		"http://169.254.169.254/latest/meta-data",
		"file:///tmp/key",
	} {
		if err := pcsValidateProviderAPIURL(rawURL, false); err == nil {
			t.Fatalf("expected provider api url to be blocked: %s", rawURL)
		}
	}
	if err := pcsValidateProviderAPIURL("https://api.moonshot.ai/v1", false); err != nil {
		t.Fatalf("public provider api url was blocked: %v", err)
	}
	if err := pcsValidateProviderAPIURL("http://127.0.0.1:11434/v1", true); err != nil {
		t.Fatalf("local provider opt-in should allow loopback: %v", err)
	}
}

func mustJSON(t *testing.T, value any) string {
	t.Helper()
	b, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}
