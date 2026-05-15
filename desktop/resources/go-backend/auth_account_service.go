package main

import (
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

const (
	authAccountCookieName = "kaguya_auth_token"
	authPasswordIters     = 120000
)

type authAccountService struct {
	runtimeDir string
	mu         sync.Mutex
	now        func() time.Time
	random     io.Reader
}

type authAccountConfig struct {
	Enabled         bool   `json:"enabled"`
	PasswordHash    string `json:"password_hash,omitempty"`
	AccessTokenHash string `json:"access_token_hash,omitempty"`
	UpdatedAt       string `json:"updated_at,omitempty"`
}

type authLocalProfile struct {
	Nickname  string `json:"nickname"`
	Email     string `json:"email"`
	Avatar    string `json:"avatar"`
	UpdatedAt string `json:"updated_at,omitempty"`
}

type authAPITokenRecord struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	TokenHash string `json:"token_hash"`
	TokenMask string `json:"token_mask"`
	CreatedAt string `json:"created_at"`
}

type authSessionRecord struct {
	ID         string `json:"id"`
	TokenHash  string `json:"token_hash"`
	TokenMask  string `json:"token_mask"`
	IP         string `json:"ip"`
	UserAgent  string `json:"user_agent,omitempty"`
	CreatedAt  string `json:"created_at"`
	LastActive string `json:"last_active"`
}

func registerAuthAccountV2Routes(mux *http.ServeMux) {
	newAuthAccountService("").registerAuthAccountV2Routes(mux)
}

func newAuthAccountService(runtimeDir string) *authAccountService {
	if runtimeDir == "" {
		runtimeDir = os.Getenv("KAGUYA_RUNTIME_DIR")
	}
	if runtimeDir == "" {
		runtimeDir = filepath.Join(os.TempDir(), "kaguya-go-auth-account")
	}
	return &authAccountService{
		runtimeDir: runtimeDir,
		now:        func() time.Time { return time.Now().UTC() },
		random:     rand.Reader,
	}
}

func (svc *authAccountService) registerAuthAccountV2Routes(mux *http.ServeMux) {
	mux.HandleFunc("/auth/login", svc.handleAuthLoginV2)
	mux.HandleFunc("/auth/logout", svc.handleAuthLogoutV2)
	mux.HandleFunc("/auth/logout-all", svc.handleAuthLogoutAllV2)
	mux.HandleFunc("/auth/register", svc.handleAuthRegisterV2)
	mux.HandleFunc("/auth/token", svc.handleAuthTokenV2)
	mux.HandleFunc("/auth/password-reset/request", svc.handleAuthPasswordResetRequestV2)
	mux.HandleFunc("/auth/password-reset/confirm", svc.handleAuthPasswordResetConfirmV2)
	mux.HandleFunc("/auth/account", svc.handleAuthAccountV2)
	mux.HandleFunc("/auth/admin/accounts", svc.handleAuthAdminAccountsV2)
	mux.HandleFunc("/auth/admin/role", svc.handleAuthAdminRoleV2)
	mux.HandleFunc("/auth/setup", svc.handleAuthSetupV2)
	mux.HandleFunc("/account/profile", svc.handleAccountProfileV2)
	mux.HandleFunc("/account/tokens", svc.handleAccountTokensV2)
	mux.HandleFunc("/account/sessions", svc.handleAccountSessionsV2)
}

