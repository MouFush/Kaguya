package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

const (
	IPWhitelistModeLoopbackOnly = "loopback_only"
	IPWhitelistModeWhitelist    = "whitelist"
	IPWhitelistModeDisabled     = "disabled"

	SecurityErrorIPNotAllowed        = "ip_not_allowed"
	SecurityErrorRemoteHighRiskDeny  = "remote_high_risk_denied"
	SecurityErrorCSRFMissing         = "csrf_required"
	SecurityErrorAuthenticationNeed  = "authentication_required"
	SecurityErrorPermissionTokenNeed = "permission_confirmation_required"
)

type SecurityPrivacyService struct {
	runtimeDir string
	mu         sync.Mutex
	now        func() time.Time
}

type SecurityRuntimeConfig struct {
	BindHost              string   `json:"bind_host,omitempty"`
	DesktopMode           bool     `json:"desktop_mode"`
	AuthEnabled           bool     `json:"auth_enabled"`
	CSRFEnabled           bool     `json:"csrf_enabled"`
	PermissionService     string   `json:"permission_service,omitempty"`
	PermissionMode        string   `json:"permission_mode,omitempty"`
	AuditLogging          bool     `json:"audit_logging"`
	WorkspaceEscapeDenied bool     `json:"workspace_escape_denied"`
	TerminalShellDefault  bool     `json:"terminal_shell_default"`
	BackendMode           string   `json:"backend_mode,omitempty"`
	PythonWorkerAvailable bool     `json:"python_worker_available"`
	IPWhitelistMode       string   `json:"ip_whitelist_mode,omitempty"`
	IPWhitelist           []string `json:"ip_whitelist,omitempty"`
}

type SecurityStatusModel struct {
	Success               bool     `json:"success"`
	Mode                  string   `json:"mode"`
	BackendMode           string   `json:"backend_mode"`
	BindHost              string   `json:"bind_host"`
	LocalOnly             bool     `json:"local_only"`
	LoopbackOnly          bool     `json:"loopback_only"`
	RemoteAccessAllowed   bool     `json:"remote_access_allowed"`
	DesktopMode           bool     `json:"desktop_mode"`
	AuthEnabled           bool     `json:"auth_enabled"`
	AuthRequiredRemote    bool     `json:"auth_required_remote"`
	CSRFProtection        bool     `json:"csrf_protection"`
	CSRFRequiredRemote    bool     `json:"csrf_required_remote"`
	PermissionService     string   `json:"permission_service"`
	PermissionMode        string   `json:"permission_mode"`
	AuditLogging          bool     `json:"audit_logging"`
	WorkspaceEscapeDenied bool     `json:"workspace_escape_denied"`
	TerminalShellDefault  bool     `json:"terminal_shell_default"`
	HighRiskRemotePolicy  string   `json:"high_risk_remote_policy"`
	IPWhitelistMode       string   `json:"ip_whitelist_mode"`
	IPWhitelistEnabled    bool     `json:"ip_whitelist_enabled"`
	IPWhitelist           []string `json:"ip_whitelist"`
	TwoFAAvailable        bool     `json:"two_fa_available"`
	TwoFAStatus           string   `json:"two_fa_status"`
	PythonWorkerAvailable bool     `json:"python_worker_available"`
	Warnings              []string `json:"warnings,omitempty"`
	UpdatedAt             string   `json:"updated_at"`
}

type SecurityRequestContext struct {
	RemoteAddr         string    `json:"remote_addr,omitempty"`
	Host               string    `json:"host,omitempty"`
	Method             string    `json:"method,omitempty"`
	Path               string    `json:"path,omitempty"`
	Action             string    `json:"action,omitempty"`
	RiskLevel          RiskLevel `json:"risk_level,omitempty"`
	HasSessionToken    bool      `json:"has_session_token"`
	HasCSRFToken       bool      `json:"has_csrf_token"`
	HasPermissionToken bool      `json:"has_permission_token"`
	AuthEnabled        bool      `json:"auth_enabled"`
	CSRFEnabled        bool      `json:"csrf_enabled"`
	IPWhitelistMode    string    `json:"ip_whitelist_mode,omitempty"`
	IPWhitelist        []string  `json:"ip_whitelist,omitempty"`
}

