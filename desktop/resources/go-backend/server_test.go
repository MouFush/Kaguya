package main

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) (*Server, http.Handler) {
	t.Helper()
	s, err := NewServer(ServerConfig{RuntimeDir: t.TempDir()})
	if err != nil {
		t.Fatal(err)
	}
	return s, s.Handler()
}

func requestJSON(t *testing.T, h http.Handler, method, path string, payload any) *httptest.ResponseRecorder {
	t.Helper()
	var body bytes.Buffer
	if payload != nil {
		if err := json.NewEncoder(&body).Encode(payload); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &body)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBody(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var got map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode body: %v: %s", err, rec.Body.String())
	}
	return got
}

func decodeSSEFrames(t *testing.T, rec *httptest.ResponseRecorder) []map[string]any {
	t.Helper()
	parts := strings.Split(rec.Body.String(), "\n\n")
	frames := []map[string]any{}
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		if !strings.HasPrefix(part, "data: ") {
			t.Fatalf("unexpected SSE frame %q", part)
		}
		var frame map[string]any
		if err := json.Unmarshal([]byte(strings.TrimPrefix(part, "data: ")), &frame); err != nil {
			t.Fatalf("decode SSE frame: %v: %s", err, part)
		}
		frames = append(frames, frame)
	}
	return frames
}

func TestDeviceBindMasksAndPersistsAPIKey(t *testing.T) {
	s, h := newTestServer(t)
	key := "sk-1234567890abcdef"
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{
		"deviceId": "dev-1",
		"provider": "moonshot",
		"apiUrl":   "https://api.moonshot.ai/v1",
		"apiKey":   key,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	got := decodeBody(t, rec)
	if got["api_key"] == key {
		t.Fatal("response returned cleartext api key")
	}
	raw, err := os.ReadFile(s.devicePath)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(raw), key) {
		t.Fatal("vault leaked cleartext api key")
	}
	rec = requestJSON(t, h, http.MethodGet, "/api/account/saved-config", nil)
	if strings.Contains(rec.Body.String(), key) {
		t.Fatalf("saved-config leaked cleartext key: %s", rec.Body.String())
	}
}

func TestDeviceVaultSurvivesServerRestart(t *testing.T) {
	runtimeDir := t.TempDir()
	key := "sk-restart-secret-abcdef"
	s1, err := NewServer(ServerConfig{RuntimeDir: runtimeDir})
	if err != nil {
		t.Fatal(err)
	}
	h1 := s1.Handler()
	rec := requestJSON(t, h1, http.MethodPost, "/api/device/bind", map[string]any{
		"provider": "kimi",
		"apiKey":   key,
		"apiUrl":   "https://api.moonshot.ai/v1",
		"model":    "kimi-k2.6",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("bind status=%d body=%s", rec.Code, rec.Body.String())
	}

	s2, err := NewServer(ServerConfig{RuntimeDir: runtimeDir})
	if err != nil {
		t.Fatal(err)
	}
	h2 := s2.Handler()
	rec = requestJSON(t, h2, http.MethodGet, "/api/account/saved-config", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("saved-config status=%d body=%s", rec.Code, rec.Body.String())
	}
	got := decodeBody(t, rec)
	if got["has_config"] != true || got["provider"] != "kimi" || got["model"] != "kimi-k2.6" {
		t.Fatalf("saved config did not survive restart: %#v", got)
	}
	if strings.Contains(rec.Body.String(), key) {
		t.Fatalf("saved config leaked cleartext key after restart: %s", rec.Body.String())
	}
	rec = requestJSON(t, h2, http.MethodGet, "/api/model-status", nil)
	status := decodeBody(t, rec)
	if status["available"] != true || status["provider"] != "kimi" {
		t.Fatalf("model status did not use restored config: %#v", status)
	}
}

func TestMaskedRoundTripPreservesSavedKey(t *testing.T) {
	_, h := newTestServer(t)
	key := "sk-preserve-123456"
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{"api_key": key})
	masked := decodeBody(t, rec)["api_key"].(string)
	requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{"provider": "kimi", "api_key": masked})
	rec = requestJSON(t, h, http.MethodGet, "/api/account/auto-fill", nil)
	body := rec.Body.String()
	if strings.Contains(body, key) {
		t.Fatalf("auto-fill leaked cleartext key: %s", body)
	}
	if !strings.Contains(body, masked) {
		t.Fatalf("masked key was not preserved: %s", body)
	}
}

