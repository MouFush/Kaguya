package main

import (
    "net/http"
)

func (s *Server) securityStatus(w http.ResponseWriter, r *http.Request) {
	status := s.securityPrivacy.SecurityStatus(SecurityRuntimeConfig{
		BindHost:              "127.0.0.1",
		DesktopMode:           true,
		AuthEnabled:           false,
		CSRFEnabled:           true,
		PermissionService:     "go",
		PermissionMode:        s.permissions.Mode,
		AuditLogging:          true,
		WorkspaceEscapeDenied: true,
		TerminalShellDefault:  false,
		BackendMode:           "go",
		PythonWorkerAvailable: s.proxy != nil,
		IPWhitelistMode:       IPWhitelistModeLoopbackOnly,
		IPWhitelist:           []string{"127.0.0.1", "::1"},
	})
	writeJSON(w, http.StatusOK, status)
}

func (s *Server) securityIPWhitelist(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success":   true,
		"mode":      "go",
		"enabled":   false,
		"mode_name": "loopback_only",
		"entries":   []string{"127.0.0.1", "::1"},
	})
}

func (s *Server) privacySettings(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		settings, err := s.securityPrivacy.LoadPrivacySettings()
		if err != nil {
			writeError(w, http.StatusInternalServerError, "load_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "settings": settings})
		return
	}
	if r.Method != http.MethodPost && r.Method != http.MethodPut {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	settings := PrivacySettings{
		ID:                 "settings",
		Telemetry:          boolValue(payload["telemetry"]),
		CrashReports:       boolValue(payload["crash_reports"]),
		Analytics:          boolValue(payload["analytics"]),
		ShareDiagnostics:   boolValue(payload["share_diagnostics"]),
		Personalization:    boolValue(payload["personalization"]),
		RetainLocalHistory: boolValue(payload["retain_local_history"]),
		RetentionDays:      intValue(payload["retention_days"]),
	}
	settings, err := s.securityPrivacy.SavePrivacySettings(settings)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "settings": settings})
}

func (s *Server) privacyExport(w http.ResponseWriter, r *http.Request) {
	bundle, err := s.securityPrivacy.PrivacyExport()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "privacy_export_failed", err.Error())
		return
	}
	cfg, _ := s.loadDeviceConfig()
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "export": bundle, "device": maskedDevice(cfg)})
}

func (s *Server) privacyDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	scopes := []string{}
	if raw, ok := payload["scopes"].([]any); ok {
		for _, item := range raw {
			if s, ok := item.(string); ok {
				scopes = append(scopes, s)
			}
		}
	}
	result, err := s.securityPrivacy.DeletePrivacyData(scopes...)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "privacy_delete_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}