type SecurityAccessDecision struct {
	Allowed              bool      `json:"allowed"`
	Reason               string    `json:"reason"`
	Error                string    `json:"error,omitempty"`
	StatusCode           int       `json:"status_code"`
	RiskLevel            RiskLevel `json:"risk_level"`
	Remote               bool      `json:"remote"`
	Loopback             bool      `json:"loopback"`
	ClientIP             string    `json:"client_ip"`
	RequiresAuth         bool      `json:"requires_auth"`
	RequiresCSRF         bool      `json:"requires_csrf"`
	RequiresConfirmation bool      `json:"requires_confirmation"`
	IPWhitelistMode      string    `json:"ip_whitelist_mode"`
}

type IPWhitelistState struct {
	Success   bool     `json:"success"`
	Mode      string   `json:"mode"`
	Enabled   bool     `json:"enabled"`
	Entries   []string `json:"entries"`
	UpdatedAt string   `json:"updated_at,omitempty"`
}

type PrivacySettings struct {
	ID                 string `json:"id"`
	Telemetry          bool   `json:"telemetry"`
	CrashReports       bool   `json:"crash_reports"`
	Analytics          bool   `json:"analytics"`
	ShareDiagnostics   bool   `json:"share_diagnostics"`
	Personalization    bool   `json:"personalization"`
	RetainLocalHistory bool   `json:"retain_local_history"`
	RetentionDays      int    `json:"retention_days"`
	UpdatedAt          string `json:"updated_at,omitempty"`
}

type PrivacyExportBundle struct {
	Success     bool            `json:"success"`
	Mode        string          `json:"mode"`
	GeneratedAt string          `json:"generated_at"`
	Settings    PrivacySettings `json:"settings"`
	Summary     map[string]any  `json:"summary"`
	Files       []string        `json:"files"`
}

type PrivacyDeleteResult struct {
	Success   bool     `json:"success"`
	Mode      string   `json:"mode"`
	Deleted   []string `json:"deleted"`
	Skipped   []string `json:"skipped,omitempty"`
	UpdatedAt string   `json:"updated_at"`
}

type TwoFAUnavailableResponse struct {
	Success              bool   `json:"success"`
	Mode                 string `json:"mode"`
	Available            bool   `json:"available"`
	Error                string `json:"error"`
	Message              string `json:"message"`
	RequiresPythonWorker bool   `json:"requires_python_worker"`
}

func NewSecurityPrivacyService(runtimeDir string) (*SecurityPrivacyService, error) {
	if strings.TrimSpace(runtimeDir) == "" {
		runtimeDir = os.Getenv("KAGUYA_RUNTIME_DIR")
	}
	if strings.TrimSpace(runtimeDir) == "" {
		runtimeDir = filepath.Join(os.TempDir(), "kaguya-go-security-privacy")
	}
	abs, err := filepath.Abs(runtimeDir)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Join(abs, "security_privacy"), 0o700); err != nil {
		return nil, err
	}
	return &SecurityPrivacyService{
		runtimeDir: abs,
		now:        func() time.Time { return time.Now().UTC() },
	}, nil
}

