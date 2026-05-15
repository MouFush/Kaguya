package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAuthAccountV2SetupLoginSessionLifecycle(t *testing.T) {
	svc, handler := newTestAuthAccountHandler(t)

	enable := postJSON(t, handler, "/auth/setup", `{"action":"enable","password":"StrongPass1!"}`, nil)
	if enable.Code != http.StatusOK {
		t.Fatalf("enable status=%d body=%s", enable.Code, enable.Body.String())
	}
	assertJSONBool(t, enable.Body.Bytes(), "success", true)

	setup := getJSON(t, handler, "/auth/setup", nil)
	assertJSONBool(t, setup.Body.Bytes(), "enabled", true)
	assertJSONBool(t, setup.Body.Bytes(), "has_password", true)

	login := postJSON(t, handler, "/auth/login", `{"password":"StrongPass1!"}`, nil)
	if login.Code != http.StatusOK {
		t.Fatalf("login status=%d body=%s", login.Code, login.Body.String())
	}
	body := decodeJSONMap(t, login.Body.Bytes())
	if body["token"] != nil || body["access_token"] != nil || strings.Contains(login.Body.String(), "StrongPass1!") {
		t.Fatalf("login leaked secret fields/body=%s", login.Body.String())
	}
	cookie := findCookie(login.Result().Cookies(), authAccountCookieName)
	if cookie == nil || cookie.Value == "" {
		t.Fatalf("login did not set auth cookie")
	}
	if !cookie.HttpOnly {
		t.Fatalf("auth cookie must be HttpOnly")
	}

	sessions := getJSON(t, handler, "/account/sessions", cookie)
	if sessions.Code != http.StatusOK {
		t.Fatalf("sessions status=%d body=%s", sessions.Code, sessions.Body.String())
	}
	sessionsBody := sessions.Body.String()
	if strings.Contains(sessionsBody, cookie.Value) {
		t.Fatalf("sessions leaked raw cookie token: %s", sessionsBody)
	}
	if !strings.Contains(sessionsBody, `"current":true`) {
		t.Fatalf("sessions did not mark current session: %s", sessionsBody)
	}

	disable := postJSON(t, handler, "/auth/setup", `{"action":"disable"}`, cookie)
	if disable.Code != http.StatusOK {
		t.Fatalf("disable status=%d body=%s", disable.Code, disable.Body.String())
	}
	assertJSONBool(t, disable.Body.Bytes(), "enabled", false)

	cfg := svc.loadConfig()
	if cfg.Enabled || cfg.AccessTokenHash != "" {
		t.Fatalf("disable did not clear auth state: %+v", cfg)
	}
}

func TestAuthAccountV2RejectsWeakPasswordAndBadProfileEmail(t *testing.T) {
	_, handler := newTestAuthAccountHandler(t)

	weak := postJSON(t, handler, "/auth/setup", `{"action":"enable","password":"short"}`, nil)
	if weak.Code != http.StatusBadRequest {
		t.Fatalf("weak password status=%d body=%s", weak.Code, weak.Body.String())
	}
	assertJSONBool(t, weak.Body.Bytes(), "success", false)

	badEmail := postJSON(t, handler, "/account/profile", `{"nickname":"Kaguya","email":"bad-email"}`, nil)
	if badEmail.Code != http.StatusBadRequest {
		t.Fatalf("bad email status=%d body=%s", badEmail.Code, badEmail.Body.String())
	}
	assertJSONBool(t, badEmail.Body.Bytes(), "success", false)
}

