package main

import (
    "net/http"
    "encoding/json"
    "io"
    "bytes"
)

func (s *Server) chat(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(io.LimitReader(r.Body, 8<<20))
	_ = r.Body.Close()
	if s.proxy != nil {
		r.Body = io.NopCloser(bytes.NewReader(body))
		s.proxy.ServeHTTP(w, r)
		return
	}
	var payload map[string]any
	_ = json.Unmarshal(body, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	cfg := pcsNormalizeExternalProviderConfig(payload, deviceConfig{})
	if cfg.APIKey == "" || cfg.APIURL == "" || cfg.Model == "" || cfg.Provider == "" {
		cfg = s.normalizedConfig(payload)
	}
	if cfg.APIKey == "" {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"success": false,
			"mode":    "go",
			"error":   "backend_unavailable",
			"message": "Python backend is unavailable and no external provider is configured.",
		})
		return
	}
	s.providerChat.serve(w, r, cfg, payload, providerChatOptions{OpenAICompatibleResponse: r.URL.Path == "/chat/completions"})
}

func (s *Server) chatCompletions(w http.ResponseWriter, r *http.Request) {
	s.chat(w, r)
}

func (s *Server) stream(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(io.LimitReader(r.Body, 8<<20))
	_ = r.Body.Close()
	if s.proxy != nil {
		r.Body = io.NopCloser(bytes.NewReader(body))
		s.proxy.ServeHTTP(w, r)
		return
	}
	var payload map[string]any
	_ = json.Unmarshal(body, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	cfg := s.normalizedConfig(payload)
	if cfg.APIKey != "" {
		s.providerChat.serve(w, r, cfg, payload, providerChatOptions{Stream: true})
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

func (s *Server) chatsExport(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"format":  "json",
		"chats":   []any{},
	})
}
