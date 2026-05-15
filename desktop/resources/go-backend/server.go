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
	"os/user"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type ServerConfig struct {
	RuntimeDir string
	PythonURL  string
	AppDir     string
	StaticDir  string
}

type Server struct {
	cfg             ServerConfig
	runtimeDir      string
	workspaceRoot   string
	devicePath      string
	mu              sync.Mutex
	permissions     permissionState
	proxy           http.Handler
	providerChat    providerChatService
	agentRuntime    *AgentRuntimeService
	securityPrivacy *SecurityPrivacyService
	workspace       *WorkspaceProjectService
	terminal        *TerminalPermissionService
	knowledge       *KnowledgeRAGService
	authAccount     *authAccountService
	projectExec     *ProjectExecutionService
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
	workspaceRoot := filepath.Join(cfg.RuntimeDir, "workspaces")
	if err := os.MkdirAll(workspaceRoot, 0o755); err != nil {
		return nil, err
	}
	s := &Server{
		cfg:           cfg,
		runtimeDir:    cfg.RuntimeDir,
		workspaceRoot: workspaceRoot,
		devicePath:    filepath.Join(cfg.RuntimeDir, "device_vault.enc"),
		permissions:   permissionState{Mode: "ask"},
		providerChat:  newProviderChatService(nil),
		agentRuntime:  NewAgentRuntimeService(),
		terminal:      NewTerminalPermissionService(filepath.Join(cfg.RuntimeDir, "audit_logs", "terminal_audit.jsonl")),
		authAccount:   newAuthAccountService(cfg.RuntimeDir),
	}
	securityPrivacy, err := NewSecurityPrivacyService(cfg.RuntimeDir)
	if err != nil {
		return nil, err
	}
	s.securityPrivacy = securityPrivacy
	workspace, err := NewWorkspaceProjectService(cfg.RuntimeDir, s.workspaceRoot)
	if err != nil {
		return nil, err
	}
	s.workspace = workspace
	knowledge, err := NewKnowledgeRAGService(cfg.RuntimeDir)
	if err != nil {
		return nil, err
	}
	s.knowledge = knowledge
	s.projectExec = NewProjectExecutionService(s.workspace, s.terminal)
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
	mux.HandleFunc("/background", s.imageAsset("kaguya-header.png"))
	mux.HandleFunc("/wallpaper", s.imageAsset("kaguya-hero.png"))
	mux.HandleFunc("/header-img", s.imageAsset("kaguya-header.png"))
	mux.HandleFunc("/hero-img", s.imageAsset("kaguya-hero.png"))
	mux.HandleFunc("/welcome-img", s.imageAsset("kaguya-welcome.png"))
	mux.HandleFunc("/favicon.ico", s.imageAsset("favicon.ico"))
	mux.HandleFunc("/static/", s.staticFile)
	mux.HandleFunc("/assets/", s.assetFile)
	mux.HandleFunc("/health", s.health)
	mux.HandleFunc("/api/config", s.apiConfig)
	mux.HandleFunc("/api/model-status", s.modelStatus)
	mux.HandleFunc("/api/device/info", s.deviceInfo)
	mux.HandleFunc("/api/device/bind", s.deviceBind)
	mux.HandleFunc("/api/device/unbind", s.deviceUnbind)
	mux.HandleFunc("/api/account/saved-config", s.savedConfig)
	mux.HandleFunc("/api/account/auto-fill", s.autoFill)
	mux.HandleFunc("/account/profile", s.accountProfile)
	mux.HandleFunc("/account/sessions", s.accountSessions)
	mux.HandleFunc("/account/tokens", s.accountTokens)
	mux.HandleFunc("/auth/account", s.accountProfile)
	mux.HandleFunc("/auth/admin/accounts", s.authAdminAccounts)
	mux.HandleFunc("/auth/admin/role", s.authAdminRole)
	mux.HandleFunc("/auth/login", s.authLogin)
	mux.HandleFunc("/auth/logout", s.authLogout)
	mux.HandleFunc("/auth/logout-all", s.authLogout)
	mux.HandleFunc("/auth/password-reset/confirm", s.authPasswordReset)
	mux.HandleFunc("/auth/password-reset/request", s.authPasswordReset)
	mux.HandleFunc("/auth/register", s.authRegister)
	mux.HandleFunc("/auth/setup", s.authSetup)
	mux.HandleFunc("/auth/token", s.authToken)
	mux.HandleFunc("/api/roles", s.roles)
	mux.HandleFunc("/api/prompts", s.prompts)
	mux.HandleFunc("/api/prompts/", s.collectionFacade("prompts"))
	mux.HandleFunc("/api/version", s.apiVersion)
	mux.HandleFunc("/models", s.models)
	mux.HandleFunc("/lora/list", s.loraList)
	mux.HandleFunc("/lora/load", s.structuredUnavailable("lora"))
	mux.HandleFunc("/scenes/", s.collectionFacade("scenes"))
	mux.HandleFunc("/templates/", s.collectionFacade("templates"))
	mux.HandleFunc("/chat", s.chat)
	mux.HandleFunc("/api/chat", s.chat)
	mux.HandleFunc("/chat/completions", s.chatCompletions)
	mux.HandleFunc("/stream", s.stream)
	mux.HandleFunc("/agent/tasks", s.agentTasks)
	mux.HandleFunc("/agent/run", s.agentRun)
	mux.HandleFunc("/agent/abort", s.agentAbort)
	mux.HandleFunc("/agent/api-status", s.agentAPIStatus)
	mux.HandleFunc("/agent/api-test", s.agentAPITest)
	mux.HandleFunc("/agent-ide", s.agentIDE)
	mux.HandleFunc("/agent/accounts", s.collectionFacade("agent_accounts"))
	mux.HandleFunc("/agent/audit/logs", s.auditLogs)
	mux.HandleFunc("/agent/audit/stats", s.auditStats)
	mux.HandleFunc("/agent/browsable-dirs", s.browsableDirs)
	mux.HandleFunc("/agent/browser/", s.structuredUnavailable("agent_browser"))
	mux.HandleFunc("/agent/compile", s.projectCommand("compile"))
	mux.HandleFunc("/agent/events", s.agentEvents)
	mux.HandleFunc("/agent/file-analyzer/", s.structuredUnavailable("file_analyzer"))
	mux.HandleFunc("/agent/file-write", s.writeFile)
	mux.HandleFunc("/agent/identify", s.agentIdentify)
	mux.HandleFunc("/agent/import-env", s.importEnv)
	mux.HandleFunc("/agent/import-files", s.importFiles)
	mux.HandleFunc("/agent/open-project", s.openProject)
	mux.HandleFunc("/agent/permission/", s.agentPermission)
	mux.HandleFunc("/agent/plugins", s.collectionFacade("agent_plugins"))
	mux.HandleFunc("/agent/plugins/", s.collectionFacade("agent_plugins"))
	mux.HandleFunc("/agent/project-output", s.projectOutput)
	mux.HandleFunc("/agent/project-status", s.projectStatus)
	mux.HandleFunc("/agent/revert-file", s.revertFile)
	mux.HandleFunc("/agent/run-project", s.projectCommand("run_project"))
	mux.HandleFunc("/agent/stop-project", s.projectStop)
	mux.HandleFunc("/agent/system/info", s.agentSystemInfo)
	mux.HandleFunc("/agent/tasks/", s.agentTaskByID)
	mux.HandleFunc("/agent/tasks/tree", s.agentTasksTree)
	mux.HandleFunc("/agent/terminal/kill", s.terminalKill)
	mux.HandleFunc("/agent/tools", s.agentTools)
	mux.HandleFunc("/agent/user-info", s.agentUserInfo)
	mux.HandleFunc("/agent/v2/", s.agentV2)
	mux.HandleFunc("/rag/documents", s.ragDocuments)
	mux.HandleFunc("/rag/add_text", s.ragAddText)
	mux.HandleFunc("/rag/upload_metadata", s.knowledge.handleUploadMetadata)
	mux.HandleFunc("/rag/upload-metadata", s.knowledge.handleUploadMetadata)
	mux.HandleFunc("/rag/search", s.knowledge.handleSearch)
	mux.HandleFunc("/rag/stats", s.knowledge.handleStats)
	mux.HandleFunc("/rag/preview", s.knowledge.handlePreview)
	mux.HandleFunc("/rag/delete", s.knowledge.handleDelete)
	mux.HandleFunc("/rag/clear_cache", s.knowledge.handleClearCache)
	mux.HandleFunc("/rag/clear-cache", s.knowledge.handleClearCache)
	mux.HandleFunc("/rag/analysis", s.knowledge.handleStructuredUnavailable("rag_analysis"))
	mux.HandleFunc("/rag/build-graph", s.knowledge.handleStructuredUnavailable("rag_knowledge_graph"))
	mux.HandleFunc("/rag/", s.structuredUnavailable("rag"))
	mux.HandleFunc("/kaguya/features/flags", s.featureFlags)
	mux.HandleFunc("/security/status", s.securityStatus)
	mux.HandleFunc("/security/2fa/setup", s.structuredUnavailable("security_2fa"))
	mux.HandleFunc("/security/audit", s.auditLogs)
	mux.HandleFunc("/security/audit/clear", s.auditClear)
	mux.HandleFunc("/security/ip-whitelist", s.securityIPWhitelist)
	mux.HandleFunc("/security/ip-whitelist/mode", s.securityIPWhitelist)
	mux.HandleFunc("/external/config", s.externalConfig)
	mux.HandleFunc("/external/test", s.externalTest)
	mux.HandleFunc("/deepseek/test", s.deepseekTest)
	mux.HandleFunc("/deepseek/chat", s.deepseekChat)
	mux.HandleFunc("/project/", s.collectionFacade("project"))
	mux.HandleFunc("/artifacts", s.collectionFacade("artifacts"))
	mux.HandleFunc("/artifacts/", s.collectionFacade("artifacts"))
	mux.HandleFunc("/ops/", s.collectionFacade("ops"))
	mux.HandleFunc("/release/", s.collectionFacade("release"))
	mux.HandleFunc("/alerts/", s.collectionFacade("alerts"))
	mux.HandleFunc("/ab/", s.collectionFacade("ab"))
	mux.HandleFunc("/integrations", s.collectionFacade("integrations"))
	mux.HandleFunc("/integrations/", s.collectionFacade("integrations"))
	mux.HandleFunc("/workspace/projects", s.workspaceProjects)
	mux.HandleFunc("/workspace/projects/", s.collectionFacade("workspace_projects"))
	mux.HandleFunc("/console/", s.consoleStatus)
	mux.HandleFunc("/system/metrics", s.systemMetrics)
	mux.HandleFunc("/performance/", s.collectionFacade("performance"))
	mux.HandleFunc("/services/health-check", s.servicesHealth)
	mux.HandleFunc("/services/", s.structuredUnavailable("service_control"))
	mux.HandleFunc("/dependencies/", s.collectionFacade("dependencies"))
	mux.HandleFunc("/git/status", s.gitStatus)
	mux.HandleFunc("/scheduler/", s.collectionFacade("scheduler"))
	mux.HandleFunc("/audio/", s.audioFile)
	mux.HandleFunc("/chats/export", s.chatsExport)
	mux.HandleFunc("/code/execute", s.codeExecute)
	mux.HandleFunc("/dataflow/stats", s.dataflowStats)
	mux.HandleFunc("/deepseek-icon", s.imageAsset("deepseek-icon.png"))
	mux.HandleFunc("/sidebar-icon", s.imageAsset("sidebar-icon.png"))
	mux.HandleFunc("/deploy/execute", s.structuredUnavailable("deploy_execute"))
	mux.HandleFunc("/kb/add", s.kbAdd)
	mux.HandleFunc("/kb/search", s.kbSearch)
	mux.HandleFunc("/memory", s.collectionFacade("memory"))
	mux.HandleFunc("/memory/", s.structuredUnavailable("memory"))
	mux.HandleFunc("/playbooks", s.collectionFacade("playbooks"))
	mux.HandleFunc("/playbooks/", s.collectionFacade("playbooks"))
	mux.HandleFunc("/privacy/delete", s.privacyDelete)
	mux.HandleFunc("/privacy/export", s.privacyExport)
	mux.HandleFunc("/privacy/settings", s.privacySettings)
	mux.HandleFunc("/search/global", s.structuredUnavailable("global_search"))
	mux.HandleFunc("/tool/execute", s.codeExecute)
	mux.HandleFunc("/tts", s.structuredUnavailable("tts"))
	mux.HandleFunc("/web/", s.structuredUnavailable("web"))
	mux.HandleFunc("/multimodal/", s.structuredUnavailable("multimodal"))
	mux.HandleFunc("/finetune/", s.structuredUnavailable("finetune"))
	mux.HandleFunc("/workflow", s.collectionFacade("workflow"))
	mux.HandleFunc("/workflow/", s.collectionFacade("workflow"))
	mux.HandleFunc("/workflows", s.collectionFacade("workflow"))
	mux.HandleFunc("/mcp/", s.structuredUnavailable("mcp"))
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

func (s *Server) serveIndex(w http.ResponseWriter, r *http.Request) bool {
	if r.URL.Path != "/" {
		return false
	}
	candidates := []string{}
	if s.cfg.StaticDir != "" {
		candidates = append(candidates, filepath.Join(s.cfg.StaticDir, "index.html"))
	}
	candidates = append(candidates, filepath.Join(s.runtimeDir, "static", "index.html"))
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
			http.ServeFile(w, r, candidate)
			return true
		}
	}
	return false
}

