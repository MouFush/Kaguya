package main

import (
    "net/http"
    "os/exec"
    "strings"
    "time"
    "context"
    "bytes"
    "errors"
)

func (s *Server) terminalKill(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "killed": false, "reason": "no_go_managed_process"})
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
	argv := commandArgs(payload["command"])
	if len(argv) == 0 {
		argv = commandArgs(payload["argv"])
	}
	if len(argv) == 0 {
		writeError(w, http.StatusBadRequest, "missing_command", "command or argv is required")
		return
	}
	risk := classifyCommand(strings.Join(argv, " "))
	if reason := dangerousCommand(argv); reason != "" {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": reason})
		writeError(w, http.StatusForbidden, "dangerous_command", reason)
		return
	}
	if risk == "high" || risk == "critical" {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": "permission_required"})
		writeError(w, http.StatusForbidden, "permission_required", "high risk commands require explicit permission")
		return
	}
	root, err := workspaceRoot(payload)
	if err != nil {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "reason": err.Error()})
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	cwd := firstString(payload, "cwd")
	if cwd == "" {
		cwd = root
	}
	cwd, err = safeJoin(root, cwd)
	if err != nil {
		s.audit("terminal_exec", map[string]any{"allowed": false, "risk_level": risk, "command": argv, "working_dir": cwd, "reason": err.Error()})
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	timeout := 30 * time.Second
	ctx, cancel := context.WithTimeout(r.Context(), timeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, argv[0], argv[1:]...)
	cmd.Dir = cwd
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err = cmd.Run()
	exitCode := 0
	if err != nil {
		exitCode = 1
		var ee *exec.ExitError
		if errors.As(err, &ee) {
			exitCode = ee.ExitCode()
		}
	}
	timedOut := ctx.Err() == context.DeadlineExceeded
	s.audit("terminal_exec", map[string]any{"allowed": true, "risk_level": risk, "command": argv, "working_dir": cwd, "exit_code": exitCode, "timeout": timedOut})
	writeJSON(w, http.StatusOK, map[string]any{
		"success":    err == nil && !timedOut,
		"ok":         err == nil && !timedOut,
		"exit_code":  exitCode,
		"stdout":     stdout.String(),
		"stderr":     stderr.String(),
		"shell":      false,
		"risk_level": risk,
		"timeout":    timedOut,
	})
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
		writeError(w, http.StatusServiceUnavailable, "python_worker_unavailable", "route is implemented by the Python worker")
		return
	}
	s.proxy.ServeHTTP(w, r)
}