func TestAuthAccountV2TokensAreMaskedAndStoredHashed(t *testing.T) {
	svc, handler := newTestAuthAccountHandler(t)

	create := postJSON(t, handler, "/account/tokens", `{"name":"ci"}`, nil)
	if create.Code != http.StatusOK {
		t.Fatalf("create token status=%d body=%s", create.Code, create.Body.String())
	}
	body := decodeJSONMap(t, create.Body.Bytes())
	if _, ok := body["token"]; ok {
		t.Fatalf("token creation leaked raw token: %s", create.Body.String())
	}
	if _, ok := body["access_token"]; ok {
		t.Fatalf("token creation leaked access token: %s", create.Body.String())
	}
	mask, _ := body["token_mask"].(string)
	if mask == "" || !strings.Contains(mask, "*") {
		t.Fatalf("token mask missing: %s", create.Body.String())
	}

	tokens := svc.loadTokens()
	if len(tokens) != 1 {
		t.Fatalf("expected one stored token, got %d", len(tokens))
	}
	if tokens[0].TokenHash == "" || tokens[0].TokenHash == tokens[0].TokenMask {
		t.Fatalf("token was not stored as hash+mask: %+v", tokens[0])
	}
	rawFile, err := os.ReadFile(filepath.Join(svc.runtimeDir, "auth_account", "api_tokens.json"))
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(rawFile), `"token":`) {
		t.Fatalf("stored api_tokens.json contains raw token field: %s", string(rawFile))
	}

	list := getJSON(t, handler, "/account/tokens", nil)
	if strings.Contains(list.Body.String(), tokens[0].TokenHash) {
		t.Fatalf("list leaked token hash: %s", list.Body.String())
	}
}

func TestAuthAccountV2AdminAndMultiUserReturnStructuredUnavailable(t *testing.T) {
	_, handler := newTestAuthAccountHandler(t)

	admin := getJSON(t, handler, "/auth/admin/accounts", nil)
	if admin.Code != http.StatusOK {
		t.Fatalf("admin accounts status=%d body=%s", admin.Code, admin.Body.String())
	}
	adminBody := decodeJSONMap(t, admin.Body.Bytes())
	if adminBody["multi_user_available"] != false {
		t.Fatalf("admin accounts did not declare multi-user unavailable: %s", admin.Body.String())
	}

	register := postJSON(t, handler, "/auth/register", `{"username":"u","password":"StrongPass1!"}`, nil)
	if register.Code != http.StatusServiceUnavailable {
		t.Fatalf("register status=%d body=%s", register.Code, register.Body.String())
	}
	registerBody := decodeJSONMap(t, register.Body.Bytes())
	if registerBody["success"] != false || registerBody["error"] == nil {
		t.Fatalf("register unavailable response is not structured: %s", register.Body.String())
	}
}

func TestAuthAccountV2ProfilePersistsLocally(t *testing.T) {
	_, handler := newTestAuthAccountHandler(t)

	save := postJSON(t, handler, "/account/profile", `{"nickname":"Kaguya","email":"kaguya@example.com","avatar":"moon"}`, nil)
	if save.Code != http.StatusOK {
		t.Fatalf("profile save status=%d body=%s", save.Code, save.Body.String())
	}

	get := getJSON(t, handler, "/auth/account", nil)
	if get.Code != http.StatusOK {
		t.Fatalf("auth account status=%d body=%s", get.Code, get.Body.String())
	}
	if !strings.Contains(get.Body.String(), `"display_name":"Kaguya"`) {
		t.Fatalf("profile did not feed auth account: %s", get.Body.String())
	}
}

func newTestAuthAccountHandler(t *testing.T) (*authAccountService, http.Handler) {
	t.Helper()
	svc := newAuthAccountService(t.TempDir())
	mux := http.NewServeMux()
	svc.registerAuthAccountV2Routes(mux)
	return svc, mux
}

func postJSON(t *testing.T, handler http.Handler, path, body string, cookie *http.Cookie) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	if cookie != nil {
		req.AddCookie(cookie)
	}
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func getJSON(t *testing.T, handler http.Handler, path string, cookie *http.Cookie) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, path, nil)
	if cookie != nil {
		req.AddCookie(cookie)
	}
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	return rec
}

func decodeJSONMap(t *testing.T, body []byte) map[string]any {
	t.Helper()
	var out map[string]any
	if err := json.Unmarshal(body, &out); err != nil {
		t.Fatalf("invalid json %s: %v", string(body), err)
	}
	return out
}

func assertJSONBool(t *testing.T, body []byte, key string, want bool) {
	t.Helper()
	out := decodeJSONMap(t, body)
	if got, ok := out[key].(bool); !ok || got != want {
		t.Fatalf("%s=%v want %v in %s", key, out[key], want, string(body))
	}
}

func findCookie(cookies []*http.Cookie, name string) *http.Cookie {
	for _, cookie := range cookies {
		if cookie.Name == name {
			return cookie
		}
	}
	return nil
}
