package main

import (
	"bytes"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

type ServerConfig struct {
	RuntimeDir string
	PythonURL  string
}

type Server struct {
	cfg         ServerConfig
	runtimeDir  string
	workspaceRoot string
	devicePath  string
	mu          sync.Mutex
	permissions permissionState
	proxy       http.Handler
}

type permissionState struct {
	Mode string `json:"mode"`
}

type deviceConfig struct {
	DeviceID string `json:"device_id,omitempty"`
	Provider string `json:"provider,omitempty"`
	APIURL   string `json:"api_url,omitempty"`
	APIKey   string `json:"api_key,omitempty"`
	Model    string `json:"model,omitempty"`
	Updated  string `json:"updated,omitempty"`
}

type DeviceVault struct {
	Provider string `json:"provider,omitempty"`
	APIKey   string `json:"api_key,omitempty"`
	APIURL   string `json:"api_url,omitempty"`
	Model    string `json:"model,omitempty"`
}

func NewServer(cfg ServerConfig) (*Server, error) {
	if cfg.RuntimeDir == "" {
		return nil, errors.New("runtime dir is required")
	}
	if err := os.MkdirAll(cfg.RuntimeDir, 0o700); err != nil {
		return nil, err
	}
	s := &Server{
		cfg:         cfg,
		runtimeDir:  cfg.RuntimeDir,
		workspaceRoot: filepath.Join(cfg.RuntimeDir, "workspaces"),
		devicePath:  filepath.Join(cfg.RuntimeDir, "device_vault.enc"),
		permissions: permissionState{Mode: "ask"},
	}
	if cfg.PythonURL != "" {
		u, err := url.Parse(cfg.PythonURL)
		if err != nil {
			return nil, err
		}
		s.proxy = httputil.NewSingleHostReverseProxy(u)
	}
	return s, nil
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/api/config", s.apiConfig)
	mux.HandleFunc("/api/model-status", s.modelStatus)
	mux.HandleFunc("/api/device/info", s.deviceInfo)
	mux.HandleFunc("/api/device/bind", s.deviceBind)
	mux.HandleFunc("/api/device/unbind", s.deviceUnbind)
	mux.HandleFunc("/api/account/saved-config", s.savedConfig)
	mux.HandleFunc("/api/account/auto-fill", s.autoFill)
	mux.HandleFunc("/models", s.models)
	mux.HandleFunc("/chat", s.chat)
	mux.HandleFunc("/api/chat", s.chat)
	mux.HandleFunc("/chat/completions", s.chatCompletions)
	mux.HandleFunc("/stream", s.stream)
	mux.HandleFunc("/agent/tasks", s.agentTasks)
	mux.HandleFunc("/agent/run", s.agentRun)
	mux.HandleFunc("/agent/abort", s.agentAbort)
	mux.HandleFunc("/agent/api-status", s.agentAPIStatus)
	mux.HandleFunc("/agent/api-test", s.agentAPITest)
	mux.HandleFunc("/rag/documents", s.ragDocuments)
	mux.HandleFunc("/kaguya/features/flags", s.featureFlags)
	mux.HandleFunc("/security/status", s.securityStatus)
	mux.HandleFunc("/external/config", s.externalConfig)
	mux.HandleFunc("/external/test", s.externalTest)
	mux.HandleFunc("/deepseek/test", s.deepseekTest)
	mux.HandleFunc("/deepseek/chat", s.deepseekChat)
	mux.HandleFunc("/permissions/status", s.permissionsStatus)
	mux.HandleFunc("/permissions/mode", s.permissionsMode)
	mux.HandleFunc("/permissions/check", s.permissionsCheck)
	mux.HandleFunc("/agent/file-tree", s.fileTree)
	mux.HandleFunc("/agent/read-file", s.readFile)
	mux.HandleFunc("/agent/write-file", s.writeFile)
	mux.HandleFunc("/agent/upload-device-files", s.uploadDeviceFiles)
	mux.HandleFunc("/agent/terminal/exec", s.terminalExec)
	mux.HandleFunc("/", s.proxyFallback)
	return withJSON(mux)
}

func withJSON(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		next.ServeHTTP(w, r)
	})
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success":           true,
		"ok":                true,
		"mode":              "go",
		"backend_available": s.proxy != nil,
		"runtime_dir":       s.cfg.RuntimeDir,
	})
}

