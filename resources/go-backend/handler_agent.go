package main

import (
    "net/http"
    "encoding/json"
    "io"
    "os"
    "strings"
    "time"
    "errors"
    "path/filepath"
    "runtime"
    "bytes"
)

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
	snapshot, _ := s.agentRuntime.FinishRun(start.RunID, AgentRunStatusAborted, errors.New("python_worker_unavailable"))
	writeSSE(w, start.Frame, s.agentRuntime.UnavailableFrame(start.RunID), s.agentRuntime.DoneFrame(snapshot))
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
	path := filepath.Join(s.runtimeDir, "audit_logs", "go_audit.jsonl")
	b, err := os.ReadFile(path)
	if err != nil {
		writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "logs": []any{}})
		return
	}
	lines := strings.Split(strings.TrimSpace(string(b)), "\n")
	logs := make([]map[string]any, 0, len(lines))
	for _, line := range lines {
		if line == "" {
			continue
		}
		var item map[string]any
		if json.Unmarshal([]byte(line), &item) == nil {
			logs = append(logs, item)
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "logs": logs})
}

func (s *Server) auditStats(w http.ResponseWriter, r *http.Request) {
	path := filepath.Join(s.runtimeDir, "audit_logs", "go_audit.jsonl")
	b, _ := os.ReadFile(path)
	count := 0
	if len(b) > 0 {
		count = len(strings.Split(strings.TrimSpace(string(b)), "\n"))
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "total": count})
}

func (s *Server) auditClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	path := filepath.Join(s.runtimeDir, "audit_logs", "go_audit.jsonl")
	if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
		writeError(w, http.StatusInternalServerError, "audit_clear_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "cleared": true})
}

func (s *Server) agentEvents(w http.ResponseWriter, r *http.Request) {
	writeSSE(w, map[string]any{"type": "ready", "success": true, "mode": "go", "python_worker": s.proxy != nil})
}

func (s *Server) agentIdentify(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "agent_id": "kaguya-go", "capabilities": []string{"config", "workspace_files", "safe_terminal"}})
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
