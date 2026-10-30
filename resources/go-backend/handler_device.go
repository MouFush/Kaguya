package main

import (
    "net/http"
    "encoding/json"
    "os"
    "crypto/sha256"
    "io"
    "strings"
    "time"
    "fmt"
    "bytes"
    "errors"
    "path/filepath"
    "runtime"
    "context"
)

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

func (s *Server) roles(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"roles": []map[string]any{
			{"id": "kaguya", "name": "Kaguya", "description": "Default IDE assistant"},
			{"id": "coder", "name": "Coder", "description": "Code-focused assistant"},
			{"id": "analyst", "name": "Analyst", "description": "Research and analysis assistant"},
		},
	})
}

func (s *Server) prompts(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"prompts": []map[string]any{
			{"id": "code-review", "name": "Code Review", "category": "engineering"},
			{"id": "debug", "name": "Debug", "category": "engineering"},
			{"id": "document", "name": "Document", "category": "general"},
		},
	})
}

func (s *Server) loraList(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "loras": []any{}, "available": false, "reason": "lora_worker_not_configured"})
}

func (s *Server) apiVersion(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"name":    "KaguyaIDE",
		"version": "3.1.0-go-port",
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

func (s *Server) externalProviderChat(w http.ResponseWriter, r *http.Request, cfg deviceConfig, payload map[string]any) {
	if payload["messages"] == nil {
		message := firstString(payload, "message", "prompt", "input")
		if message == "" {
			writeError(w, http.StatusBadRequest, "missing_message", "messages or message is required")
			return
		}
		payload["messages"] = []map[string]any{{"role": "user", "content": message}}
	}
	if payload["model"] == nil || payload["model"] == "" {
		payload["model"] = cfg.Model
	}
	delete(payload, "api_key")
	delete(payload, "apiKey")
	delete(payload, "api_url")
	delete(payload, "apiUrl")
	delete(payload, "provider")

	reqBody, err := json.Marshal(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_payload", err.Error())
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 90*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, chatCompletionsURL(cfg.APIURL), bytes.NewReader(reqBody))
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_api_url", err.Error())
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+cfg.APIKey)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]any{
			"success":  false,
			"mode":     "go",
			"provider": cfg.Provider,
			"model":    cfg.Model,
			"error":    "provider_request_failed",
			"message":  err.Error(),
		})
		return
	}
	defer resp.Body.Close()
	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 16<<20))
	if resp.StatusCode >= 400 {
		writeJSON(w, resp.StatusCode, map[string]any{
			"success":       false,
			"mode":          "go",
			"provider":      cfg.Provider,
			"model":         cfg.Model,
			"error":         "provider_error",
			"status_code":   resp.StatusCode,
			"upstream_body": string(respBody),
		})
		return
	}
	var upstream map[string]any
	if err := json.Unmarshal(respBody, &upstream); err != nil {
		w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
		w.WriteHeader(resp.StatusCode)
		_, _ = w.Write(respBody)
		return
	}
	if r.URL.Path == "/chat/completions" {
		writeJSON(w, resp.StatusCode, upstream)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":  true,
		"mode":     "go",
		"provider": cfg.Provider,
		"model":    cfg.Model,
		"response": extractAssistantContent(upstream),
		"raw":      upstream,
	})
}

func (s *Server) featureFlags(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "features": map[string]any{"go_backend": true, "python_worker": s.proxy != nil}})
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
			"success":  false,
			"ok":       false,
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
		"success":  false,
		"ok":       false,
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

func (s *Server) deviceConfigPath() string {
	if s.devicePath != "" {
		return s.devicePath
	}
	return s.vaultPath()
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
