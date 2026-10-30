package main

import (
    "net/http"
    "os"
    "path/filepath"
    "time"
)

func (s *Server) accountProfile(w http.ResponseWriter, r *http.Request) {
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"account": map[string]any{
			"id":             s.deviceID(),
			"display_name":   "Local desktop user",
			"auth_required":  false,
			"provider":       cfg.Provider,
			"masked_api_key": maskAPIKey(cfg.APIKey),
		},
	})
}

func (s *Server) accountSessions(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"sessions": []map[string]any{{
			"id":         s.deviceID(),
			"type":       "desktop_loopback",
			"created_at": time.Now().UTC().Format(time.RFC3339),
		}},
	})
}

func (s *Server) accountTokens(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost || r.Method == http.MethodDelete {
		writeError(w, http.StatusServiceUnavailable, "auth_worker_unavailable", "token mutation requires the auth worker")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "tokens": []any{}})
}

func (s *Server) authLogin(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"auth":    "desktop_loopback",
		"message": "Desktop loopback mode does not require password login.",
	})
}

func (s *Server) authLogout(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "logged_out": true})
}

func (s *Server) authRegister(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "auth_worker_unavailable", "account registration requires the auth worker")
}

func (s *Server) authSetup(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success":        true,
		"mode":           "go",
		"setup_required": false,
		"auth_required":  false,
	})
}

func (s *Server) authToken(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"token":   "",
		"message": "No browser-readable auth token is issued in desktop loopback mode.",
	})
}

func (s *Server) authPasswordReset(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "auth_worker_unavailable", "password reset requires the auth worker")
}

func (s *Server) authAdminAccounts(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "accounts": []any{}})
		return
	}
	writeError(w, http.StatusServiceUnavailable, "auth_worker_unavailable", "account administration requires the auth worker")
}

func (s *Server) authAdminRole(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "auth_worker_unavailable", "role administration requires the auth worker")
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
