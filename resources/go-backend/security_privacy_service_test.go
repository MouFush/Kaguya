package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestSecurityPrivacyStatusReflectsLoopbackPolicy(t *testing.T) {
	svc, err := NewSecurityPrivacyService(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	status := svc.SecurityStatus(SecurityRuntimeConfig{
		BindHost:              "127.0.0.1",
		DesktopMode:           true,
		AuthEnabled:           false,
		CSRFEnabled:           true,
		PermissionService:     "go",
		PermissionMode:        "ask",
		AuditLogging:          true,
		WorkspaceEscapeDenied: true,
	})
	if !status.Success || !status.LocalOnly || !status.LoopbackOnly || status.RemoteAccessAllowed {
		t.Fatalf("unexpected loopback security status: %#v", status)
	}
	if !status.CSRFRequiredRemote || !status.AuthRequiredRemote {
		t.Fatalf("remote protections not reflected: %#v", status)
	}
}

func TestSecurityPrivacyRemoteHighRiskDenied(t *testing.T) {
	decision := DenyRemoteHighRisk(SecurityRequestContext{
		RemoteAddr:      "192.168.1.10:5000",
		Method:          http.MethodPost,
		Path:            "/agent/terminal/exec",
		RiskLevel:       RiskCritical,
		AuthEnabled:     false,
		CSRFEnabled:     true,
		IPWhitelistMode: IPWhitelistModeLoopbackOnly,
	})
	if decision.Allowed || decision.Error != SecurityErrorRemoteHighRiskDeny {
		t.Fatalf("remote high-risk request was not denied: %#v", decision)
	}
	if !decision.Remote || decision.Loopback {
		t.Fatalf("remote/loopback flags wrong: %#v", decision)
	}
}

func TestSecurityPrivacyLoopbackLowRiskAllowed(t *testing.T) {
	svc, err := NewSecurityPrivacyService(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	decision := svc.AssessRequest(SecurityRequestContext{
		RemoteAddr:      "127.0.0.1:54321",
		Method:          http.MethodGet,
		Path:            "/api/model-status",
		RiskLevel:       RiskLow,
		AuthEnabled:     false,
		CSRFEnabled:     true,
		IPWhitelistMode: IPWhitelistModeLoopbackOnly,
	})
	if !decision.Allowed || decision.RequiresAuth || decision.RequiresCSRF {
		t.Fatalf("loopback low-risk request should be allowed: %#v", decision)
	}
}

func TestSecurityPrivacySettingsPersistAndExport(t *testing.T) {
	svc, err := NewSecurityPrivacyService(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	saved, err := svc.SavePrivacySettings(PrivacySettings{
		Telemetry:          false,
		CrashReports:       false,
		Analytics:          false,
		ShareDiagnostics:   false,
		Personalization:    false,
		RetainLocalHistory: true,
		RetentionDays:      7,
	})
	if err != nil {
		t.Fatal(err)
	}
	if saved.ID == "" || saved.UpdatedAt == "" {
		t.Fatalf("privacy settings missing metadata: %#v", saved)
	}
	loaded, err := svc.LoadPrivacySettings()
	if err != nil {
		t.Fatal(err)
	}
	if loaded.RetentionDays != 7 || !loaded.RetainLocalHistory {
		t.Fatalf("privacy settings did not persist: %#v", loaded)
	}
	bundle, err := svc.PrivacyExport()
	if err != nil {
		t.Fatal(err)
	}
	if !bundle.Success || bundle.Settings.RetentionDays != 7 {
		t.Fatalf("privacy export mismatch: %#v", bundle)
	}
}

func TestSecurityPrivacyDeleteManagedData(t *testing.T) {
	svc, err := NewSecurityPrivacyService(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := svc.SavePrivacySettings(PrivacySettings{RetainLocalHistory: true}); err != nil {
		t.Fatal(err)
	}
	result, err := svc.DeletePrivacyData("privacy_settings")
	if err != nil {
		t.Fatal(err)
	}
	if !result.Success || len(result.Deleted) == 0 {
		t.Fatalf("privacy delete did not report deletion: %#v", result)
	}
}

func TestSecurityPrivacyRequestContextFromHTTP(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "http://127.0.0.1/agent/write-file", strings.NewReader("{}"))
	req.RemoteAddr = "127.0.0.1:10000"
	req.Header.Set("X-CSRF-Token", "csrf")
	req.Header.Set("X-Kaguya-Permission", "perm")
	ctx := RequestContextFromHTTP(req, RiskHigh)
	if ctx.RiskLevel != RiskHigh || !ctx.HasCSRFToken || !ctx.HasPermissionToken {
		t.Fatalf("bad request context: %#v", ctx)
	}
}