func (svc *SecurityPrivacyService) SecurityStatus(cfg SecurityRuntimeConfig) SecurityStatusModel {
	cfg = normalizeSecurityRuntimeConfig(cfg)
	loopbackBind := IsLoopbackHost(cfg.BindHost)
	warnings := []string{}
	if !loopbackBind && !cfg.AuthEnabled {
		warnings = append(warnings, "non_loopback_bind_requires_auth_or_startup_refusal")
	}
	if cfg.TerminalShellDefault {
		warnings = append(warnings, "terminal_shell_default_should_remain_false")
	}
	if !cfg.WorkspaceEscapeDenied {
		warnings = append(warnings, "workspace_escape_protection_is_disabled")
	}
	sort.Strings(warnings)
	entries := cleanWhitelistEntries(cfg.IPWhitelist)
	return SecurityStatusModel{
		Success:               true,
		Mode:                  "go",
		BackendMode:           cfg.BackendMode,
		BindHost:              cfg.BindHost,
		LocalOnly:             loopbackBind,
		LoopbackOnly:          cfg.IPWhitelistMode == IPWhitelistModeLoopbackOnly,
		RemoteAccessAllowed:   !loopbackBind && cfg.AuthEnabled,
		DesktopMode:           cfg.DesktopMode,
		AuthEnabled:           cfg.AuthEnabled,
		AuthRequiredRemote:    true,
		CSRFProtection:        cfg.CSRFEnabled,
		CSRFRequiredRemote:    cfg.CSRFEnabled,
		PermissionService:     cfg.PermissionService,
		PermissionMode:        cfg.PermissionMode,
		AuditLogging:          cfg.AuditLogging,
		WorkspaceEscapeDenied: cfg.WorkspaceEscapeDenied,
		TerminalShellDefault:  cfg.TerminalShellDefault,
		HighRiskRemotePolicy:  "deny_even_if_ip_whitelisted",
		IPWhitelistMode:       cfg.IPWhitelistMode,
		IPWhitelistEnabled:    cfg.IPWhitelistMode != IPWhitelistModeDisabled,
		IPWhitelist:           entries,
		TwoFAAvailable:        false,
		TwoFAStatus:           "unavailable",
		PythonWorkerAvailable: cfg.PythonWorkerAvailable,
		Warnings:              warnings,
		UpdatedAt:             svc.now().Format(time.RFC3339),
	}
}

func (svc *SecurityPrivacyService) AssessRequest(ctx SecurityRequestContext) SecurityAccessDecision {
	ctx = normalizeSecurityRequestContext(ctx)
	clientIP := ExtractClientIP(ctx.RemoteAddr)
	loopback := IsLoopbackHost(clientIP)
	remote := !loopback
	risk := ctx.RiskLevel
	if risk == "" {
		risk = ClassifySecurityRequest(ctx.Method, ctx.Path, ctx.Action)
	}
	mode := normalizeIPWhitelistMode(ctx.IPWhitelistMode)
	ipAllowed, ipReason := IPAllowed(clientIP, mode, ctx.IPWhitelist)
	decision := SecurityAccessDecision{
		Allowed:         true,
		Reason:          "allowed",
		StatusCode:      http.StatusOK,
		RiskLevel:       risk,
		Remote:          remote,
		Loopback:        loopback,
		ClientIP:        clientIP,
		IPWhitelistMode: mode,
	}
	if !ipAllowed {
		decision.Allowed = false
		decision.Error = SecurityErrorIPNotAllowed
		decision.Reason = ipReason
		decision.StatusCode = http.StatusForbidden
		return decision
	}
	if deny := DenyRemoteHighRisk(ctx); !deny.Allowed {
		deny.ClientIP = clientIP
		deny.IPWhitelistMode = mode
		return deny
	}
	if remote && ctx.AuthEnabled && !ctx.HasSessionToken {
		decision.Allowed = false
		decision.Error = SecurityErrorAuthenticationNeed
		decision.Reason = "remote request requires an authenticated session"
		decision.StatusCode = http.StatusUnauthorized
		decision.RequiresAuth = true
		return decision
	}
	if remote && ctx.CSRFEnabled && IsMutatingMethod(ctx.Method) && !ctx.HasCSRFToken {
		decision.Allowed = false
		decision.Error = SecurityErrorCSRFMissing
		decision.Reason = "remote mutating request requires csrf token"
		decision.StatusCode = http.StatusForbidden
		decision.RequiresCSRF = true
		return decision
	}
	if !remote && IsHighRisk(risk) && !ctx.HasPermissionToken {
		decision.Allowed = false
		decision.Error = SecurityErrorPermissionTokenNeed
		decision.Reason = "high risk local action requires explicit permission confirmation"
		decision.StatusCode = http.StatusForbidden
		decision.RequiresConfirmation = true
		return decision
	}
	return decision
}