func (s *Server) apiConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		s.deviceBind(w, r)
		return
	}
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, map[string]any{
		"success":        true,
		"mode":           "go",
		"runtime_dir":    s.cfg.RuntimeDir,
		"python_url":     s.cfg.PythonURL,
		"has_config":     cfg.APIKey != "",
		"provider":       cfg.Provider,
		"api_url":        cfg.APIURL,
		"apiUrl":         cfg.APIURL,
		"model":          cfg.Model,
		"masked_api_key": maskAPIKey(cfg.APIKey),
		"api_key":        maskAPIKey(cfg.APIKey),
		"apiKey":         maskAPIKey(cfg.APIKey),
	})
}

func (s *Server) modelStatus(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	available := cfg.APIKey != ""
	reason := "missing_api_key"
	if available {
		reason = "external_provider_configured"
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":                      true,
		"available":                    available,
		"mode":                         "go",
		"backend_available":            true,
		"python_worker_available":      s.proxy != nil,
		"external_provider_configured": available,
		"provider":                     cfg.Provider,
		"model":                        cfg.Model,
		"reason":                       reason,
	})
}

func (s *Server) deviceInfo(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"device": map[string]any{
			"device_id":            s.deviceID(),
			"device_name":          hostName(),
			"platform":             runtime.GOOS,
			"encryption_available": true,
			"encryption":           "aes-gcm-local",
			"vault_exists":         cfg.APIKey != "",
			"active_provider":      cfg.Provider,
			"api_url":              cfg.APIURL,
			"apiUrl":               cfg.APIURL,
			"model":                cfg.Model,
			"masked_api_key":       maskAPIKey(cfg.APIKey),
			"api_key":              maskAPIKey(cfg.APIKey),
			"apiKey":               maskAPIKey(cfg.APIKey),
			"runtime_dir":          s.cfg.RuntimeDir,
		},
	})
}

func (s *Server) deviceBind(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	existing, _ := s.loadDeviceConfig()
	next := deviceConfig{
		DeviceID: firstString(payload, "device_id", "deviceId"),
		Provider: firstString(payload, "provider"),
		APIURL:   firstString(payload, "api_url", "apiUrl"),
		APIKey:   firstString(payload, "api_key", "apiKey"),
		Model:    firstString(payload, "model"),
		Updated:  time.Now().UTC().Format(time.RFC3339),
	}
	normalizeProviderDefaults(&next)
	if next.DeviceID == "" {
		next.DeviceID = existing.DeviceID
	}
	if next.DeviceID == "" {
		next.DeviceID = s.deviceID()
	}
	if next.Provider == "" {
		next.Provider = existing.Provider
	}
	if next.APIURL == "" {
		next.APIURL = existing.APIURL
	}
	if next.APIKey == "" || next.APIKey == maskAPIKey(existing.APIKey) {
		next.APIKey = existing.APIKey
	}
	if next.Model == "" {
		next.Model = existing.Model
	}
	if next.APIKey == "" {
		writeError(w, http.StatusBadRequest, "missing_api_key", "api_key/apiKey is required")
		return
	}
	if err := s.saveDeviceConfig(next); err != nil {
		writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":        true,
		"ok":             true,
		"bound":          true,
		"device_id":      next.DeviceID,
		"provider":       next.Provider,
		"api_url":        next.APIURL,
		"apiUrl":         next.APIURL,
		"model":          next.Model,
		"masked_api_key": maskAPIKey(next.APIKey),
		"api_key":        maskAPIKey(next.APIKey),
		"apiKey":         maskAPIKey(next.APIKey),
		"encryption":     "aes-gcm-local",
	})
}

func (s *Server) deviceUnbind(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	if err := os.Remove(s.deviceConfigPath()); err != nil && !errors.Is(err, os.ErrNotExist) {
		writeError(w, http.StatusInternalServerError, "unbind_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "ok": true, "bound": false})
}

func (s *Server) savedConfig(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, maskedDevice(cfg))
}

func (s *Server) autoFill(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, map[string]any{
		"success":        true,
		"has_config":     cfg.APIKey != "",
		"available":      cfg.APIKey != "",
		"provider":       cfg.Provider,
		"api_url":        cfg.APIURL,
		"apiUrl":         cfg.APIURL,
		"model":          cfg.Model,
		"masked_api_key": maskAPIKey(cfg.APIKey),
		"api_key":        maskAPIKey(cfg.APIKey),
		"apiKey":         maskAPIKey(cfg.APIKey),
	})
}