func (s *Server) staticFile(w http.ResponseWriter, r *http.Request) {
	if s.cfg.AppDir == "" {
		writeError(w, http.StatusNotFound, "static_not_configured", "app-dir is not configured")
		return
	}
	rel := strings.TrimPrefix(r.URL.Path, "/static/")
	target, err := safeJoin(filepath.Join(s.cfg.AppDir, "static"), rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_static", err.Error())
		return
	}
	http.ServeFile(w, r, target)
}

func (s *Server) assetFile(w http.ResponseWriter, r *http.Request) {
	if s.cfg.AppDir == "" {
		writeError(w, http.StatusNotFound, "assets_not_configured", "app-dir is not configured")
		return
	}
	rel := strings.TrimPrefix(r.URL.Path, "/assets/")
	target, err := safeJoin(filepath.Join(s.cfg.AppDir, "assets"), rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_assets", err.Error())
		return
	}
	http.ServeFile(w, r, target)
}

func (s *Server) imageAsset(name string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if s.cfg.AppDir == "" {
			writeError(w, http.StatusNotFound, "asset_not_configured", "app-dir is not configured")
			return
		}
		for _, candidate := range s.imageAssetCandidates(name) {
			if _, err := os.Stat(candidate.root); err != nil {
				continue
			}
			target, err := safeJoin(candidate.root, candidate.name)
			if err != nil {
				writeError(w, http.StatusForbidden, "outside_assets", err.Error())
				return
			}
			info, err := os.Stat(target)
			if err == nil && !info.IsDir() {
				http.ServeFile(w, r, target)
				return
			}
		}
		writeError(w, http.StatusNotFound, "asset_not_found", fmt.Sprintf("%s is not available", name))
	}
}