func DenyRemoteHighRisk(ctx SecurityRequestContext) SecurityAccessDecision {
	ctx = normalizeSecurityRequestContext(ctx)
	clientIP := ExtractClientIP(ctx.RemoteAddr)
	loopback := IsLoopbackHost(clientIP)
	risk := ctx.RiskLevel
	if risk == "" {
		risk = ClassifySecurityRequest(ctx.Method, ctx.Path, ctx.Action)
	}
	if !loopback && IsHighRisk(risk) {
		return SecurityAccessDecision{
			Allowed:              false,
			Reason:               "remote high-risk actions are denied before permission checks",
			Error:                SecurityErrorRemoteHighRiskDeny,
			StatusCode:           http.StatusForbidden,
			RiskLevel:            risk,
			Remote:               true,
			Loopback:             false,
			ClientIP:             clientIP,
			RequiresAuth:         true,
			RequiresCSRF:         IsMutatingMethod(ctx.Method),
			RequiresConfirmation: true,
			IPWhitelistMode:      normalizeIPWhitelistMode(ctx.IPWhitelistMode),
		}
	}
	return SecurityAccessDecision{
		Allowed:         true,
		Reason:          "not_remote_high_risk",
		StatusCode:      http.StatusOK,
		RiskLevel:       risk,
		Remote:          !loopback,
		Loopback:        loopback,
		ClientIP:        clientIP,
		IPWhitelistMode: normalizeIPWhitelistMode(ctx.IPWhitelistMode),
	}
}

func (svc *SecurityPrivacyService) LoadIPWhitelist() (IPWhitelistState, error) {
	var state IPWhitelistState
	err := svc.readJSON("ip_whitelist.json", &state)
	if errors.Is(err, os.ErrNotExist) {
		return DefaultIPWhitelistState(), nil
	}
	if err != nil {
		return IPWhitelistState{}, err
	}
	return normalizeIPWhitelistState(state), nil
}

func (svc *SecurityPrivacyService) SaveIPWhitelist(state IPWhitelistState) (IPWhitelistState, error) {
	state = normalizeIPWhitelistState(state)
	state.Success = true
	state.UpdatedAt = svc.now().Format(time.RFC3339)
	if err := svc.writeJSON("ip_whitelist.json", state); err != nil {
		return IPWhitelistState{}, err
	}
	return state, nil
}

func (svc *SecurityPrivacyService) SetIPWhitelistMode(mode string) (IPWhitelistState, error) {
	state, err := svc.LoadIPWhitelist()
	if err != nil {
		return IPWhitelistState{}, err
	}
	state.Mode = normalizeIPWhitelistMode(mode)
	return svc.SaveIPWhitelist(state)
}

func (svc *SecurityPrivacyService) LoadPrivacySettings() (PrivacySettings, error) {
	var settings PrivacySettings
	err := svc.readJSON("privacy_settings.json", &settings)
	if errors.Is(err, os.ErrNotExist) {
		return DefaultPrivacySettings(), nil
	}
	if err != nil {
		return PrivacySettings{}, err
	}
	return normalizePrivacySettings(settings, false, svc.now), nil
}

func (svc *SecurityPrivacyService) SavePrivacySettings(settings PrivacySettings) (PrivacySettings, error) {
	settings = normalizePrivacySettings(settings, true, svc.now)
	if err := svc.writeJSON("privacy_settings.json", settings); err != nil {
		return PrivacySettings{}, err
	}
	return settings, nil
}

func (svc *SecurityPrivacyService) PrivacyExport() (PrivacyExportBundle, error) {
	settings, err := svc.LoadPrivacySettings()
	if err != nil {
		return PrivacyExportBundle{}, err
	}
	files, err := svc.managedFiles()
	if err != nil {
		return PrivacyExportBundle{}, err
	}
	return PrivacyExportBundle{
		Success:     true,
		Mode:        "go",
		GeneratedAt: svc.now().Format(time.RFC3339),
		Settings:    settings,
		Summary: map[string]any{
			"telemetry":       settings.Telemetry,
			"crash_reports":   settings.CrashReports,
			"analytics":       settings.Analytics,
			"file_count":      len(files),
			"contains_secret": false,
		},
		Files: files,
	}, nil
}