func (s *Server) models(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	models := []map[string]any{}
	if cfg.APIKey != "" && cfg.Model != "" {
		models = append(models, map[string]any{"id": cfg.Model, "provider": cfg.Provider, "owned_by": cfg.Provider})
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "object": "list", "data": models, "models": models})
}

func (s *Server) chat(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	cfg, _ := s.loadDeviceConfig()
	if cfg.APIKey == "" {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"success": false,
			"mode":    "go",
			"error":   "backend_unavailable",
			"message": "Python backend is unavailable and no external provider is configured.",
		})
		return
	}
	writeJSON(w, http.StatusNotImplemented, map[string]any{
		"success": false,
		"mode":    "go",
		"error":   "external_provider_proxy_not_implemented",
		"message": "External provider configuration is saved, but chat proxy should run through the Python worker in this build.",
	})
}

func (s *Server) chatCompletions(w http.ResponseWriter, r *http.Request) {
	s.chat(w, r)
}

func (s *Server) stream(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	writeSSE(w,
		map[string]any{
			"type":      "unavailable",
			"success":   false,
			"available": false,
			"mode":      "go",
			"error":     "python_worker_unavailable",
			"message":   "Streaming chat requires the Python worker in this build.",
		},
		map[string]any{
			"type":      "done",
			"done":      true,
			"success":   false,
			"available": false,
			"status":    "unavailable",
			"mode":      "go",
		},
	)
}

func (s *Server) agentTasks(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "tasks": []any{}, "mode": "go"})
}

func (s *Server) agentRun(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	runID := "go-" + time.Now().UTC().Format("20060102150405.000000000")
	writeSSE(w,
		map[string]any{
			"type":    "run_started",
			"run_id":  runID,
			"success": false,
			"mode":    "go",
		},
		map[string]any{
			"type":      "unavailable",
			"run_id":    runID,
			"success":   false,
			"available": false,
			"error":     "python_worker_unavailable",
			"message":   "Agent execution is delegated to the Python worker.",
			"mode":      "go",
		},
		map[string]any{
			"type":      "done",
			"done":      true,
			"run_id":    runID,
			"success":   false,
			"available": false,
			"status":    "aborted",
			"aborted":   true,
			"error":     "python_worker_unavailable",
			"mode":      "go",
		},
	)
}

func (s *Server) ragDocuments(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "documents": []any{}, "mode": "go", "available": false, "reason": "python_worker_unavailable"})
}

func (s *Server) featureFlags(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "features": map[string]any{"go_backend": true, "python_worker": s.proxy != nil}})
}

func (s *Server) securityStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success":                 true,
		"mode":                    "go",
		"local_only":              true,
		"permission_service":      "go",
		"permission_mode":         s.permissions.Mode,
		"csrf_required_remote":    true,
		"terminal_shell_default":  false,
		"workspace_escape_denied": true,
	})
}

func (s *Server) externalConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		s.savedConfig(w, r)
		return
	}
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	s.deviceBind(w, r)
}

func (s *Server) externalTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	s.externalTestWithPayload(w, payload)
}

func (s *Server) deepseekTest(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	if firstString(payload, "provider") == "" {
		payload["provider"] = "deepseek"
	}
	if firstString(payload, "api_url", "apiUrl") == "" {
		payload["api_url"] = "https://api.deepseek.com/v1"
	}
	if firstString(payload, "model") == "" {
		payload["model"] = "deepseek-chat"
	}
	s.externalTestWithPayload(w, payload)
}