func (svc *authAccountService) handleAuthSetupV2(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		cfg := svc.loadConfig()
		writeJSON(w, http.StatusOK, map[string]any{
			"success":      true,
			"mode":         "go",
			"enabled":      cfg.Enabled,
			"has_password": cfg.PasswordHash != "",
			"multi_user":   false,
		})
	case http.MethodPost:
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		action := firstString(payload, "action")
		cfg := svc.loadConfig()
		if cfg.Enabled && action != "enable" && !svc.requestAuthorized(r, cfg) {
			writeJSON(w, http.StatusUnauthorized, map[string]any{"success": false, "error": "admin_auth_required"})
			return
		}
		switch action {
		case "enable":
			password := strings.TrimSpace(firstString(payload, "password"))
			if err := validateAuthPasswordStrength(password); err != "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"success": false, "error": err})
				return
			}
			hash, err := svc.hashPassword(password)
			if err != nil {
				writeError(w, http.StatusInternalServerError, "hash_failed", err.Error())
				return
			}
			cfg.Enabled = true
			cfg.PasswordHash = hash
			cfg.AccessTokenHash = ""
			cfg.UpdatedAt = svc.now().Format(time.RFC3339)
			if err := svc.saveConfig(cfg); err != nil {
				writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "enabled": true})
		case "disable":
			cfg.Enabled = false
			cfg.AccessTokenHash = ""
			cfg.UpdatedAt = svc.now().Format(time.RFC3339)
			if err := svc.saveConfig(cfg); err != nil {
				writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
				return
			}
			_ = svc.saveSessions(nil)
			clearAuthCookie(w)
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "enabled": false})
		case "change_password":
			oldPassword := strings.TrimSpace(firstString(payload, "old_password", "oldPassword"))
			newPassword := strings.TrimSpace(firstString(payload, "new_password", "newPassword"))
			if !verifyPasswordHash(oldPassword, cfg.PasswordHash) {
				writeJSON(w, http.StatusBadRequest, map[string]any{"success": false, "error": "old_password_invalid"})
				return
			}
			if err := validateAuthPasswordStrength(newPassword); err != "" {
				writeJSON(w, http.StatusBadRequest, map[string]any{"success": false, "error": err})
				return
			}
			hash, err := svc.hashPassword(newPassword)
			if err != nil {
				writeError(w, http.StatusInternalServerError, "hash_failed", err.Error())
				return
			}
			cfg.PasswordHash = hash
			cfg.AccessTokenHash = ""
			cfg.UpdatedAt = svc.now().Format(time.RFC3339)
			if err := svc.saveConfig(cfg); err != nil {
				writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
				return
			}
			_ = svc.saveSessions(nil)
			clearAuthCookie(w)
			writeJSON(w, http.StatusOK, map[string]any{"success": true})
		default:
			writeJSON(w, http.StatusBadRequest, map[string]any{"success": false, "error": "unknown_action"})
		}
	default:
		methodNotAllowed(w)
	}
}

func (svc *authAccountService) handleAuthLoginV2(w http.ResponseWriter, r *http.Request) {
	cfg := svc.loadConfig()
	if !cfg.Enabled {
		writeJSON(w, http.StatusOK, map[string]any{
			"success":       true,
			"mode":          "go",
			"auth_required": false,
			"message":       "desktop_loopback_auth_disabled",
		})
		return
	}
	if r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "auth_required": true, "login": "password"})
		return
	}
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	password := ""
	if strings.Contains(r.Header.Get("Content-Type"), "application/json") {
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		password = firstString(payload, "password")
	} else {
		if err := r.ParseForm(); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_form", err.Error())
			return
		}
		password = r.Form.Get("password")
	}
	if !verifyPasswordHash(strings.TrimSpace(password), cfg.PasswordHash) {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"success": false, "error": "invalid_credentials"})
		return
	}
	token, err := svc.newSecret("kag_sess_", 32)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "token_failed", err.Error())
		return
	}
	tokenHash := hashSecret(token)
	cfg.AccessTokenHash = tokenHash
	cfg.UpdatedAt = svc.now().Format(time.RFC3339)
	if err := svc.saveConfig(cfg); err != nil {
		writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
		return
	}
	session := authSessionRecord{
		ID:         svc.mustID("sess"),
		TokenHash:  tokenHash,
		TokenMask:  maskAPIKey(token),
		IP:         clientIP(r),
		UserAgent:  r.UserAgent(),
		CreatedAt:  svc.now().Format(time.RFC3339),
		LastActive: svc.now().Format(time.RFC3339),
	}
	sessions := svc.loadSessions()
	sessions = append(sessions, session)
	if err := svc.saveSessions(sessions); err != nil {
		writeError(w, http.StatusInternalServerError, "session_save_failed", err.Error())
		return
	}
	http.SetCookie(w, &http.Cookie{
		Name:     authAccountCookieName,
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		Expires:  svc.now().Add(24 * time.Hour),
	})
	writeJSON(w, http.StatusOK, map[string]any{
		"success":       true,
		"auth":          "desktop_password",
		"session_id":    session.ID,
		"token_mask":    maskAPIKey(token),
		"auth_required": true,
	})
}