func (svc *SecurityPrivacyService) DeletePrivacyData(scopes ...string) (PrivacyDeleteResult, error) {
	if len(scopes) == 0 {
		scopes = []string{"privacy_settings"}
	}
	allowed := map[string]string{
		"privacy_settings": "privacy_settings.json",
		"ip_whitelist":     "ip_whitelist.json",
	}
	deleted := []string{}
	skipped := []string{}
	for _, scope := range scopes {
		scope = strings.TrimSpace(strings.ToLower(scope))
		name, ok := allowed[scope]
		if !ok {
			skipped = append(skipped, scope)
			continue
		}
		path := svc.path(name)
		err := os.Remove(path)
		if err == nil || errors.Is(err, os.ErrNotExist) {
			deleted = append(deleted, scope)
			continue
		}
		return PrivacyDeleteResult{}, err
	}
	return PrivacyDeleteResult{
		Success:   true,
		Mode:      "go",
		Deleted:   deleted,
		Skipped:   skipped,
		UpdatedAt: svc.now().Format(time.RFC3339),
	}, nil
}

func (svc *SecurityPrivacyService) TwoFAUnavailable() TwoFAUnavailableResponse {
	return TwoFAUnavailableResponse{
		Success:              false,
		Mode:                 "go",
		Available:            false,
		Error:                "two_factor_unavailable",
		Message:              "2FA enrollment and verification require the full auth worker; Go desktop mode reports this as unavailable instead of pretending it is enabled.",
		RequiresPythonWorker: true,
	}
}

func RequestContextFromHTTP(r *http.Request, risk RiskLevel) SecurityRequestContext {
	if r == nil {
		return SecurityRequestContext{RiskLevel: risk}
	}
	return SecurityRequestContext{
		RemoteAddr:         r.RemoteAddr,
		Host:               r.Host,
		Method:             r.Method,
		Path:               r.URL.Path,
		RiskLevel:          risk,
		HasSessionToken:    hasSessionCredential(r),
		HasCSRFToken:       hasCSRFHeader(r),
		HasPermissionToken: hasPermissionHeader(r),
	}
}

func ClassifySecurityRequest(method, path, action string) RiskLevel {
	method = strings.ToUpper(strings.TrimSpace(method))
	path = strings.ToLower(strings.TrimSpace(path))
	action = strings.ToLower(strings.TrimSpace(action))
	if strings.Contains(action, "delete") || strings.Contains(path, "/privacy/delete") ||
		strings.Contains(path, "/security/audit/clear") {
		return RiskCritical
	}
	for _, marker := range []string{
		"/agent/terminal/exec",
		"/code/execute",
		"/tool/execute",
		"/agent/run-project",
		"/agent/compile",
		"/deploy/execute",
		"/agent/open-project",
		"/agent/import-files",
		"/agent/upload-device-files",
		"/agent/write-file",
		"/agent/file-write",
		"/agent/revert-file",
	} {
		if strings.Contains(path, marker) {
			return RiskHigh
		}
	}
	if strings.Contains(action, "execute") || strings.Contains(action, "run_project") ||
		strings.Contains(action, "compile") || strings.Contains(action, "open_external") {
		return RiskHigh
	}
	if IsMutatingMethod(method) {
		return RiskMedium
	}
	return RiskLow
}

func IsHighRisk(risk RiskLevel) bool {
	return risk == RiskHigh || risk == RiskCritical
}

func IsMutatingMethod(method string) bool {
	switch strings.ToUpper(strings.TrimSpace(method)) {
	case http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete:
		return true
	default:
		return false
	}
}

func ExtractClientIP(remoteAddr string) string {
	remoteAddr = strings.TrimSpace(remoteAddr)
	if remoteAddr == "" {
		return "unknown"
	}
	if strings.Contains(remoteAddr, ",") {
		remoteAddr = strings.TrimSpace(strings.Split(remoteAddr, ",")[0])
	}
	if host, _, err := net.SplitHostPort(remoteAddr); err == nil {
		return strings.Trim(host, "[]")
	}
	if strings.HasPrefix(remoteAddr, "[") && strings.Contains(remoteAddr, "]") {
		return strings.Trim(remoteAddr, "[]")
	}
	if ip := net.ParseIP(remoteAddr); ip != nil {
		return ip.String()
	}
	return strings.Trim(remoteAddr, "[]")
}