type imageAssetCandidate struct {
	root string
	name string
}

func (s *Server) imageAssetCandidates(name string) []imageAssetCandidate {
	appAssets := filepath.Join(s.cfg.AppDir, "assets")
	electronAssets := filepath.Join(s.cfg.AppDir, "..", "app.asar.src", "assets")
	candidates := []imageAssetCandidate{{root: appAssets, name: name}}

	switch name {
	case "sidebar-icon.png", "deepseek-icon.png":
		candidates = append(candidates,
			imageAssetCandidate{root: appAssets, name: "kaguya-welcome.png"},
			imageAssetCandidate{root: appAssets, name: "kaguya-header.png"},
			imageAssetCandidate{root: electronAssets, name: "kaguya.png"},
		)
	case "favicon.ico":
		candidates = append(candidates,
			imageAssetCandidate{root: electronAssets, name: "kaguya.ico"},
		)
	}

	return candidates
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

func (s *Server) accountProfile(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/auth/account" {
		s.authAccount.handleAuthAccountV2(w, r)
		return
	}
	s.authAccount.handleAccountProfileV2(w, r)
}

func (s *Server) accountSessions(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAccountSessionsV2(w, r)
}

func (s *Server) accountTokens(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAccountTokensV2(w, r)
}

func (s *Server) authLogin(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthLoginV2(w, r)
}

func (s *Server) authLogout(w http.ResponseWriter, r *http.Request) {
	if strings.HasSuffix(r.URL.Path, "/logout-all") {
		s.authAccount.handleAuthLogoutAllV2(w, r)
		return
	}
	s.authAccount.handleAuthLogoutV2(w, r)
}

