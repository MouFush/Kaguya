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