func IsLoopbackHost(host string) bool {
	host = strings.TrimSpace(strings.ToLower(strings.Trim(host, "[]")))
	if host == "" {
		return false
	}
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

func IPAllowed(clientIP, mode string, entries []string) (bool, string) {
	mode = normalizeIPWhitelistMode(mode)
	clientIP = ExtractClientIP(clientIP)
	if mode == IPWhitelistModeDisabled {
		return true, "ip_whitelist_disabled"
	}
	if IsLoopbackHost(clientIP) {
		return true, "loopback_allowed"
	}
	if mode == IPWhitelistModeLoopbackOnly {
		return false, "only loopback clients are allowed"
	}
	for _, entry := range cleanWhitelistEntries(entries) {
		if whitelistEntryMatches(clientIP, entry) {
			return true, "ip_whitelist_match"
		}
	}
	return false, "client ip is not in whitelist"
}

func DefaultIPWhitelistState() IPWhitelistState {
	return IPWhitelistState{
		Success: true,
		Mode:    IPWhitelistModeLoopbackOnly,
		Enabled: true,
		Entries: []string{"127.0.0.1", "::1", "localhost"},
	}
}

func DefaultPrivacySettings() PrivacySettings {
	return PrivacySettings{
		ID:                 "settings",
		Telemetry:          false,
		CrashReports:       false,
		Analytics:          false,
		ShareDiagnostics:   false,
		Personalization:    false,
		RetainLocalHistory: true,
		RetentionDays:      30,
	}
}

func normalizeSecurityRuntimeConfig(cfg SecurityRuntimeConfig) SecurityRuntimeConfig {
	if strings.TrimSpace(cfg.BindHost) == "" {
		cfg.BindHost = "127.0.0.1"
	}
	if strings.TrimSpace(cfg.PermissionService) == "" {
		cfg.PermissionService = "go"
	}
	if strings.TrimSpace(cfg.PermissionMode) == "" {
		cfg.PermissionMode = "ask"
	}
	if strings.TrimSpace(cfg.BackendMode) == "" {
		cfg.BackendMode = "go"
	}
	if strings.TrimSpace(cfg.IPWhitelistMode) == "" {
		cfg.IPWhitelistMode = IPWhitelistModeLoopbackOnly
	}
	cfg.IPWhitelistMode = normalizeIPWhitelistMode(cfg.IPWhitelistMode)
	if len(cfg.IPWhitelist) == 0 {
		cfg.IPWhitelist = DefaultIPWhitelistState().Entries
	}
	return cfg
}

func normalizeSecurityRequestContext(ctx SecurityRequestContext) SecurityRequestContext {
	ctx.Method = strings.ToUpper(strings.TrimSpace(ctx.Method))
	if ctx.Method == "" {
		ctx.Method = http.MethodGet
	}
	ctx.Path = strings.TrimSpace(ctx.Path)
	if ctx.Path == "" {
		ctx.Path = "/"
	}
	ctx.IPWhitelistMode = normalizeIPWhitelistMode(ctx.IPWhitelistMode)
	if len(ctx.IPWhitelist) == 0 {
		ctx.IPWhitelist = DefaultIPWhitelistState().Entries
	}
	return ctx
}

func normalizeIPWhitelistMode(mode string) string {
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case IPWhitelistModeDisabled:
		return IPWhitelistModeDisabled
	case IPWhitelistModeWhitelist:
		return IPWhitelistModeWhitelist
	default:
		return IPWhitelistModeLoopbackOnly
	}
}

func normalizeIPWhitelistState(state IPWhitelistState) IPWhitelistState {
	state.Success = true
	state.Mode = normalizeIPWhitelistMode(state.Mode)
	state.Enabled = state.Mode != IPWhitelistModeDisabled
	state.Entries = cleanWhitelistEntries(state.Entries)
	if len(state.Entries) == 0 {
		state.Entries = DefaultIPWhitelistState().Entries
	}
	return state
}