func (svc *authAccountService) handleAuthLogoutV2(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	token := svc.authTokenFromRequest(r)
	if token != "" {
		tokenHash := hashSecret(token)
		sessions := svc.loadSessions()
		filtered := make([]authSessionRecord, 0, len(sessions))
		for _, item := range sessions {
			if item.TokenHash != tokenHash {
				filtered = append(filtered, item)
			}
		}
		_ = svc.saveSessions(filtered)
	}
	cfg := svc.loadConfig()
	cfg.AccessTokenHash = ""
	_ = svc.saveConfig(cfg)
	clearAuthCookie(w)
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "logged_out": true})
}

func (svc *authAccountService) handleAuthLogoutAllV2(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	cfg := svc.loadConfig()
	cfg.AccessTokenHash = ""
	cfg.UpdatedAt = svc.now().Format(time.RFC3339)
	if err := svc.saveConfig(cfg); err != nil {
		writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
		return
	}
	_ = svc.saveSessions(nil)
	clearAuthCookie(w)
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "logged_out_all": true})
}

func (svc *authAccountService) handleAuthRegisterV2(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("multi_user_unavailable", "multi-user account registration is not available in the Go desktop auth service"))
}

func (svc *authAccountService) handleAuthTokenV2(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("multi_user_unavailable", "OAuth/JWT token exchange requires the multi-user auth worker"))
}

func (svc *authAccountService) handleAuthPasswordResetRequestV2(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("multi_user_unavailable", "password reset requires the multi-user auth worker"))
}

func (svc *authAccountService) handleAuthPasswordResetConfirmV2(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("multi_user_unavailable", "password reset requires the multi-user auth worker"))
}

func (svc *authAccountService) handleAuthAdminAccountsV2(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]any{
			"success":              true,
			"mode":                 "go",
			"multi_user_available": false,
			"accounts": []map[string]any{{
				"id":           "local-desktop-user",
				"username":     "desktop",
				"role":         "owner",
				"display_name": "Local desktop user",
				"local":        true,
			}},
			"warning": "admin account management is unavailable outside the Python multi-user worker",
		})
		return
	}
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("admin_unavailable", "admin account mutation requires the multi-user auth worker"))
}

func (svc *authAccountService) handleAuthAdminRoleV2(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusServiceUnavailable, authAccountUnavailable("admin_unavailable", "role administration requires the multi-user auth worker"))
}

func (svc *authAccountService) handleAuthAccountV2(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		profile := svc.loadProfile()
		cfg := svc.loadConfig()
		writeJSON(w, http.StatusOK, map[string]any{
			"success": true,
			"mode":    "go",
			"account": map[string]any{
				"id":                   "local-desktop-user",
				"username":             "desktop",
				"display_name":         displayName(profile),
				"email":                profile.Email,
				"avatar":               profile.Avatar,
				"role":                 "owner",
				"local":                true,
				"auth_enabled":         cfg.Enabled,
				"multi_user_available": false,
			},
		})
	case http.MethodPut, http.MethodPost:
		svc.handleAccountProfileV2(w, r)
	default:
		methodNotAllowed(w)
	}
}

