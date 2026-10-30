package main

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type ProjectExecutionService struct {
	mu        sync.Mutex
	runs      []ProjectExecutionRecord
	terminal  *TerminalPermissionService
	workspace *WorkspaceProjectService
}

type ProjectExecutionRecord struct {
	ID        string                  `json:"id"`
	Action    string                  `json:"action"`
	Command   []string                `json:"command"`
	Root      string                  `json:"root"`
	StartedAt string                  `json:"started_at"`
	EndedAt   string                  `json:"ended_at,omitempty"`
	Running   bool                    `json:"running"`
	Result    TerminalExecutionResult `json:"result"`
}

func NewProjectExecutionService(workspace *WorkspaceProjectService, terminal *TerminalPermissionService) *ProjectExecutionService {
	return &ProjectExecutionService{workspace: workspace, terminal: terminal}
}

func (svc *ProjectExecutionService) Execute(ctx context.Context, action string, payload map[string]any) (ProjectExecutionRecord, error) {
	if svc == nil || svc.workspace == nil || svc.terminal == nil {
		return ProjectExecutionRecord{}, errors.New("project execution service is not initialized")
	}
	if payload == nil {
		payload = map[string]any{}
	}
	rootRaw := firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root", "path", "project_path", "projectPath")
	decision, err := svc.workspace.AuthorizePath(action, rootRaw, ".", false)
	if err != nil {
		return ProjectExecutionRecord{}, err
	}
	argv := commandArgs(payload["argv"])
	if len(argv) == 0 {
		argv = commandArgs(payload["command"])
	}
	if len(argv) == 0 {
		argv = inferProjectCommand(action, decision.Target)
	}
	if len(argv) == 0 {
		return ProjectExecutionRecord{}, errors.New("command is required and no project command could be inferred")
	}
	timeoutMs := intValue(payload["timeout_ms"])
	if timeoutMs == 0 {
		timeoutMs = intValue(payload["timeoutMs"])
	}
	record := ProjectExecutionRecord{
		ID:        newAuditID("proj"),
		Action:    action,
		Command:   cleanArgv(argv),
		Root:      decision.Target,
		StartedAt: time.Now().UTC().Format(time.RFC3339Nano),
		Running:   true,
	}
	svc.store(record)
	result := svc.terminal.Execute(ctx, TerminalCommandRequest{
		Argv:       record.Command,
		WorkingDir: record.Root,
		Shell:      boolValue(payload["shell"]),
		TimeoutMs:  timeoutMs,
	})
	record.Running = false
	record.EndedAt = time.Now().UTC().Format(time.RFC3339Nano)
	record.Result = result
	svc.store(record)
	return record, nil
}

func (svc *ProjectExecutionService) Status() map[string]any {
	if svc == nil {
		return map[string]any{"running": false, "runs": []ProjectExecutionRecord{}}
	}
	svc.mu.Lock()
	defer svc.mu.Unlock()
	runs := append([]ProjectExecutionRecord(nil), svc.runs...)
	running := false
	for _, run := range runs {
		if run.Running {
			running = true
			break
		}
	}
	return map[string]any{"running": running, "runs": runs}
}

func (svc *ProjectExecutionService) Output(limit int) map[string]any {
	if svc == nil {
		return map[string]any{"running": false, "output": ""}
	}
	svc.mu.Lock()
	defer svc.mu.Unlock()
	if len(svc.runs) == 0 {
		return map[string]any{"running": false, "output": "", "runs": []ProjectExecutionRecord{}}
	}
	last := svc.runs[len(svc.runs)-1]
	output := strings.TrimSpace(last.Result.Stdout + "\n" + last.Result.Stderr)
	if limit > 0 && len(output) > limit {
		output = output[len(output)-limit:]
	}
	return map[string]any{"running": last.Running, "output": output, "last": last}
}

func (svc *ProjectExecutionService) Stop() map[string]any {
	if svc == nil {
		return map[string]any{"success": true, "stopped": false, "reason": "project execution service unavailable"}
	}
	return map[string]any{"success": true, "mode": "go", "stopped": false, "reason": "no asynchronous Go-managed project process is running"}
}

func (svc *ProjectExecutionService) store(record ProjectExecutionRecord) {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	for i := range svc.runs {
		if svc.runs[i].ID == record.ID {
			svc.runs[i] = record
			return
		}
	}
	svc.runs = append(svc.runs, record)
	if len(svc.runs) > 50 {
		svc.runs = svc.runs[len(svc.runs)-50:]
	}
}

func inferProjectCommand(action, root string) []string {
	action = strings.ToLower(strings.TrimSpace(action))
	if root == "" {
		return nil
	}
	if fileExists(filepath.Join(root, "go.mod")) {
		if action == "compile" {
			return []string{"go", "test", "./..."}
		}
		return []string{"go", "run", "."}
	}
	if fileExists(filepath.Join(root, "package.json")) {
		if action == "compile" {
			return []string{"npm", "run", "build"}
		}
		return []string{"npm", "run", "dev"}
	}
	if fileExists(filepath.Join(root, "pyproject.toml")) || fileExists(filepath.Join(root, "pytest.ini")) {
		if action == "compile" {
			return []string{"pytest"}
		}
	}
	return nil
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