func normalizePrivacySettings(settings PrivacySettings, stamp bool, now func() time.Time) PrivacySettings {
	if strings.TrimSpace(settings.ID) == "" {
		settings.ID = "settings"
	}
	if settings.RetentionDays <= 0 {
		settings.RetentionDays = 30
	}
	if settings.RetentionDays > 3650 {
		settings.RetentionDays = 3650
	}
	if stamp {
		if now == nil {
			now = func() time.Time { return time.Now().UTC() }
		}
		settings.UpdatedAt = now().UTC().Format(time.RFC3339)
	}
	return settings
}

func cleanWhitelistEntries(entries []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, entry := range entries {
		entry = strings.TrimSpace(strings.ToLower(entry))
		if entry == "" || seen[entry] {
			continue
		}
		seen[entry] = true
		out = append(out, entry)
	}
	sort.Strings(out)
	return out
}

func whitelistEntryMatches(clientIP, entry string) bool {
	clientIP = ExtractClientIP(clientIP)
	if entry == "localhost" && IsLoopbackHost(clientIP) {
		return true
	}
	ip := net.ParseIP(clientIP)
	if strings.Contains(entry, "/") {
		_, network, err := net.ParseCIDR(entry)
		return err == nil && ip != nil && network.Contains(ip)
	}
	entryIP := net.ParseIP(entry)
	if ip != nil && entryIP != nil {
		return ip.Equal(entryIP)
	}
	return strings.EqualFold(clientIP, entry)
}

func hasSessionCredential(r *http.Request) bool {
	if r.Header.Get("Authorization") != "" {
		return true
	}
	if _, err := r.Cookie(authAccountCookieName); err == nil {
		return true
	}
	return false
}

func hasCSRFHeader(r *http.Request) bool {
	return strings.TrimSpace(r.Header.Get("X-CSRF-Token")) != "" ||
		strings.TrimSpace(r.Header.Get("X-Kaguya-CSRF")) != ""
}

func hasPermissionHeader(r *http.Request) bool {
	return strings.TrimSpace(r.Header.Get("X-Kaguya-Permission")) != "" ||
		strings.TrimSpace(r.Header.Get("X-Permission-Token")) != ""
}

func (svc *SecurityPrivacyService) managedFiles() ([]string, error) {
	root := filepath.Join(svc.runtimeDir, "security_privacy")
	entries, err := os.ReadDir(root)
	if errors.Is(err, os.ErrNotExist) {
		return []string{}, nil
	}
	if err != nil {
		return nil, err
	}
	files := make([]string, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		files = append(files, entry.Name())
	}
	sort.Strings(files)
	return files, nil
}

func (svc *SecurityPrivacyService) readJSON(name string, dst any) error {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	b, err := os.ReadFile(svc.path(name))
	if err != nil {
		return err
	}
	return json.Unmarshal(b, dst)
}

func (svc *SecurityPrivacyService) writeJSON(name string, value any) error {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	path := svc.path(name)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o600)
}

func (svc *SecurityPrivacyService) path(name string) string {
	name = filepath.Base(filepath.Clean(name))
	if name == "." || name == string(filepath.Separator) {
		name = "state.json"
	}
	return filepath.Join(svc.runtimeDir, "security_privacy", name)
}

func (d SecurityAccessDecision) JSON() map[string]any {
	return map[string]any{
		"success":               d.Allowed,
		"allowed":               d.Allowed,
		"reason":                d.Reason,
		"error":                 d.Error,
		"status_code":           d.StatusCode,
		"risk_level":            d.RiskLevel,
		"remote":                d.Remote,
		"loopback":              d.Loopback,
		"client_ip":             d.ClientIP,
		"requires_auth":         d.RequiresAuth,
		"requires_csrf":         d.RequiresCSRF,
		"requires_confirmation": d.RequiresConfirmation,
		"ip_whitelist_mode":     d.IPWhitelistMode,
	}
}

func (svc *SecurityPrivacyService) EnsureReady() error {
	if svc == nil {
		return errors.New("security privacy service is nil")
	}
	if strings.TrimSpace(svc.runtimeDir) == "" {
		return errors.New("runtime dir is required")
	}
	if err := os.MkdirAll(filepath.Join(svc.runtimeDir, "security_privacy"), 0o700); err != nil {
		return fmt.Errorf("security privacy runtime init failed: %w", err)
	}
	return nil
}