func TestExternalConfigAcceptsActiveProviderMap(t *testing.T) {
	_, h := newTestServer(t)
	key := "sk-external-map-abcdef"
	rec := requestJSON(t, h, http.MethodPost, "/external/config", map[string]any{
		"active_provider": "minimax",
		"providers": map[string]any{
			"kimi": map[string]any{
				"api_key": "sk-wrong-provider",
				"api_url": "https://api.moonshot.ai/v1",
				"model":   "kimi-k2.6",
			},
			"minimax": map[string]any{
				"apiKey": key,
				"apiUrl": "https://api.minimaxi.com/v1",
				"model":  "MiniMax-M2.7",
			},
		},
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("external config status=%d body=%s", rec.Code, rec.Body.String())
	}
	got := decodeBody(t, rec)
	if got["provider"] != "minimax" || got["model"] != "MiniMax-M2.7" {
		t.Fatalf("active provider map was not flattened: %#v", got)
	}
	if strings.Contains(rec.Body.String(), key) {
		t.Fatalf("external config leaked cleartext key: %s", rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/api/account/saved-config", nil)
	saved := decodeBody(t, rec)
	if saved["provider"] != "minimax" || saved["has_config"] != true {
		t.Fatalf("saved config did not use active provider: %#v", saved)
	}
}

func TestSafeJoinRejectsWorkspaceEscape(t *testing.T) {
	root := t.TempDir()
	if _, err := safeJoin(root, ".."); err == nil {
		t.Fatal("expected parent escape to be rejected")
	}
	outside := filepath.Join(t.TempDir(), "x.txt")
	if _, err := safeJoin(root, outside); err == nil {
		t.Fatal("expected absolute path outside workspace to be rejected")
	}
}

func TestReadWriteFileWithinWorkspace(t *testing.T) {
	s, h := newTestServer(t)
	root := s.workspace.WorkspaceRoot()
	rec := requestJSON(t, h, http.MethodPost, "/agent/write-file", map[string]any{
		"workspace": root,
		"path":      "nested/file.txt",
		"content":   "hello",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("write status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/agent/read-file", map[string]any{
		"workspace": root,
		"path":      "nested/file.txt",
	})
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "hello") {
		t.Fatalf("read failed status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestTerminalRejectsDangerousCommands(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/agent/terminal/exec", map[string]any{
		"workspace": t.TempDir(),
		"command":   []string{"rm", "-rf", "."},
	})
	if rec.Code != http.StatusForbidden {
		t.Fatalf("expected forbidden, got %d body=%s", rec.Code, rec.Body.String())
	}
}

func TestUnknownRouteProxiesToPythonWorker(t *testing.T) {
	worker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		w.WriteHeader(http.StatusTeapot)
		_, _ = w.Write([]byte(`{"proxied":true}`))
	}))
	defer worker.Close()
	s, err := NewServer(ServerConfig{RuntimeDir: t.TempDir(), PythonURL: worker.URL})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, "/chat", nil)
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusTeapot || !strings.Contains(rec.Body.String(), "proxied") {
		t.Fatalf("proxy failed status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestUploadDeviceFilesStaysInWorkspace(t *testing.T) {
	s, h := newTestServer(t)
	root := s.workspace.WorkspaceRoot()
	var body bytes.Buffer
	mw := multipart.NewWriter(&body)
	if err := mw.WriteField("workspace", root); err != nil {
		t.Fatal(err)
	}
	if err := mw.WriteField("paths", "dir/a.txt"); err != nil {
		t.Fatal(err)
	}
	part, err := mw.CreateFormFile("files", "dir/a.txt")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := io.WriteString(part, "uploaded"); err != nil {
		t.Fatal(err)
	}
	if err := mw.Close(); err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/agent/upload-device-files", &body)
	req.Header.Set("Content-Type", mw.FormDataContentType())
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("upload status=%d body=%s", rec.Code, rec.Body.String())
	}
	got, err := os.ReadFile(filepath.Join(root, "dir", "a.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "uploaded" {
		t.Fatalf("uploaded content=%q", string(got))
	}
}

func TestCoreFacadeRoutesWithoutPythonWorker(t *testing.T) {
	_, h := newTestServer(t)
	for _, item := range []struct {
		method string
		path   string
		body   any
	}{
		{http.MethodGet, "/security/status", nil},
		{http.MethodGet, "/agent/api-status", nil},
		{http.MethodGet, "/external/config", nil},
		{http.MethodPost, "/external/test", map[string]any{}},
		{http.MethodPost, "/deepseek/test", map[string]any{}},
		{http.MethodPost, "/agent/api-test", map[string]any{}},
		{http.MethodGet, "/models", nil},
		{http.MethodGet, "/rag/documents", nil},
		{http.MethodGet, "/kaguya/features/flags", nil},
	} {
		rec := requestJSON(t, h, item.method, item.path, item.body)
		if rec.Code >= 500 {
			t.Fatalf("%s %s returned %d body=%s", item.method, item.path, rec.Code, rec.Body.String())
		}
		if !strings.Contains(rec.Header().Get("Content-Type"), "application/json") {
			t.Fatalf("%s %s did not return json", item.method, item.path)
		}
	}
}

func TestKimiDefaultsAndNoPlaintextResponse(t *testing.T) {
	_, h := newTestServer(t)
	key := "sk-kimi-secret-abcdef"
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{
		"provider": "kimi",
		"apiKey":   key,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	body := rec.Body.String()
	if strings.Contains(body, key) {
		t.Fatalf("response leaked key: %s", body)
	}
	if !strings.Contains(body, "api.moonshot.ai") || !strings.Contains(body, "kimi-k2.6") {
		t.Fatalf("kimi defaults missing: %s", body)
	}
	got := decodeBody(t, rec)
	if got["apiUrl"] == "" || got["apiKey"] == key {
		t.Fatalf("camelCase Kimi compatibility fields missing or leaked: %#v", got)
	}
	rec = requestJSON(t, h, http.MethodGet, "/external/config", nil)
	got = decodeBody(t, rec)
	if got["apiUrl"] == "" || got["apiKey"] == key || strings.Contains(rec.Body.String(), key) {
		t.Fatalf("external config compatibility fields missing or leaked: %s", rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/deepseek/chat", map[string]any{"messages": []any{}})
	got = decodeBody(t, rec)
	if got["provider"] != "deepseek" || !strings.Contains(got["apiUrl"].(string), "deepseek") {
		t.Fatalf("deepseek endpoint inherited Kimi config: %#v", got)
	}
}

func TestExternalProviderChatUsesSavedOpenAICompatibleConfig(t *testing.T) {
	var gotAuth, gotPath string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		gotPath = r.URL.Path
		var payload map[string]any
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		if payload["api_key"] != nil || payload["apiKey"] != nil {
			t.Fatalf("provider payload leaked api key: %#v", payload)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"cmpl-test","choices":[{"message":{"role":"assistant","content":"pong"}}]}`))
	}))
	defer upstream.Close()

	_, h := newTestServer(t)
	key := "sk-provider-secret"
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{
		"provider": "kimi",
		"api_url":  upstream.URL + "/v1",
		"api_key":  key,
		"model":    "kimi-k2.6",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("bind status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/api/chat", map[string]any{"message": "ping"})
	if rec.Code != http.StatusOK {
		t.Fatalf("chat status=%d body=%s", rec.Code, rec.Body.String())
	}
	if gotPath != "/v1/chat/completions" || gotAuth != "Bearer "+key {
		t.Fatalf("upstream path/auth mismatch path=%s auth=%s", gotPath, gotAuth)
	}
	body := rec.Body.String()
	if strings.Contains(body, key) || !strings.Contains(body, "pong") {
		t.Fatalf("chat response leaked key or missed content: %s", body)
	}
}

func TestAgentAPITestVerifiesKimiProviderWithoutLeakingKey(t *testing.T) {
	key := "sk-kimi-secret-abcdef"
	var gotPath, gotAuth string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"object":"list","data":[{"id":"kimi-k2.6"}]}`))
	}))
	defer upstream.Close()

	s, h := newTestServer(t)
	s.providerChat = newProviderChatService(upstream.Client())
	rec := requestJSON(t, h, http.MethodPost, "/agent/api-test", map[string]any{
		"provider": "kimi",
		"apiUrl":   upstream.URL + "/v1",
		"apiKey":   key,
		"model":    "kimi-k2.6",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	got := decodeBody(t, rec)
	if got["success"] != true || got["available"] != true || got["provider"] != "kimi" {
		t.Fatalf("unexpected provider test response: %#v", got)
	}
	if gotPath != "/v1/models" || gotAuth != "Bearer "+key {
		t.Fatalf("provider test path/auth mismatch path=%s auth=%s", gotPath, gotAuth)
	}
	if strings.Contains(rec.Body.String(), key) {
		t.Fatalf("provider test leaked api key: %s", rec.Body.String())
	}
}

func TestDeepSeekChatUsesGoProviderService(t *testing.T) {
	var gotAuth, gotPath string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		gotPath = r.URL.Path
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"deep pong"}}]}`))
	}))
	defer upstream.Close()

	_, h := newTestServer(t)
	key := "sk-deepseek-secret-abcdef"
	rec := requestJSON(t, h, http.MethodPost, "/deepseek/chat", map[string]any{
		"apiKey": key,
		"apiUrl": upstream.URL + "/v1",
		"messages": []map[string]any{{
			"role":    "user",
			"content": "ping",
		}},
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	if gotAuth != "Bearer "+key {
		t.Fatalf("auth header mismatch: %q", gotAuth)
	}
	if gotPath != "/v1/chat/completions" {
		t.Fatalf("path mismatch: %s", gotPath)
	}
	body := rec.Body.String()
	if strings.Contains(body, key) || strings.Contains(body, "python_worker"+"_"+"unavailable") {
		t.Fatalf("response leaked key or used worker fallback: %s", body)
	}
	decoded := decodeBody(t, rec)
	if decoded["provider"] != "deepseek" || decoded["response"] != "deep pong" {
		t.Fatalf("unexpected response: %#v", decoded)
	}
}

func TestServerStreamUsesProviderChatServiceWhenConfigured(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"hi\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer upstream.Close()

	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{
		"provider": "kimi",
		"api_url":  upstream.URL + "/v1",
		"api_key":  "sk-stream-secret",
		"model":    "kimi-k2.6",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("bind status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/stream", map[string]any{"message": "ping"})
	if rec.Code != http.StatusOK {
		t.Fatalf("stream status=%d body=%s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Header().Get("Content-Type"), "text/event-stream") {
		t.Fatalf("expected stream content type, got %s", rec.Header().Get("Content-Type"))
	}
	if strings.Contains(rec.Body.String(), "sk-stream-secret") || !strings.Contains(rec.Body.String(), "hi") {
		t.Fatalf("stream leaked key or missed content: %s", rec.Body.String())
	}
}

func TestServerAgentRuntimeBacksTasksAndAbort(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/agent/run", map[string]any{"message": "runtime smoke"})
	if rec.Code != http.StatusOK {
		t.Fatalf("agent run status=%d body=%s", rec.Code, rec.Body.String())
	}
	frames := decodeSSEFrames(t, rec)
	if len(frames) != 3 {
		t.Fatalf("expected 3 frames, got %#v", frames)
	}
	taskID, _ := frames[0]["task_id"].(string)
	if taskID == "" {
		t.Fatalf("run_started frame lacks task_id: %#v", frames[0])
	}
	rec = requestJSON(t, h, http.MethodGet, "/agent/tasks", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), taskID) {
		t.Fatalf("tasks did not include runtime task: status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/agent/tasks/tree", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), taskID) {
		t.Fatalf("task tree did not include runtime task: status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestAgentRunUsesGoProviderWhenConfigured(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"agent pong"}}]}`))
	}))
	defer upstream.Close()

	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/api/device/bind", map[string]any{
		"provider": "kimi",
		"api_url":  upstream.URL + "/v1",
		"api_key":  "sk-agent-secret",
		"model":    "kimi-k2.6",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("bind status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/agent/run", map[string]any{"message": "ping"})
	if rec.Code != http.StatusOK {
		t.Fatalf("agent run status=%d body=%s", rec.Code, rec.Body.String())
	}
	body := rec.Body.String()
	if strings.Contains(body, "sk-agent-secret") || strings.Contains(body, "agent_tools_unavailable") || !strings.Contains(body, "agent pong") {
		t.Fatalf("agent run did not use provider safely: %s", body)
	}
	frames := decodeSSEFrames(t, rec)
	if len(frames) != 3 || frames[1]["type"] != "message" || frames[2]["success"] != true {
		t.Fatalf("unexpected frames: %#v", frames)
	}
}