func (s *Server) authRegister(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthRegisterV2(w, r)
}

func (s *Server) authSetup(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthSetupV2(w, r)
}

func (s *Server) authToken(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthTokenV2(w, r)
}

func (s *Server) authPasswordReset(w http.ResponseWriter, r *http.Request) {
	if strings.HasSuffix(r.URL.Path, "/confirm") {
		s.authAccount.handleAuthPasswordResetConfirmV2(w, r)
		return
	}
	s.authAccount.handleAuthPasswordResetRequestV2(w, r)
}

func (s *Server) authAdminAccounts(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthAdminAccountsV2(w, r)
}

func (s *Server) authAdminRole(w http.ResponseWriter, r *http.Request) {
	s.authAccount.handleAuthAdminRoleV2(w, r)
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
			"error":     "missing_api_key",
			"message":   "Streaming chat requires a saved external provider API key.",
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
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "tasks": s.agentRuntime.Tasks(), "mode": "go"})
}

func (s *Server) agentRun(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	start, err := s.agentRuntime.StartRun(r.Context(), AgentRunRequest{
		Message:        firstString(payload, "message", "prompt", "input"),
		WorkingDir:     firstString(payload, "working_dir", "workingDir", "cwd"),
		DeviceID:       firstString(payload, "device_id", "deviceId"),
		SessionID:      firstString(payload, "session_id", "sessionId"),
		ParentTaskID:   firstString(payload, "parent_task_id", "parentTaskId"),
		PermissionMode: s.permissions.Mode,
		Metadata:       payload,
	})
	if err != nil {
		writeError(w, http.StatusInternalServerError, "agent_runtime_failed", err.Error())
		return
	}
	if s.agentRuntime.CheckAbort(start.RunID) {
		snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusAborted, errors.New("aborted"))
		writeSSE(w, start.Frame, s.agentRuntime.AbortFrame(start.RunID), s.agentRuntime.DoneFrame(snapshot))
		return
	}
	cfg := s.normalizedConfig(payload)
	if cfg.APIKey == "" {
		snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusFailed, errors.New("missing_external_provider_api_key"))
		writeSSE(w, start.Frame, AgentSSEPayload{
			"type":      AgentFrameUnavailable,
			"success":   false,
			"run_id":    start.RunID,
			"available": false,
			"error":     "missing_api_key",
			"message":   "Agent run requires a saved external provider API key or an apiKey/api_key in the request.",
			"mode":      "go",
		}, s.agentRuntime.DoneFrame(snapshot))
		return
	}
	runCtx, ok := s.agentRuntime.RunContext(start.RunID)
	if !ok {
		writeSSE(w, start.Frame, s.agentRuntime.AbortFrame(start.RunID))
		return
	}
	result, err := s.providerChat.complete(runCtx, cfg, payload, providerChatOptions{})
	if s.agentRuntime.CheckAbort(start.RunID) {
		snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusAborted, errors.New("aborted"))
		writeSSE(w, start.Frame, s.agentRuntime.AbortFrame(start.RunID), s.agentRuntime.DoneFrame(snapshot))
		return
	}
	if err != nil {
		snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusFailed, err)
		writeSSE(w, start.Frame, AgentSSEPayload{
			"type":    "error",
			"success": false,
			"run_id":  start.RunID,
			"error":   "provider_request_failed",
			"message": err.Error(),
			"mode":    "go",
		}, s.agentRuntime.DoneFrame(snapshot))
		return
	}
	if result.StatusCode >= 400 {
		msg := "provider request failed"
		code := "provider_error"
		if result.JSON != nil {
			if v := firstString(result.JSON, "message"); v != "" {
				msg = v
			}
			if v := firstString(result.JSON, "error"); v != "" {
				code = v
			}
		}
		snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusFailed, errors.New(code))
		writeSSE(w, start.Frame, AgentSSEPayload{
			"type":        "error",
			"success":     false,
			"run_id":      start.RunID,
			"status_code": result.StatusCode,
			"error":       code,
			"message":     msg,
			"mode":        "go",
		}, s.agentRuntime.DoneFrame(snapshot))
		return
	}
	response := ""
	if result.JSON != nil {
		response = firstString(result.JSON, "response")
	}
	snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusCompleted, nil)
	writeSSE(w, start.Frame, AgentSSEPayload{
		"type":     "message",
		"success":  true,
		"run_id":   start.RunID,
		"task_id":  start.TaskID,
		"role":     "assistant",
		"content":  response,
		"provider": cfg.Provider,
		"model":    cfg.Model,
		"mode":     "go",
	}, s.agentRuntime.DoneFrame(snapshot))
}

func (s *Server) ragDocuments(w http.ResponseWriter, r *http.Request) {
	s.knowledge.handleDocuments(w, r)
}

func (s *Server) ragAddText(w http.ResponseWriter, r *http.Request) {
	s.knowledge.handleAddText(w, r)
}

func (s *Server) featureFlags(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "features": map[string]any{"go_backend": true, "python_worker": s.proxy != nil}})
}

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
	result := s.providerChat.testConfig(context.Background(), cfg)
	writeJSON(w, result.StatusCode, result.JSON)
}

func (s *Server) deepseekChat(w http.ResponseWriter, r *http.Request) {
	body, _ := io.ReadAll(io.LimitReader(r.Body, 8<<20))
	_ = r.Body.Close()
	var payload map[string]any
	_ = json.Unmarshal(body, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	payload["provider"] = "deepseek"
	existing, _ := s.loadDeviceConfig()
	if !strings.EqualFold(existing.Provider, "deepseek") {
		existing = deviceConfig{}
	}
	cfg := pcsNormalizeExternalProviderConfig(payload, existing)
	s.providerChat.serve(w, r, cfg, payload, providerChatOptions{})
}

func (s *Server) agentAPIStatus(w http.ResponseWriter, r *http.Request) {
	s.modelStatus(w, r)
}

func (s *Server) agentAPITest(w http.ResponseWriter, r *http.Request) {
	s.externalTest(w, r)
}

func (s *Server) agentIDE(w http.ResponseWriter, r *http.Request) {
	if s.serveIndex(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "page": "agent-ide", "python_worker": s.proxy != nil})
}

