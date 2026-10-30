package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
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
		cfg:           cfg,
		runtimeDir:    cfg.RuntimeDir,
		workspaceRoot: filepath.Join(cfg.RuntimeDir, "workspaces"),
		devicePath:    filepath.Join(cfg.RuntimeDir, "device_vault.enc"),
		permissions:   permissionState{Mode: "ask"},
		providerChat:  newProviderChatService(nil),
		agentRuntime:  NewAgentRuntimeService(),
	}
	securityPrivacy, err := NewSecurityPrivacyService(cfg.RuntimeDir)
	if err != nil {
		return nil, err
	}
	s.securityPrivacy = securityPrivacy
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
	mux.HandleFunc("/css/", s.staticDirFile)
	mux.HandleFunc("/js/", s.staticDirFile)
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
	mux.HandleFunc("/workspace/projects", s.collectionFacade("workspace_projects"))
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
	rel := strings.TrimPrefix(r.URL.Path, "/static/")
	var candidates []string
	if s.cfg.StaticDir != "" {
		candidates = append(candidates, filepath.Join(s.cfg.StaticDir, rel))
	}
	if s.cfg.AppDir != "" {
		candidates = append(candidates, filepath.Join(s.cfg.AppDir, "static", rel))
	}
	if len(candidates) == 0 {
		writeError(w, http.StatusNotFound, "static_not_configured", "no static directory configured")
		return
	}
	for _, candidate := range candidates {
		dir := filepath.Dir(candidate)
		base := filepath.Base(candidate)
		target, err := safeJoin(dir, base)
		if err != nil {
			continue
		}
		if _, err := os.Stat(target); err == nil {
			http.ServeFile(w, r, target)
			return
		}
	}
	writeError(w, http.StatusNotFound, "file_not_found", "static file not found")
}
func (s *Server) staticDirFile(w http.ResponseWriter, r *http.Request) {
	if s.cfg.StaticDir == "" {
		writeError(w, http.StatusNotFound, "static_not_configured", "static-dir is not configured")
		return
	}
	rel := strings.TrimPrefix(r.URL.Path, "/")
	target, err := safeJoin(s.cfg.StaticDir, rel)
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
		target, err := safeJoin(filepath.Join(s.cfg.AppDir, "assets"), name)
		if err != nil {
			writeError(w, http.StatusForbidden, "outside_assets", err.Error())
			return
		}
		http.ServeFile(w, r, target)
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

func hostName() string {
	name, err := os.Hostname()
	if err != nil || name == "" {
		return "desktop"
	}
	return name
}