func (s *Server) externalTestWithPayload(w http.ResponseWriter, payload map[string]any) {
	cfg := s.normalizedConfig(payload)
	if cfg.APIKey == "" {
		writeJSON(w, http.StatusOK, map[string]any{
			"success": false,
			"ok":      false,
			"provider": cfg.Provider,
			"api_url":  cfg.APIURL,
			"apiUrl":   cfg.APIURL,
			"model":    cfg.Model,
			"error":    "missing_api_key",
			"message":  "No API key is configured.",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success": false,
		"ok":      false,
		"provider": cfg.Provider,
		"api_url":  cfg.APIURL,
		"apiUrl":   cfg.APIURL,
		"model":    cfg.Model,
		"error":    "network_test_not_implemented",
		"message":  "The Go facade validates configuration shape; live provider tests are delegated to the Python worker.",
	})
}

func (s *Server) deepseekChat(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	cfg, _ := s.loadDeviceConfig()
	if !strings.EqualFold(cfg.Provider, "deepseek") {
		cfg = deviceConfig{}
	}
	cfg.Provider = "deepseek"
	normalizeProviderDefaults(&cfg)
	writeJSON(w, http.StatusServiceUnavailable, map[string]any{
		"success":   false,
		"available": false,
		"mode":      "go",
		"provider":  cfg.Provider,
		"api_url":   cfg.APIURL,
		"apiUrl":    cfg.APIURL,
		"model":     cfg.Model,
		"error":     "python_worker_unavailable",
		"message":   "DeepSeek chat requires the Python worker in this build.",
	})
}

func (s *Server) agentAPIStatus(w http.ResponseWriter, r *http.Request) {
	s.modelStatus(w, r)
}

func (s *Server) agentAPITest(w http.ResponseWriter, r *http.Request) {
	s.externalTest(w, r)
}

func (s *Server) agentAbort(w http.ResponseWriter, r *http.Request) {
	var payload map[string]any
	body, _ := io.ReadAll(io.LimitReader(r.Body, 8<<20))
	_ = r.Body.Close()
	_ = json.Unmarshal(body, &payload)
	runID := firstString(payload, "run_id", "runId")
	if runID == "" {
		writeError(w, http.StatusBadRequest, "missing_run_id", "run_id is required")
		return
	}
	if s.proxy != nil {
		r.Body = io.NopCloser(bytes.NewReader(body))
		s.proxy.ServeHTTP(w, r)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": false, "run_id": runID, "aborted": false, "error": "run_not_found"})
}

func (s *Server) permissionsStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode": s.permissions.Mode,
		"ok":   true,
	})
}

func (s *Server) permissionsMode(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		s.permissionsStatus(w, r)
		return
	}
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	mode := firstString(payload, "mode")
	switch mode {
	case "ask", "allow", "deny":
		s.permissions.Mode = mode
		writeJSON(w, http.StatusOK, map[string]any{"ok": true, "mode": mode})
	default:
		writeError(w, http.StatusBadRequest, "invalid_mode", "mode must be ask, allow, or deny")
	}
}

func (s *Server) permissionsCheck(w http.ResponseWriter, r *http.Request) {
	allowed := s.permissions.Mode == "allow"
	tool := "unknown"
	var payload map[string]any
	if err := readJSON(r, &payload); err == nil {
		if v := firstString(payload, "tool_name", "toolName"); v != "" {
			tool = v
		}
	}
	risk := classifyTool(tool)
	writeJSON(w, http.StatusOK, map[string]any{
		"success":               true,
		"allowed":               allowed || risk == "low",
		"auto_approved":         allowed || risk == "low",
		"requires_confirmation": !(allowed || risk == "low"),
		"mode":                  s.permissions.Mode,
		"tool_name":             tool,
		"risk_level":            risk,
		"reason":                "go permission service",
	})
}

func (s *Server) fileTree(w http.ResponseWriter, r *http.Request) {
	root, rel, err := workspaceAndPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	entries, err := os.ReadDir(target)
	if err != nil {
		writeError(w, http.StatusBadRequest, "read_dir_failed", err.Error())
		return
	}
	type entry struct {
		Name  string `json:"name"`
		Path  string `json:"path"`
		IsDir bool   `json:"is_dir"`
		Size  int64  `json:"size,omitempty"`
	}
	items := make([]entry, 0, len(entries))
	for _, e := range entries {
		info, _ := e.Info()
		size := int64(0)
		if info != nil {
			size = info.Size()
		}
		childRel, _ := filepath.Rel(root, filepath.Join(target, e.Name()))
		items = append(items, entry{Name: e.Name(), Path: filepath.ToSlash(childRel), IsDir: e.IsDir(), Size: size})
	}
	sort.Slice(items, func(i, j int) bool {
		if items[i].IsDir != items[j].IsDir {
			return items[i].IsDir
		}
		return strings.ToLower(items[i].Name) < strings.ToLower(items[j].Name)
	})
	writeJSON(w, http.StatusOK, map[string]any{"root": root, "path": filepath.ToSlash(rel), "entries": items})
}