func (s *Server) auditLogs(w http.ResponseWriter, r *http.Request) {
	limit := 200
	if raw := r.URL.Query().Get("limit"); raw != "" {
		if parsed := intFromString(raw); parsed > 0 {
			limit = parsed
		}
	}
	logs, err := s.terminal.Audit.Read(limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "audit_read_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "logs": logs})
}

func (s *Server) auditStats(w http.ResponseWriter, r *http.Request) {
	stats, err := s.terminal.Audit.Stats()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "audit_stats_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "stats": stats, "total": stats.Total})
}

func (s *Server) auditClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	if err := s.terminal.Audit.Clear(); err != nil {
		writeError(w, http.StatusInternalServerError, "audit_clear_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "cleared": true})
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

func (s *Server) browsableDirs(w http.ResponseWriter, r *http.Request) {
	root := s.workspace.WorkspaceRoot()
	projects, _ := s.workspace.TrustedProjects()
	dirs := []map[string]any{{"path": root, "trusted": true, "scope": "workspace"}}
	for _, project := range projects {
		dirs = append(dirs, map[string]any{"path": project.Root, "trusted": project.Trusted, "scope": "imported_project", "name": project.Name})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"dirs":    dirs,
	})
}

func (s *Server) agentEvents(w http.ResponseWriter, r *http.Request) {
	writeSSE(w, map[string]any{"type": "ready", "success": true, "mode": "go", "python_worker": s.proxy != nil})
}

func (s *Server) agentIdentify(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "agent_id": "kaguya-go", "capabilities": []string{"config", "workspace_files", "safe_terminal"}})
}

func (s *Server) importEnv(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "env_import_unavailable", "environment import requires explicit Python worker support")
}

func (s *Server) importFiles(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	if !boolValue(payload["confirmed"]) && !boolValue(payload["user_confirmed"]) && !boolValue(payload["trusted"]) {
		writeError(w, http.StatusForbidden, "confirmation_required", "project import requires explicit user confirmation from the desktop picker")
		return
	}
	path := firstString(payload, "path", "root", "project_path", "projectPath")
	project, err := s.workspace.TrustProject(path, "desktop_picker")
	if err != nil {
		writeError(w, http.StatusForbidden, "import_denied", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "project": project})
}

func (s *Server) openProject(w http.ResponseWriter, r *http.Request) {
	var payload map[string]any
	_ = readJSON(r, &payload)
	root := firstString(payload, "path", "root", "workspace", "workspace_root", "workspaceRoot")
	if boolValue(payload["confirmed"]) || boolValue(payload["user_confirmed"]) || boolValue(payload["trusted"]) {
		project, err := s.workspace.TrustProject(root, "desktop_picker")
		if err != nil {
			writeError(w, http.StatusForbidden, "trust_project_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "project": project, "trusted": true})
		return
	}
	preview, err := s.workspace.PreviewProject(root, 50)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_workspace", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":               true,
		"mode":                  "go",
		"preview":               preview,
		"path":                  preview.Root,
		"trusted":               false,
		"requires_confirmation": true,
		"message":               "Go backend can preview this project path but does not trust it until the desktop picker confirms import.",
	})
}

func (s *Server) agentPermission(w http.ResponseWriter, r *http.Request) {
	switch {
	case strings.HasSuffix(r.URL.Path, "/config"):
		s.permissionsStatus(w, r)
	case strings.HasSuffix(r.URL.Path, "/respond"):
		writeJSON(w, http.StatusOK, map[string]any{"success": false, "mode": "go", "error": "permission_request_not_found"})
	case strings.HasSuffix(r.URL.Path, "/rule"):
		s.collectionFacade("permission_rules")(w, r)
	case strings.HasSuffix(r.URL.Path, "/sandbox-dir"):
		s.browsableDirs(w, r)
	default:
		writeError(w, http.StatusNotFound, "unknown_permission_route", "unknown permission route")
	}
}

func (s *Server) projectOutput(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "project": s.projectExec.Output(64 * 1024)})
}

func (s *Server) projectStatus(w http.ResponseWriter, r *http.Request) {
	status := s.projectExec.Status()
	status["success"] = true
	status["mode"] = "go"
	writeJSON(w, http.StatusOK, status)
}

func (s *Server) workspaceProjects(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		projects, err := s.workspace.TrustedProjects()
		if err != nil {
			writeError(w, http.StatusInternalServerError, "trusted_projects_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"success":        true,
			"mode":           "go",
			"workspace_root": s.workspace.WorkspaceRoot(),
			"projects":       projects,
		})
		return
	}
	if r.Method == http.MethodPost {
		s.importFiles(w, r)
		return
	}
	methodNotAllowed(w)
}