func (svc *authAccountService) handleAccountProfileV2(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "profile": svc.loadProfile()})
	case http.MethodPost, http.MethodPut:
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		profile := authLocalProfile{
			Nickname:  strings.TrimSpace(firstString(payload, "nickname", "name", "display_name")),
			Email:     strings.TrimSpace(firstString(payload, "email")),
			Avatar:    strings.TrimSpace(firstString(payload, "avatar")),
			UpdatedAt: svc.now().Format(time.RFC3339),
		}
		if profile.Avatar == "" {
			profile.Avatar = "🌙"
		}
		if profile.Email != "" && !validEmail(profile.Email) {
			writeJSON(w, http.StatusBadRequest, map[string]any{"success": false, "error": "invalid_email"})
			return
		}
		if err := svc.saveProfile(profile); err != nil {
			writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "profile": profile})
	default:
		methodNotAllowed(w)
	}
}

func (svc *authAccountService) handleAccountTokensV2(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "tokens": svc.safeTokens()})
	case http.MethodPost:
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil && !errors.Is(err, io.EOF) {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		name := strings.TrimSpace(firstString(payload, "name"))
		if name == "" {
			name = "API Token"
		}
		raw, err := svc.newSecret("kag_", 32)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "token_failed", err.Error())
			return
		}
		record := authAPITokenRecord{
			ID:        svc.mustID("tok"),
			Name:      name,
			TokenHash: hashSecret(raw),
			TokenMask: maskAPIKey(raw),
			CreatedAt: svc.now().Format(time.RFC3339),
		}
		tokens := svc.loadTokens()
		tokens = append(tokens, record)
		if err := svc.saveTokens(tokens); err != nil {
			writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"success":    true,
			"id":         record.ID,
			"name":       record.Name,
			"token_mask": record.TokenMask,
			"created_at": record.CreatedAt,
		})
	case http.MethodDelete:
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		id := firstString(payload, "id")
		tokens := svc.loadTokens()
		filtered := make([]authAPITokenRecord, 0, len(tokens))
		for _, item := range tokens {
			if item.ID != id {
				filtered = append(filtered, item)
			}
		}
		if err := svc.saveTokens(filtered); err != nil {
			writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "deleted": len(tokens) - len(filtered)})
	default:
		methodNotAllowed(w)
	}
}

func (svc *authAccountService) handleAccountSessionsV2(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		token := svc.authTokenFromRequest(r)
		tokenHash := hashSecret(token)
		sessions := svc.loadSessions()
		if token != "" {
			found := false
			for i := range sessions {
				if sessions[i].TokenHash == tokenHash {
					sessions[i].IP = clientIP(r)
					sessions[i].UserAgent = r.UserAgent()
					sessions[i].LastActive = svc.now().Format(time.RFC3339)
					found = true
				}
			}
			if !found {
				sessions = append(sessions, authSessionRecord{
					ID:         svc.mustID("sess"),
					TokenHash:  tokenHash,
					TokenMask:  maskAPIKey(token),
					IP:         clientIP(r),
					UserAgent:  r.UserAgent(),
					CreatedAt:  svc.now().Format(time.RFC3339),
					LastActive: svc.now().Format(time.RFC3339),
				})
			}
			_ = svc.saveSessions(sessions)
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "sessions": safeSessions(sessions, tokenHash)})
	case http.MethodDelete:
		var payload map[string]any
		if err := v2ReadJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		id := firstString(payload, "id")
		sessions := svc.loadSessions()
		filtered := make([]authSessionRecord, 0, len(sessions))
		for _, item := range sessions {
			if item.ID != id {
				filtered = append(filtered, item)
			}
		}
		if err := svc.saveSessions(filtered); err != nil {
			writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "deleted": len(sessions) - len(filtered)})
	default:
		methodNotAllowed(w)
	}
}

func (svc *authAccountService) loadConfig() authAccountConfig {
	var cfg authAccountConfig
	if err := svc.readJSONFile("auth_config.json", &cfg); err != nil {
		return authAccountConfig{}
	}
	return cfg
}