func (s *Server) readFile(w http.ResponseWriter, r *http.Request) {
	root, rel, err := workspaceAndPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	b, err := os.ReadFile(target)
	if err != nil {
		writeError(w, http.StatusBadRequest, "read_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"path": filepath.ToSlash(rel), "content": string(b)})
}

func (s *Server) writeFile(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodPut {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	root, err := workspaceRoot(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	rel := firstString(payload, "path", "file_path", "filePath")
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	content := firstString(payload, "content")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		writeError(w, http.StatusInternalServerError, "mkdir_failed", err.Error())
		return
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		writeError(w, http.StatusInternalServerError, "write_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "path": filepath.ToSlash(rel)})
}

func (s *Server) uploadDeviceFiles(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	if err := r.ParseMultipartForm(128 << 20); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_multipart", err.Error())
		return
	}
	rootRaw := r.FormValue("workspace")
	if rootRaw == "" {
		rootRaw = r.FormValue("workspace_root")
	}
	root, err := normalizeRoot(rootRaw)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	count := 0
	for _, headers := range r.MultipartForm.File {
		for _, header := range headers {
			if err := s.saveUploadedFile(root, header); err != nil {
				writeError(w, http.StatusForbidden, "upload_failed", err.Error())
				return
			}
			count++
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "uploaded": count})
}

func (s *Server) saveUploadedFile(root string, header *multipart.FileHeader) error {
	src, err := header.Open()
	if err != nil {
		return err
	}
	defer src.Close()
	name := filepath.Clean(filepath.FromSlash(header.Filename))
	if filepath.IsAbs(name) {
		name = filepath.Base(name)
	}
	target, err := safeJoin(root, name)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	dst, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer dst.Close()
	_, err = io.Copy(dst, src)
	return err
}

func (s *Server) terminalExec(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	argv := commandArgs(payload["command"])
	if len(argv) == 0 {
		argv = commandArgs(payload["argv"])
	}
	if len(argv) == 0 {
		writeError(w, http.StatusBadRequest, "missing_command", "command or argv is required")
		return
	}
	risk := classifyCommand(strings.Join(argv, " "))
	if reason := dangerousCommand(argv); reason != "" {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": reason})
		writeError(w, http.StatusForbidden, "dangerous_command", reason)
		return
	}
	if risk == "high" || risk == "critical" {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": "permission_required"})
		writeError(w, http.StatusForbidden, "permission_required", "high risk commands require explicit permission")
		return
	}
	root, err := workspaceRoot(payload)
	if err != nil {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": err.Error()})
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	cwd := firstString(payload, "cwd")
	if cwd == "" {
		cwd = root
	}
	cwd, err = safeJoin(root, cwd)
	if err != nil {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "working_dir": cwd, "reason": err.Error()})
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	timeout := 30 * time.Second
	ctx, cancel := context.WithTimeout(r.Context(), timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, argv[0], argv[1:]...)
	cmd.Dir = cwd
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	exitCode := 0
	if err != nil {
		exitCode = 1
		var ee *exec.ExitError
		if errors.As(err, &ee) {
			exitCode = ee.ExitCode()
		}
	}
	timedOut := ctx.Err() == context.DeadlineExceeded
	s.audit("terminal_exec", map[string]any{"allowed": true, "risk_level": risk, "command": argv, "working_dir": cwd, "exit_code": exitCode, "timeout": timedOut})
	writeJSON(w, http.StatusOK, map[string]any{
		"success":   err == nil && !timedOut,
		"ok":        err == nil && !timedOut,
		"exit_code": exitCode,
		"stdout":    stdout.String(),
		"stderr":    stderr.String(),
		"shell":     false,
		"risk_level": risk,
		"timeout":   timedOut,
	})
}

func (s *Server) proxyFallback(w http.ResponseWriter, r *http.Request) {
	if s.proxy == nil {
		if r.URL.Path == "/" {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte("<!doctype html><meta charset=\"utf-8\"><title>Kaguya Go Backend</title><h1>Kaguya Go Backend</h1><p>Core APIs are online. Python compatibility worker is unavailable.</p>"))
			return
		}
		writeError(w, http.StatusServiceUnavailable, "python_worker_unavailable", "route is implemented by the Python worker")
		return
	}
	s.proxy.ServeHTTP(w, r)
}

func (s *Server) loadDeviceConfig() (deviceConfig, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	b, err := os.ReadFile(s.deviceConfigPath())
	if err != nil {
		return deviceConfig{}, err
	}
	b, err = decryptLocal(s.runtimeDir, b)
	if err != nil {
		return deviceConfig{}, err
	}
	var cfg deviceConfig
	if err := json.Unmarshal(b, &cfg); err != nil {
		return deviceConfig{}, err
	}
	return cfg, nil
}

func (s *Server) saveDeviceConfig(cfg deviceConfig) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	path := s.deviceConfigPath()
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	b, err = encryptLocal(s.runtimeDir, b)
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o600)
}

func (s *Server) workspaceFor(deviceID string) string {
	root := s.workspaceRoot
	if root == "" {
		root = filepath.Join(s.runtimeDir, "workspaces")
	}
	if deviceID == "" {
		deviceID = "default"
	}
	name := filepath.Base(filepath.Clean(deviceID))
	path := filepath.Join(root, name)
	_ = os.MkdirAll(path, 0o755)
	return path
}

func (s *Server) authorize(deviceID, requested string, forWrite bool) (string, error) {
	root := s.workspaceFor(deviceID)
	target, err := safeJoin(root, requested)
	if err != nil {
		return "", err
	}
	if forWrite {
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return "", err
		}
	}
	return target, nil
}