func (s *Server) revertFile(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}
	snapshotID := firstString(payload, "snapshot_id", "snapshotId", "id")
	if snapshotID == "" {
		writeError(w, http.StatusBadRequest, "missing_snapshot_id", "snapshot_id is required")
		return
	}
	result, err := s.workspace.RevertSnapshot(snapshotID)
	if err != nil {
		writeError(w, http.StatusForbidden, "revert_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "result": result})
}

func (s *Server) projectCommand(action string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			methodNotAllowed(w)
			return
		}
		var payload map[string]any
		if err := readJSON(r, &payload); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
			return
		}
		s.terminal.Mode = s.permissions.Mode
		record, err := s.projectExec.Execute(r.Context(), action, payload)
		if err != nil {
			writeError(w, http.StatusForbidden, action+"_denied", err.Error())
			return
		}
		status := http.StatusOK
		if !record.Result.Executed && !record.Result.Decision.Allowed {
			status = http.StatusForbidden
		}
		writeJSON(w, status, map[string]any{"success": record.Result.Success, "mode": "go", "project_run": record, "result": record.Result})
	}
}

func (s *Server) projectStop(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.projectExec.Stop())
}

func (s *Server) agentSystemInfo(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"system":  map[string]any{"os": runtime.GOOS, "arch": runtime.GOARCH, "workspace_root": s.workspaceRoot, "python_worker": s.proxy != nil},
	})
}

func (s *Server) agentTaskByID(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"path":    r.URL.Path,
		"task":    map[string]any{"id": strings.TrimPrefix(r.URL.Path, "/agent/tasks/"), "status": "unavailable"},
	})
}

func (s *Server) agentTasksTree(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "tree": s.agentRuntime.TaskTree()})
}

func (s *Server) terminalKill(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "killed": false, "reason": "no_go_managed_process"})
}

func (s *Server) agentTools(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"tools": []map[string]any{
			{"name": "read_file", "risk_level": "low"},
			{"name": "write_file", "risk_level": "medium"},
			{"name": "execute_command", "risk_level": "high"},
		},
	})
}

func (s *Server) agentUserInfo(w http.ResponseWriter, r *http.Request) {
	s.accountProfile(w, r)
}

func (s *Server) agentV2(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	switch {
	case strings.Contains(path, "/command-safety"):
		var payload map[string]any
		_ = readJSON(r, &payload)
		argv := commandArgs(payload["command"])
		risk := classifyCommand(strings.Join(argv, " "))
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "risk_level": risk, "allowed": risk == "low"})
	case strings.Contains(path, "/executor/status"):
		s.projectStatus(w, r)
	case strings.Contains(path, "/permissions/"):
		s.permissionsStatus(w, r)
	case strings.Contains(path, "/sessions"):
		s.accountSessions(w, r)
	default:
		writeError(w, http.StatusNotFound, "unknown_agent_v2_route", "unknown agent v2 route")
	}
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
	result := s.agentRuntime.AbortRun(runID)
	status := http.StatusOK
	if !result.Success {
		status = http.StatusNotFound
	}
	writeJSON(w, status, result)
}

func (s *Server) permissionsStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    s.permissions.Mode,
		"ok":      true,
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
		s.terminal.Mode = mode
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
	if tool == "execute_command" || tool == "terminal_exec" || tool == "run_project" || tool == "compile" {
		toolInput, _ := payload["tool_input"].(map[string]any)
		if toolInput == nil {
			toolInput, _ = payload["input"].(map[string]any)
		}
		req := TerminalCommandRequest{
			Command: firstString(toolInput, "command"),
			Argv:    commandArgs(toolInput["argv"]),
			Shell:   boolValue(toolInput["shell"]),
		}
		normalized, err := s.terminal.Normalize(req)
		if err != nil {
			decision := PermissionDecision{Allowed: false, Reason: err.Error(), RiskLevel: RiskCritical, RequiresConfirmation: true}
			writeJSON(w, http.StatusOK, map[string]any{
				"success":               true,
				"allowed":               false,
				"auto_approved":         false,
				"requires_confirmation": decision.RequiresConfirmation,
				"mode":                  s.permissions.Mode,
				"tool_name":             tool,
				"risk_level":            decision.RiskLevel,
				"reason":                decision.Reason,
			})
			return
		}
		decision := s.terminal.Check(normalized)
		writeJSON(w, http.StatusOK, map[string]any{
			"success":               true,
			"allowed":               decision.Allowed,
			"auto_approved":         decision.Allowed,
			"requires_confirmation": decision.RequiresConfirmation,
			"mode":                  s.permissions.Mode,
			"tool_name":             tool,
			"risk_level":            decision.RiskLevel,
			"reason":                decision.Reason,
			"permission_id":         decision.PermissionID,
		})
		return
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
	root, rel, err := workspaceRequestRootPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	depth := intFromString(r.URL.Query().Get("depth"))
	if depth == 0 {
		depth = 1
	}
	entries, err := s.workspace.FileTree(root, rel, depth)
	if err != nil {
		writeError(w, http.StatusForbidden, "workspace_denied", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "root": root, "path": filepath.ToSlash(rel), "entries": entries})
}

