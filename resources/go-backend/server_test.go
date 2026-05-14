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
	_, h := newTestServer(t)
	root := t.TempDir()
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
	_, h := newTestServer(t)
	root := t.TempDir()
	var body bytes.Buffer
	mw := multipart.NewWriter(&body)
	if err := mw.WriteField("workspace", root); err != nil {
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

func TestAgentRunSSEFallbackHasUnavailableDoneAborted(t *testing.T) {
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
	if frames[1]["type"] != "unavailable" || frames[1]["run_id"] != runID || frames[1]["success"] != false {
		t.Fatalf("unexpected unavailable frame: %#v", frames[1])
	}
	if frames[2]["type"] != "done" || frames[2]["done"] != true || frames[2]["status"] != "aborted" || frames[2]["aborted"] != true || frames[2]["success"] != false {
		t.Fatalf("unexpected done/aborted frame: %#v", frames[2])
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
	appDir := t.TempDir()
	assetDir := filepath.Join(appDir, "assets")
	if err := os.MkdirAll(assetDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(assetDir, "kaguya-header.png"), []byte("png"), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := NewServer(ServerConfig{RuntimeDir: t.TempDir(), AppDir: appDir})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, "/header-img", nil)
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK || rec.Body.String() != "png" {
		t.Fatalf("asset alias failed: status=%d body=%q", rec.Code, rec.Body.String())
	}
}