func (s *Server) vaultPath() string {
	root := s.runtimeDir
	if root == "" {
		root = s.cfg.RuntimeDir
	}
	return filepath.Join(root, "device_vault.enc")
}

func (s *Server) deviceConfigPath() string {
	if s.devicePath != "" {
		return s.devicePath
	}
	return s.vaultPath()
}

func (s *Server) saveVault(v DeviceVault) error {
	return s.saveDeviceConfig(deviceConfig{DeviceID: s.deviceID(), Provider: v.Provider, APIURL: v.APIURL, APIKey: v.APIKey, Model: v.Model, Updated: time.Now().UTC().Format(time.RFC3339)})
}

func (s *Server) loadVault() (DeviceVault, error) {
	cfg, err := s.loadDeviceConfig()
	if err != nil {
		return DeviceVault{}, err
	}
	return DeviceVault{Provider: cfg.Provider, APIURL: cfg.APIURL, APIKey: cfg.APIKey, Model: cfg.Model}, nil
}

func workspaceAndPath(r *http.Request) (string, string, error) {
	if r.Method == http.MethodGet {
		root := r.URL.Query().Get("workspace")
		if root == "" {
			root = r.URL.Query().Get("workspace_root")
		}
		normalized, err := normalizeRoot(root)
		if err != nil {
			return "", "", err
		}
		return normalized, r.URL.Query().Get("path"), nil
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		return "", "", err
	}
	root, err := workspaceRoot(payload)
	if err != nil {
		return "", "", err
	}
	return root, firstString(payload, "path", "file_path", "filePath"), nil
}

func workspaceRoot(payload map[string]any) (string, error) {
	root := firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root")
	return normalizeRoot(root)
}

func normalizeRoot(root string) (string, error) {
	if root == "" {
		wd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		root = wd
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	real, err := filepath.EvalSymlinks(abs)
	if err != nil {
		return "", err
	}
	return filepath.Clean(real), nil
}

func encryptLocal(runtimeDir string, plain []byte) ([]byte, error) {
	block, err := aes.NewCipher(localKey(runtimeDir))
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	raw := gcm.Seal(nonce, nonce, plain, nil)
	return []byte(base64.StdEncoding.EncodeToString(raw)), nil
}

func decryptLocal(runtimeDir string, encoded []byte) ([]byte, error) {
	raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(string(encoded)))
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(localKey(runtimeDir))
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(raw) < gcm.NonceSize() {
		return nil, errors.New("vault too short")
	}
	return gcm.Open(nil, raw[:gcm.NonceSize()], raw[gcm.NonceSize():], nil)
}

func localKey(runtimeDir string) []byte {
	current, _ := user.Current()
	username := ""
	if current != nil {
		username = current.Username
	}
	sum := sha256.Sum256([]byte(filepath.Clean(runtimeDir) + "|" + hostName() + "|" + runtime.GOOS + "|" + username))
	return sum[:]
}

func safeJoin(root, rel string) (string, error) {
	root, err := normalizeRoot(root)
	if err != nil {
		return "", err
	}
	if rel == "" || rel == "." {
		return root, nil
	}
	candidate := filepath.Clean(filepath.FromSlash(rel))
	if filepath.IsAbs(candidate) {
		candidate = filepath.Clean(candidate)
	} else {
		candidate = filepath.Join(root, candidate)
	}
	abs, err := filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	final, err := realCandidate(abs)
	if err != nil {
		return "", err
	}
	if !commonPath(root, final) {
		return "", fmt.Errorf("%s is outside workspace %s", final, root)
	}
	return final, nil
}