func (s *Server) readFile(w http.ResponseWriter, r *http.Request) {
	root, rel, err := workspaceRequestRootPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	result, err := s.workspace.ReadFile(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "read_denied", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "path": result.Path, "content": result.Content, "size": result.Size, "modified_at": result.ModifiedAt})
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
	root := firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root")
	rel := firstString(payload, "path", "file_path", "filePath")
	content := firstString(payload, "content")
	result, err := s.workspace.WriteFile(root, rel, content, boolValue(payload["is_dir"]) || boolValue(payload["isDir"]))
	if err != nil {
		writeError(w, http.StatusForbidden, "write_denied", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "ok": true, "mode": "go", "result": result, "path": result.Path, "snapshot_id": result.SnapshotID})
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
	pathOverrides := r.MultipartForm.Value["paths"]
	root := r.FormValue("workspace")
	if root == "" {
		root = r.FormValue("workspace_root")
	}
	type pendingUpload struct {
		header *multipart.FileHeader
		meta   UploadMetadata
	}
	pending := []pendingUpload{}
	fileIndex := 0
	for _, headers := range r.MultipartForm.File {
		for _, header := range headers {
			rel := header.Filename
			if fileIndex < len(pathOverrides) && pathOverrides[fileIndex] != "" {
				rel = pathOverrides[fileIndex]
			}
			pending = append(pending, pendingUpload{
				header: header,
				meta:   s.workspace.BuildUploadMetadata(header.Filename, rel, header.Size, nil),
			})
			fileIndex++
		}
	}
	metas := make([]UploadMetadata, 0, len(pending))
	for _, item := range pending {
		metas = append(metas, item.meta)
	}
	prepared, err := s.workspace.PrepareUploadEntries(root, metas)
	if err != nil {
		writeError(w, http.StatusForbidden, "upload_denied", err.Error())
		return
	}
	for i, upload := range prepared {
		src, err := pending[i].header.Open()
		if err != nil {
			writeError(w, http.StatusBadRequest, "upload_open_failed", err.Error())
			return
		}
		if err := os.MkdirAll(filepath.Dir(upload.Target), 0o755); err != nil {
			_ = src.Close()
			writeError(w, http.StatusInternalServerError, "upload_mkdir_failed", err.Error())
			return
		}
		dst, err := os.OpenFile(upload.Target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
		if err != nil {
			_ = src.Close()
			writeError(w, http.StatusInternalServerError, "upload_create_failed", err.Error())
			return
		}
		_, copyErr := io.Copy(dst, src)
		closeErr := dst.Close()
		_ = src.Close()
		if copyErr != nil {
			writeError(w, http.StatusInternalServerError, "upload_write_failed", copyErr.Error())
			return
		}
		if closeErr != nil {
			writeError(w, http.StatusInternalServerError, "upload_close_failed", closeErr.Error())
			return
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "ok": true, "mode": "go", "uploaded": len(prepared), "files": prepared})
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
	root := firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root")
	cwdRel := firstString(payload, "cwd", "working_dir", "workingDir")
	decision, err := s.workspace.AuthorizePath("execute_command", root, cwdRel, false)
	if err != nil {
		reqArgv := commandArgs(payload["argv"])
		if len(reqArgv) == 0 {
			reqArgv = commandArgs(payload["command"])
		}
		perm := PermissionDecision{Allowed: false, Reason: "working_dir denied: " + err.Error(), RiskLevel: RiskHigh, RequiresConfirmation: true}
		event := s.terminal.appendAudit("terminal_exec", perm, TerminalAuditEvent{
			Allowed:    false,
			RiskLevel:  perm.RiskLevel,
			Reason:     perm.Reason,
			Command:    reqArgv,
			WorkingDir: cwdRel,
			Error:      err.Error(),
		})
		perm.AuditID = event.AuditID
		writeJSON(w, http.StatusForbidden, TerminalExecutionResult{
			Success:    false,
			Executed:   false,
			Decision:   perm,
			Command:    reqArgv,
			RiskLevel:  perm.RiskLevel,
			WorkingDir: cwdRel,
			ExitCode:   -1,
			Error:      err.Error(),
			AuditID:    event.AuditID,
		})
		return
	}
	req := TerminalCommandRequest{
		Command:    firstString(payload, "command"),
		Argv:       commandArgs(payload["argv"]),
		WorkingDir: decision.Target,
		Shell:      boolValue(payload["shell"]),
		TimeoutMs:  intValue(payload["timeout_ms"]),
	}
	if req.Command == "" && len(req.Argv) == 0 {
		writeError(w, http.StatusBadRequest, "missing_command", "command or argv is required")
		return
	}
	result := s.terminal.Execute(r.Context(), req)
	status := http.StatusOK
	if !result.Executed && !result.Decision.Allowed {
		status = http.StatusForbidden
	}
	writeJSON(w, status, result)
}

func (s *Server) proxyFallback(w http.ResponseWriter, r *http.Request) {
	if s.serveIndex(w, r) {
		return
	}
	if s.proxy == nil {
		if r.URL.Path == "/" {
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte("<!doctype html><meta charset=\"utf-8\"><title>Kaguya Go Backend</title><h1>Kaguya Go Backend</h1><p>Core APIs are online. Python compatibility worker is unavailable.</p>"))
			return
		}
		writeError(w, http.StatusServiceUnavailable, "route_not_implemented_in_go", "route is not implemented in the Go backend")
		return
	}
	s.proxy.ServeHTTP(w, r)
}

func (s *Server) collectionFacade(domain string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		key := domain + "_" + safeName(r.URL.Path)
		if r.Method == http.MethodGet {
			items, err := s.loadCollection(key)
			if err != nil {
				writeError(w, http.StatusInternalServerError, "load_failed", err.Error())
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{
				"success": true,
				"mode":    "go",
				"domain":  domain,
				"path":    r.URL.Path,
				"items":   items,
			})
			return
		}
		if r.Method == http.MethodPost || r.Method == http.MethodPut || r.Method == http.MethodPatch {
			var payload map[string]any
			_ = readJSON(r, &payload)
			if payload == nil {
				payload = map[string]any{}
			}
			payload["updated_at"] = time.Now().UTC().Format(time.RFC3339)
			if payload["id"] == nil || payload["id"] == "" {
				payload["id"] = domain + "-" + time.Now().UTC().Format("20060102150405.000000000")
			}
			items, _ := s.loadCollection(key)
			items = upsertCollectionItem(items, payload)
			if err := s.saveCollection(key, items); err != nil {
				writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "domain": domain, "item": payload, "items": items})
			return
		}
		if r.Method == http.MethodDelete {
			if err := s.saveCollection(key, []map[string]any{}); err != nil {
				writeError(w, http.StatusInternalServerError, "delete_failed", err.Error())
				return
			}
			writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "domain": domain, "deleted": true})
			return
		}
		methodNotAllowed(w)
	}
}