func (svc *authAccountService) saveConfig(cfg authAccountConfig) error {
	return svc.writeJSONFile("auth_config.json", cfg)
}

func (svc *authAccountService) loadProfile() authLocalProfile {
	var profile authLocalProfile
	if err := svc.readJSONFile("user_profile.json", &profile); err != nil {
		return authLocalProfile{Nickname: "", Email: "", Avatar: "🌙"}
	}
	if profile.Avatar == "" {
		profile.Avatar = "🌙"
	}
	return profile
}

func (svc *authAccountService) saveProfile(profile authLocalProfile) error {
	return svc.writeJSONFile("user_profile.json", profile)
}

func (svc *authAccountService) loadTokens() []authAPITokenRecord {
	var tokens []authAPITokenRecord
	if err := svc.readJSONFile("api_tokens.json", &tokens); err != nil {
		return []authAPITokenRecord{}
	}
	return tokens
}

func (svc *authAccountService) saveTokens(tokens []authAPITokenRecord) error {
	return svc.writeJSONFile("api_tokens.json", tokens)
}

func (svc *authAccountService) safeTokens() []map[string]any {
	tokens := svc.loadTokens()
	out := make([]map[string]any, 0, len(tokens))
	for _, token := range tokens {
		out = append(out, map[string]any{
			"id":         token.ID,
			"name":       token.Name,
			"token_mask": token.TokenMask,
			"created_at": token.CreatedAt,
		})
	}
	return out
}

func (svc *authAccountService) loadSessions() []authSessionRecord {
	var sessions []authSessionRecord
	if err := svc.readJSONFile("active_sessions.json", &sessions); err != nil {
		return []authSessionRecord{}
	}
	return sessions
}

func (svc *authAccountService) saveSessions(sessions []authSessionRecord) error {
	if sessions == nil {
		sessions = []authSessionRecord{}
	}
	return svc.writeJSONFile("active_sessions.json", sessions)
}

func (svc *authAccountService) readJSONFile(name string, dst any) error {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	path := svc.dataPath(name)
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, dst)
}

func (svc *authAccountService) writeJSONFile(name string, value any) error {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	path := svc.dataPath(name)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o600)
}

func (svc *authAccountService) dataPath(name string) string {
	return filepath.Join(svc.runtimeDir, "auth_account", filepath.Clean(name))
}

func (svc *authAccountService) authTokenFromRequest(r *http.Request) string {
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(strings.ToLower(auth), "bearer ") {
		return strings.TrimSpace(auth[7:])
	}
	if cookie, err := r.Cookie(authAccountCookieName); err == nil {
		return cookie.Value
	}
	return ""
}

func (svc *authAccountService) requestAuthorized(r *http.Request, cfg authAccountConfig) bool {
	token := svc.authTokenFromRequest(r)
	if token == "" {
		return false
	}
	tokenHash := hashSecret(token)
	if cfg.AccessTokenHash != "" && subtle.ConstantTimeCompare([]byte(tokenHash), []byte(cfg.AccessTokenHash)) == 1 {
		return true
	}
	for _, session := range svc.loadSessions() {
		if subtle.ConstantTimeCompare([]byte(tokenHash), []byte(session.TokenHash)) == 1 {
			return true
		}
	}
	return false
}

func (svc *authAccountService) newSecret(prefix string, n int) (string, error) {
	buf := make([]byte, n)
	if _, err := io.ReadFull(svc.random, buf); err != nil {
		return "", err
	}
	return prefix + base64.RawURLEncoding.EncodeToString(buf), nil
}

func (svc *authAccountService) mustID(prefix string) string {
	secret, err := svc.newSecret(prefix+"_", 8)
	if err != nil {
		return fmt.Sprintf("%s_%d", prefix, svc.now().UnixNano())
	}
	return secret
}