func realCandidate(abs string) (string, error) {
	current := filepath.Clean(abs)
	missing := []string{}
	for {
		if _, err := os.Lstat(current); err == nil {
			realBase, err := filepath.EvalSymlinks(current)
			if err != nil {
				return "", err
			}
			for i := len(missing) - 1; i >= 0; i-- {
				realBase = filepath.Join(realBase, missing[i])
			}
			return realBase, nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("no existing path component for %s", abs)
		}
		missing = append(missing, filepath.Base(current))
		current = parent
	}
}

func commonPath(root, target string) bool {
	root = filepath.Clean(strings.ToLower(root))
	target = filepath.Clean(strings.ToLower(target))
	if runtime.GOOS == "windows" {
		root = strings.TrimRight(root, `\`)
		return target == root || strings.HasPrefix(target, root+`\`)
	}
	root = strings.TrimRight(root, `/`)
	return target == root || strings.HasPrefix(target, root+`/`)
}

func dangerousCommand(argv []string) string {
	base := strings.ToLower(filepath.Base(argv[0]))
	base = strings.TrimSuffix(base, ".exe")
	blocked := map[string]bool{
		"rm": true, "del": true, "erase": true, "rmdir": true, "rd": true,
		"remove-item": true, "ri": true, "move-item": true,
		"format": true, "diskpart": true, "shutdown": true, "reboot": true,
		"mkfs": true, "dd": true, "reg": true, "takeown": true, "icacls": true,
	}
	if blocked[base] {
		return "refusing destructive command " + base
	}
	joined := strings.ToLower(strings.Join(argv, " "))
	for _, token := range []string{"&&", "||", ";", "`", "$(", ">", "<", "|"} {
		if strings.Contains(joined, token) {
			return "shell metacharacters are not allowed"
		}
	}
	return ""
}

func classifyCommand(command string) string {
	argv := strings.Fields(command)
	if len(argv) == 0 {
		return "low"
	}
	base := strings.ToLower(filepath.Base(argv[0]))
	base = strings.TrimSuffix(base, ".exe")
	if len(argv) == 2 && (argv[1] == "--version" || argv[1] == "-v" || argv[1] == "version") {
		return "low"
	}
	switch base {
	case "rm", "del", "erase", "rmdir", "rd", "remove-item", "ri", "format", "diskpart", "shutdown", "reboot", "mkfs", "dd":
		return "critical"
	case "pip", "pip3", "curl", "wget":
		return "high"
	case "python", "python3", "py", "powershell", "pwsh", "cmd", "bash", "sh", "node":
		return "high"
	case "npm":
		if len(argv) > 1 && (argv[1] == "test" || argv[1] == "run") {
			return "medium"
		}
		return "high"
	default:
		if dangerousCommand(argv) != "" {
			return "critical"
		}
		return "low"
	}
}

func classifyTool(tool string) string {
	t := strings.ToLower(tool)
	switch {
	case strings.Contains(t, "delete") || strings.Contains(t, "terminal") || strings.Contains(t, "execute") || strings.Contains(t, "run_project"):
		return "high"
	case strings.Contains(t, "write") || strings.Contains(t, "upload") || strings.Contains(t, "import"):
		return "medium"
	default:
		return "low"
	}
}

func commandArgs(v any) []string {
	switch x := v.(type) {
	case string:
		return strings.Fields(x)
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			if s, ok := item.(string); ok && s != "" {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return x
	default:
		return nil
	}
}

func firstString(payload map[string]any, keys ...string) string {
	for _, key := range keys {
		if v, ok := payload[key]; ok {
			if s, ok := v.(string); ok {
				return s
			}
		}
	}
	return ""
}

func maskAPIKey(key string) string {
	if key == "" {
		return ""
	}
	if len(key) <= 8 {
		return strings.Repeat("*", len(key))
	}
	return key[:4] + strings.Repeat("*", len(key)-8) + key[len(key)-4:]
}

func maskedDevice(cfg deviceConfig) map[string]any {
	return map[string]any{
		"success":        true,
		"has_config":     cfg.APIKey != "",
		"device_id":      cfg.DeviceID,
		"provider":       cfg.Provider,
		"api_url":        cfg.APIURL,
		"apiUrl":         cfg.APIURL,
		"model":          cfg.Model,
		"masked_api_key": maskAPIKey(cfg.APIKey),
		"api_key":        maskAPIKey(cfg.APIKey),
		"apiKey":         maskAPIKey(cfg.APIKey),
		"bound":          cfg.APIKey != "",
		"updated":        cfg.Updated,
	}
}

func normalizeProviderDefaults(cfg *deviceConfig) {
	provider := strings.ToLower(cfg.Provider)
	if provider == "kimi" || provider == "moonshot" || strings.Contains(provider, "kimi") {
		if cfg.APIURL == "" {
			cfg.APIURL = "https://api.moonshot.ai/v1"
		}
		if cfg.Model == "" {
			cfg.Model = "kimi-k2.6"
		}
	}
	if provider == "openai" && cfg.APIURL == "" {
		cfg.APIURL = "https://api.openai.com/v1"
	}
	if provider == "deepseek" {
		if cfg.APIURL == "" {
			cfg.APIURL = "https://api.deepseek.com/v1"
		}
		if cfg.Model == "" {
			cfg.Model = "deepseek-chat"
		}
	}
}

func (s *Server) normalizedConfig(payload map[string]any) deviceConfig {
	if payload == nil {
		payload = map[string]any{}
	}
	existing, _ := s.loadDeviceConfig()
	cfg := deviceConfig{
		DeviceID: firstString(payload, "device_id", "deviceId"),
		Provider: firstString(payload, "provider"),
		APIURL:   firstString(payload, "api_url", "apiUrl"),
		APIKey:   firstString(payload, "api_key", "apiKey"),
		Model:    firstString(payload, "model"),
		Updated:  time.Now().UTC().Format(time.RFC3339),
	}
	if nested, ok := payload["external_api"].(map[string]any); ok {
		n := s.normalizedConfig(nested)
		if cfg.Provider == "" {
			cfg.Provider = n.Provider
		}
		if cfg.APIURL == "" {
			cfg.APIURL = n.APIURL
		}
		if cfg.APIKey == "" {
			cfg.APIKey = n.APIKey
		}
		if cfg.Model == "" {
			cfg.Model = n.Model
		}
	}
	if cfg.DeviceID == "" {
		cfg.DeviceID = existing.DeviceID
	}
	if cfg.DeviceID == "" {
		cfg.DeviceID = s.deviceID()
	}
	if cfg.Provider == "" {
		cfg.Provider = existing.Provider
	}
	if cfg.APIURL == "" {
		cfg.APIURL = existing.APIURL
	}
	if cfg.APIKey == "" || cfg.APIKey == maskAPIKey(existing.APIKey) {
		cfg.APIKey = existing.APIKey
	}
	if cfg.Model == "" {
		cfg.Model = existing.Model
	}
	normalizeProviderDefaults(&cfg)
	return cfg
}

func (s *Server) deviceID() string {
	sum := sha256.Sum256([]byte(filepath.Clean(s.runtimeDir) + "|" + hostName() + "|" + runtime.GOOS))
	return fmt.Sprintf("dev-%x", sum[:8])
}

func hostName() string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return "desktop"
	}
	return name
}

func (s *Server) audit(action string, fields map[string]any) {
	fields["action"] = action
	fields["ts"] = time.Now().UTC().Format(time.RFC3339)
	dir := filepath.Join(s.runtimeDir, "audit_logs")
	_ = os.MkdirAll(dir, 0o700)
	b, _ := json.Marshal(fields)
	f, err := os.OpenFile(filepath.Join(dir, "go_audit.jsonl"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return
	}
	defer f.Close()
	_, _ = f.Write(append(b, '\n'))
}

func readJSON(r *http.Request, dst any) error {
	defer r.Body.Close()
	dec := json.NewDecoder(io.LimitReader(r.Body, 8<<20))
	dec.UseNumber()
	return dec.Decode(dst)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeSSE(w http.ResponseWriter, frames ...map[string]any) {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	for _, frame := range frames {
		b, err := json.Marshal(frame)
		if err != nil {
			continue
		}
		_, _ = fmt.Fprintf(w, "data: %s\n\n", b)
	}
	if f, ok := w.(http.Flusher); ok {
		f.Flush()
	}
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	writeJSON(w, status, map[string]any{"ok": false, "error": code, "message": message})
}

func methodNotAllowed(w http.ResponseWriter) {
	writeError(w, http.StatusMethodNotAllowed, "method_not_allowed", "method not allowed")
}