func (s *Server) structuredUnavailable(feature string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"success":   false,
			"available": false,
			"mode":      "go",
			"feature":   feature,
			"error":     "worker_not_configured",
			"message":   feature + " is not yet implemented in the Go backend.",
		})
	}
}

func (s *Server) consoleStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "path": r.URL.Path, "status": "ok", "backend": "go"})
}

func (s *Server) systemMetrics(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"metrics": map[string]any{
			"runtime_dir":     s.runtimeDir,
			"goos":            runtime.GOOS,
			"python_worker":   s.proxy != nil,
			"workspace_root":  s.workspaceRoot,
			"permission_mode": s.permissions.Mode,
		},
	})
}

func (s *Server) servicesHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"services": []map[string]any{
			{"id": "go-backend", "status": "healthy"},
			{"id": "python-worker", "status": map[bool]string{true: "available", false: "unavailable"}[s.proxy != nil]},
		},
	})
}

func (s *Server) gitStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "repositories": []any{}, "available": false, "reason": "git_status_not_configured"})
}

func (s *Server) audioFile(w http.ResponseWriter, r *http.Request) {
	if s.cfg.AppDir == "" {
		writeError(w, http.StatusNotFound, "audio_not_configured", "audio asset directory is not configured")
		return
	}
	rel := strings.TrimPrefix(r.URL.Path, "/audio/")
	target, err := safeJoin(filepath.Join(s.cfg.AppDir, "audio_cache"), rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_audio_cache", err.Error())
		return
	}
	http.ServeFile(w, r, target)
}

func (s *Server) chatsExport(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"format":  "json",
		"chats":   []any{},
	})
}

func (s *Server) codeExecute(w http.ResponseWriter, r *http.Request) {
	risk := classifyTool("execute_command")
	s.audit("code_execute", map[string]any{"allowed": false, "risk_level": risk, "reason": "permission_required"})
	writeJSON(w, http.StatusForbidden, map[string]any{
		"success":               false,
		"mode":                  "go",
		"allowed":               false,
		"requires_confirmation": true,
		"risk_level":            risk,
		"error":                 "permission_required",
	})
}

func (s *Server) dataflowStats(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "stats": map[string]any{"events": 0, "pipelines": 0}})
}

func (s *Server) kbAdd(w http.ResponseWriter, r *http.Request) {
	s.knowledge.handleAddText(w, r)
}

func (s *Server) kbSearch(w http.ResponseWriter, r *http.Request) {
	s.knowledge.handleSearch(w, r)
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

func workspaceRequestRootPath(r *http.Request) (string, string, error) {
	if r.Method == http.MethodGet {
		root := r.URL.Query().Get("workspace")
		if root == "" {
			root = r.URL.Query().Get("workspace_root")
		}
		if root == "" {
			root = r.URL.Query().Get("root")
		}
		return root, r.URL.Query().Get("path"), nil
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		return "", "", err
	}
	return firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root"),
		firstString(payload, "path", "file_path", "filePath"), nil
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
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}

func boolValue(value any) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return strings.EqualFold(v, "true") || v == "1" || strings.EqualFold(v, "yes")
	case float64:
		return v != 0
	case int:
		return v != 0
	default:
		return false
	}
}

func intValue(value any) int {
	switch v := value.(type) {
	case int:
		return v
	case float64:
		return int(v)
	case string:
		var n int
		if _, err := fmt.Sscanf(v, "%d", &n); err == nil {
			return n
		}
	}
	return 0
}

func intFromString(value string) int {
	return intValue(strings.TrimSpace(value))
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

func chatCompletionsURL(base string) string {
	base = strings.TrimRight(base, "/")
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	return base + "/chat/completions"
}

func providerModelsURL(base string) string {
	base = strings.TrimRight(base, "/")
	if strings.HasSuffix(base, "/models") {
		return base
	}
	if strings.HasSuffix(base, "/chat/completions") {
		return strings.TrimSuffix(base, "/chat/completions") + "/models"
	}
	return base + "/models"
}

func extractAssistantContent(upstream map[string]any) string {
	choices, _ := upstream["choices"].([]any)
	if len(choices) == 0 {
		return ""
	}
	first, _ := choices[0].(map[string]any)
	if first == nil {
		return ""
	}
	message, _ := first["message"].(map[string]any)
	if message == nil {
		return firstString(first, "text", "content")
	}
	return firstString(message, "content")
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

func (s *Server) collectionPath(key string) string {
	return filepath.Join(s.runtimeDir, "go_collections", key+".json")
}

func (s *Server) loadCollection(key string) ([]map[string]any, error) {
	path := s.collectionPath(key)
	b, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return []map[string]any{}, nil
	}
	if err != nil {
		return nil, err
	}
	var items []map[string]any
	if err := json.Unmarshal(b, &items); err != nil {
		return nil, err
	}
	return items, nil
}

func (s *Server) saveCollection(key string, items []map[string]any) error {
	path := s.collectionPath(key)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(items, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o600)
}

func upsertCollectionItem(items []map[string]any, item map[string]any) []map[string]any {
	id := fmt.Sprint(item["id"])
	for i := range items {
		if fmt.Sprint(items[i]["id"]) == id {
			items[i] = item
			return items
		}
	}
	return append(items, item)
}

func safeName(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	if value == "" {
		return "default"
	}
	var b strings.Builder
	for _, r := range value {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
			continue
		}
		b.WriteByte('_')
	}
	out := strings.Trim(b.String(), "_")
	if out == "" {
		return "default"
	}
	return out
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