func (svc *authAccountService) hashPassword(password string) (string, error) {
	saltBytes := make([]byte, 16)
	if _, err := io.ReadFull(svc.random, saltBytes); err != nil {
		return "", err
	}
	salt := hex.EncodeToString(saltBytes)
	sum := iterativeSHA256([]byte(password), []byte(salt), authPasswordIters)
	return fmt.Sprintf("sha256:%d:%s:%s", authPasswordIters, salt, hex.EncodeToString(sum)), nil
}

func verifyPasswordHash(password, stored string) bool {
	parts := strings.Split(stored, ":")
	if len(parts) != 4 || parts[0] != "sha256" {
		return false
	}
	var iters int
	if _, err := fmt.Sscanf(parts[1], "%d", &iters); err != nil || iters <= 0 {
		return false
	}
	want, err := hex.DecodeString(parts[3])
	if err != nil {
		return false
	}
	got := iterativeSHA256([]byte(password), []byte(parts[2]), iters)
	return subtle.ConstantTimeCompare(got, want) == 1
}

func iterativeSHA256(password, salt []byte, iters int) []byte {
	h := sha256.Sum256(append(append([]byte{}, salt...), password...))
	out := h[:]
	for i := 1; i < iters; i++ {
		next := sha256.Sum256(out)
		out = next[:]
	}
	return append([]byte{}, out...)
}

func hashSecret(secret string) string {
	if secret == "" {
		return ""
	}
	sum := sha256.Sum256([]byte(secret))
	return hex.EncodeToString(sum[:])
}

func validateAuthPasswordStrength(password string) string {
	if len(password) < 8 {
		return "password_too_short"
	}
	score := 0
	if regexp.MustCompile(`[A-Z]`).MatchString(password) {
		score++
	}
	if regexp.MustCompile(`[a-z]`).MatchString(password) {
		score++
	}
	if regexp.MustCompile(`[0-9]`).MatchString(password) {
		score++
	}
	if regexp.MustCompile(`[!@#$%^&*()_\+\-=\[\]{}|;:,.<>?/~` + "`" + `]`).MatchString(password) {
		score++
	}
	if score < 3 {
		return "password_strength_insufficient"
	}
	return ""
}

func authAccountUnavailable(code, message string) map[string]any {
	return map[string]any{
		"success":              false,
		"mode":                 "go",
		"error":                code,
		"message":              message,
		"multi_user_available": false,
	}
}

func v2ReadJSON(r *http.Request, dst any) error {
	defer r.Body.Close()
	dec := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	dec.UseNumber()
	return dec.Decode(dst)
}

func clearAuthCookie(w http.ResponseWriter) {
	http.SetCookie(w, &http.Cookie{
		Name:     authAccountCookieName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   -1,
	})
}

func validEmail(email string) bool {
	return regexp.MustCompile(`^[^@\s]+@[^@\s]+\.[^@\s]+$`).MatchString(email)
}

func displayName(profile authLocalProfile) string {
	if strings.TrimSpace(profile.Nickname) != "" {
		return strings.TrimSpace(profile.Nickname)
	}
	return "Local desktop user"
}

func clientIP(r *http.Request) string {
	if r.RemoteAddr == "" {
		return "unknown"
	}
	host := r.RemoteAddr
	if idx := strings.LastIndex(host, ":"); idx > -1 {
		host = host[:idx]
	}
	host = strings.Trim(host, "[]")
	if host == "" {
		return "unknown"
	}
	return host
}

func safeSessions(sessions []authSessionRecord, currentHash string) []map[string]any {
	out := make([]map[string]any, 0, len(sessions))
	for _, item := range sessions {
		out = append(out, map[string]any{
			"id":          item.ID,
			"current":     currentHash != "" && subtle.ConstantTimeCompare([]byte(item.TokenHash), []byte(currentHash)) == 1,
			"ip":          item.IP,
			"user_agent":  item.UserAgent,
			"last_active": item.LastActive,
			"created_at":  item.CreatedAt,
			"token_mask":  item.TokenMask,
		})
	}
	return out
}