func TestProjectCommandUsesGoTerminalPermission(t *testing.T) {
	s, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/agent/compile", map[string]any{
		"workspace": s.workspace.WorkspaceRoot(),
		"command":   []string{"go", "test", "./..."},
	})
	if rec.Code != http.StatusForbidden {
		t.Fatalf("expected permission denial for medium-risk compile, got %d body=%s", rec.Code, rec.Body.String())
	}
	body := rec.Body.String()
	if strings.Contains(body, "Python") || strings.Contains(body, "worker") {
		t.Fatalf("project command still reports worker fallback: %s", body)
	}
	rec = requestJSON(t, h, http.MethodPost, "/permissions/mode", map[string]any{"mode": "allow"})
	if rec.Code != http.StatusOK {
		t.Fatalf("permission mode status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/agent/compile", map[string]any{
		"workspace": s.workspace.WorkspaceRoot(),
		"command":   []string{"go", "version"},
	})
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "go version") {
		t.Fatalf("allowed project command failed status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/agent/project-status", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "compile") {
		t.Fatalf("project status missing run record status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestServerSecurityAndPrivacyUseSecurityPrivacyService(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodGet, "/security/status", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "high_risk_remote_policy") {
		t.Fatalf("security status not service-backed: status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/privacy/settings", map[string]any{"retain_local_history": true, "retention_days": 3})
	if rec.Code != http.StatusOK {
		t.Fatalf("privacy save status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/privacy/settings", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "\"retention_days\":3") {
		t.Fatalf("privacy settings not persisted through service: status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestStreamSSEFallbackIsStructuredUnavailable(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/stream", map[string]any{"message": "hi"})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Header().Get("Content-Type"), "text/event-stream") {
		t.Fatalf("expected SSE content type, got %s", rec.Header().Get("Content-Type"))
	}
	frames := decodeSSEFrames(t, rec)
	if len(frames) != 2 {
		t.Fatalf("expected 2 frames, got %#v", frames)
	}
	if frames[0]["type"] != "unavailable" || frames[0]["success"] != false || frames[0]["available"] != false {
		t.Fatalf("unexpected unavailable frame: %#v", frames[0])
	}
	if frames[1]["type"] != "done" || frames[1]["done"] != true || frames[1]["status"] != "unavailable" || frames[1]["success"] != false {
		t.Fatalf("unexpected done frame: %#v", frames[1])
	}
}

func TestAgentRunSSEFallbackRequiresProviderConfig(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/agent/run", map[string]any{"message": "hi"})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	frames := decodeSSEFrames(t, rec)
	if len(frames) != 3 {
		t.Fatalf("expected 3 frames, got %#v", frames)
	}
	runID, _ := frames[0]["run_id"].(string)
	if frames[0]["type"] != "run_started" || runID == "" {
		t.Fatalf("missing run_started frame: %#v", frames[0])
	}
	if frames[1]["type"] != "unavailable" || frames[1]["run_id"] != runID || frames[1]["success"] != false || frames[1]["error"] != "missing_api_key" {
		t.Fatalf("unexpected unavailable frame: %#v", frames[1])
	}
	if frames[2]["type"] != "done" || frames[2]["done"] != true || frames[2]["status"] != "failed" || frames[2]["aborted"] != false || frames[2]["success"] != false {
		t.Fatalf("unexpected done/failed frame: %#v", frames[2])
	}
}

func TestDeepSeekFallbacksAreStructuredAndMasked(t *testing.T) {
	_, h := newTestServer(t)
	key := "sk-deepseek-secret-abcdef"
	rec := requestJSON(t, h, http.MethodPost, "/deepseek/test", map[string]any{"apiKey": key})
	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	if strings.Contains(rec.Body.String(), key) {
		t.Fatalf("deepseek test leaked key: %s", rec.Body.String())
	}
	got := decodeBody(t, rec)
	if got["success"] != false || got["provider"] != "deepseek" || got["apiUrl"] == "" || got["model"] == "" {
		t.Fatalf("unexpected deepseek test response: %#v", got)
	}
	rec = requestJSON(t, h, http.MethodPost, "/deepseek/chat", map[string]any{"messages": []any{}})
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status=%d body=%s", rec.Code, rec.Body.String())
	}
	got = decodeBody(t, rec)
	if got["success"] != false || got["available"] != false || got["provider"] != "deepseek" || got["apiUrl"] == "" {
		t.Fatalf("unexpected deepseek chat response: %#v", got)
	}
}

func TestServesExtractedIndexWithoutPythonWorker(t *testing.T) {
	dir := t.TempDir()
	staticDir := filepath.Join(dir, "static")
	if err := os.MkdirAll(staticDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(staticDir, "index.html"), []byte("<html>kaguya-go-index</html>"), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := NewServer(ServerConfig{RuntimeDir: t.TempDir(), StaticDir: staticDir})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "kaguya-go-index") {
		t.Fatalf("index not served by go backend: status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestAssetAliasesUseAppDir(t *testing.T) {
	rootDir := t.TempDir()
	appDir := filepath.Join(rootDir, "python-app")
	assetDir := filepath.Join(appDir, "assets")
	if err := os.MkdirAll(assetDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(assetDir, "kaguya-header.png"), []byte("png"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(assetDir, "kaguya-welcome.png"), []byte("welcome"), 0o644); err != nil {
		t.Fatal(err)
	}
	electronAssetDir := filepath.Join(rootDir, "app.asar.src", "assets")
	if err := os.MkdirAll(electronAssetDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(electronAssetDir, "kaguya.ico"), []byte("ico"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(electronAssetDir, "kaguya.png"), []byte("icon"), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := NewServer(ServerConfig{RuntimeDir: t.TempDir(), AppDir: appDir})
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		path string
		body string
	}{
		{path: "/header-img", body: "png"},
		{path: "/sidebar-icon", body: "icon"},
		{path: "/deepseek-icon", body: "welcome"},
		{path: "/favicon.ico", body: "ico"},
	} {
		req := httptest.NewRequest(http.MethodGet, tc.path, nil)
		rec := httptest.NewRecorder()
		s.Handler().ServeHTTP(rec, req)
		if rec.Code != http.StatusOK || rec.Body.String() != tc.body {
			t.Fatalf("%s asset alias failed: status=%d body=%q", tc.path, rec.Code, rec.Body.String())
		}
	}
}

func TestCollectionFacadePersistsProjectItems(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/project/tasks", map[string]any{"id": "task-1", "title": "Port module"})
	if rec.Code != http.StatusOK {
		t.Fatalf("post status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/project/tasks", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "Port module") {
		t.Fatalf("get status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestGoOwnedStatusFacades(t *testing.T) {
	_, h := newTestServer(t)
	for _, path := range []string{"/api/roles", "/api/prompts", "/api/version", "/account/profile", "/auth/setup", "/console/overview", "/system/metrics", "/services/health-check", "/git/status", "/security/ip-whitelist"} {
		rec := requestJSON(t, h, http.MethodGet, path, nil)
		if rec.Code >= 500 {
			t.Fatalf("%s status=%d body=%s", path, rec.Code, rec.Body.String())
		}
		if !strings.Contains(rec.Header().Get("Content-Type"), "application/json") {
			t.Fatalf("%s did not return json", path)
		}
	}
}

func TestKnowledgeBaseAddAndSearch(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/kb/add", map[string]any{"text": "Kaguya route migration note"})
	if rec.Code != http.StatusOK {
		t.Fatalf("kb add status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/kb/search", map[string]any{"query": "migration"})
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "Kaguya route migration note") {
		t.Fatalf("kb search status=%d body=%s", rec.Code, rec.Body.String())
	}
}

func TestPrivacySettingsPersistAndToolExecuteDenied(t *testing.T) {
	_, h := newTestServer(t)
	rec := requestJSON(t, h, http.MethodPost, "/privacy/settings", map[string]any{"telemetry": false, "crash_reports": false})
	if rec.Code != http.StatusOK {
		t.Fatalf("privacy write status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/privacy/settings", nil)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), "telemetry") {
		t.Fatalf("privacy read status=%d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/tool/execute", map[string]any{"tool": "shell", "command": "rm -rf ."})
	if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "permission_required") {
		t.Fatalf("tool execute should be denied, status=%d body=%s", rec.Code, rec.Body.String())
	}
}
