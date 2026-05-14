package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

const (
	AgentRunStatusRunning   = "running"
	AgentRunStatusCompleted = "completed"
	AgentRunStatusAborted   = "aborted"
	AgentRunStatusFailed    = "failed"

	AgentTaskStatusRunning   = "running"
	AgentTaskStatusCompleted = "completed"
	AgentTaskStatusAborted   = "aborted"
	AgentTaskStatusFailed    = "failed"

	AgentFrameRunStarted         = "run_started"
	AgentFramePermissionRequired = "permission_required"
	AgentFrameUnavailable        = "unavailable"
	AgentFrameAborted            = "aborted"
	AgentFrameDone               = "done"
)

var agentRuntimeIDCounter atomic.Uint64

// AgentRuntimeService owns the Go-side Agent execution state.
//
// It intentionally does not execute tools. The service is the minimum durable
// runtime needed by HTTP handlers: create run IDs, retain abortable contexts,
// build SSE frames, keep task state, expose run status, and clean the active
// registry on every terminal path.
type AgentRuntimeService struct {
	mu      sync.RWMutex
	now     func() time.Time
	newID   func(prefix string) string
	runs    map[string]*agentRunState
	history map[string]AgentRunSnapshot
	tasks   map[string]*AgentTask
}

type agentRunState struct {
	snapshot AgentRunSnapshot
	ctx      context.Context
	cancel   context.CancelFunc
}

type AgentRunRequest struct {
	Message        string         `json:"message,omitempty"`
	WorkingDir     string         `json:"working_dir,omitempty"`
	DeviceID       string         `json:"device_id,omitempty"`
	SessionID      string         `json:"session_id,omitempty"`
	ParentTaskID   string         `json:"parent_task_id,omitempty"`
	PermissionMode string         `json:"permission_mode,omitempty"`
	MaxIterations  int            `json:"max_iterations,omitempty"`
	Metadata       map[string]any `json:"metadata,omitempty"`
}

type AgentRunStart struct {
	RunID     string           `json:"run_id"`
	TaskID    string           `json:"task_id"`
	Frame     AgentSSEPayload  `json:"frame"`
	SSE       string           `json:"sse"`
	Snapshot  AgentRunSnapshot `json:"snapshot"`
	CreatedAt time.Time        `json:"created_at"`
}

type AgentRunSnapshot struct {
	RunID           string         `json:"run_id"`
	TaskID          string         `json:"task_id"`
	ParentTaskID    string         `json:"parent_task_id,omitempty"`
	Message         string         `json:"message,omitempty"`
	WorkingDir      string         `json:"working_dir,omitempty"`
	DeviceID        string         `json:"device_id,omitempty"`
	SessionID       string         `json:"session_id,omitempty"`
	Status          string         `json:"status"`
	AbortRequested  bool           `json:"abort_requested"`
	PermissionMode  string         `json:"permission_mode,omitempty"`
	MaxIterations   int            `json:"max_iterations,omitempty"`
	CreatedAt       time.Time      `json:"created_at"`
	UpdatedAt       time.Time      `json:"updated_at"`
	FinishedAt      *time.Time     `json:"finished_at,omitempty"`
	Error           string         `json:"error,omitempty"`
	TerminalFrame   string         `json:"terminal_frame,omitempty"`
	Metadata        map[string]any `json:"metadata,omitempty"`
	RegistryPresent bool           `json:"registry_present"`
}

type AgentTask struct {
	ID          string         `json:"id"`
	RunID       string         `json:"run_id"`
	ParentID    string         `json:"parent_id,omitempty"`
	Title       string         `json:"title"`
	Status      string         `json:"status"`
	CreatedAt   time.Time      `json:"created_at"`
	UpdatedAt   time.Time      `json:"updated_at"`
	FinishedAt  *time.Time     `json:"finished_at,omitempty"`
	ChildrenIDs []string       `json:"children_ids,omitempty"`
	Metadata    map[string]any `json:"metadata,omitempty"`
}

type AgentTaskNode struct {
	Task     AgentTask       `json:"task"`
	Children []AgentTaskNode `json:"children,omitempty"`
}

type AgentAbortResult struct {
	Success bool   `json:"success"`
	RunID   string `json:"run_id,omitempty"`
	Aborted bool   `json:"aborted"`
	Error   string `json:"error,omitempty"`
}

type AgentToolDecision struct {
	Success              bool           `json:"success"`
	RunID                string         `json:"run_id,omitempty"`
	Tool                 string         `json:"tool,omitempty"`
	Allowed              bool           `json:"allowed"`
	Available            bool           `json:"available"`
	RequiresConfirmation bool           `json:"requires_confirmation"`
	RiskLevel            string         `json:"risk_level"`
	Error                string         `json:"error,omitempty"`
	Message              string         `json:"message,omitempty"`
	Input                map[string]any `json:"input,omitempty"`
}

type AgentSSEPayload map[string]any

func NewAgentRuntimeService() *AgentRuntimeService {
	return &AgentRuntimeService{
		now:     func() time.Time { return time.Now().UTC() },
		newID:   newAgentRuntimeID,
		runs:    map[string]*agentRunState{},
		history: map[string]AgentRunSnapshot{},
		tasks:   map[string]*AgentTask{},
	}
}

func (s *AgentRuntimeService) StartRun(parent context.Context, req AgentRunRequest) (AgentRunStart, error) {
	if s == nil {
		return AgentRunStart{}, errors.New("agent runtime service is nil")
	}
	if parent == nil {
		parent = context.Background()
	}
	now := s.now()
	runID := s.newID("run")
	taskID := s.newID("task")
	if req.MaxIterations <= 0 {
		req.MaxIterations = 1
	}
	ctx, cancel := context.WithCancel(parent)
	task := &AgentTask{
		ID:        taskID,
		RunID:     runID,
		ParentID:  req.ParentTaskID,
		Title:     agentTaskTitle(req.Message),
		Status:    AgentTaskStatusRunning,
		CreatedAt: now,
		UpdatedAt: now,
		Metadata:  cloneAgentMetadata(req.Metadata),
	}
	snapshot := AgentRunSnapshot{
		RunID:           runID,
		TaskID:          taskID,
		ParentTaskID:    req.ParentTaskID,
		Message:         req.Message,
		WorkingDir:      req.WorkingDir,
		DeviceID:        req.DeviceID,
		SessionID:       req.SessionID,
		Status:          AgentRunStatusRunning,
		PermissionMode:  req.PermissionMode,
		MaxIterations:   req.MaxIterations,
		CreatedAt:       now,
		UpdatedAt:       now,
		Metadata:        cloneAgentMetadata(req.Metadata),
		RegistryPresent: true,
	}
	frame := AgentSSEPayload{
		"type":           AgentFrameRunStarted,
		"success":        true,
		"mode":           "go",
		"run_id":         runID,
		"task_id":        taskID,
		"status":         AgentRunStatusRunning,
		"created_at":     now.Format(time.RFC3339Nano),
		"max_iterations": req.MaxIterations,
	}
	if req.ParentTaskID != "" {
		frame["parent_task_id"] = req.ParentTaskID
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.runs[runID] = &agentRunState{snapshot: snapshot, ctx: ctx, cancel: cancel}
	s.tasks[taskID] = task
	if req.ParentTaskID != "" {
		if parentTask, ok := s.tasks[req.ParentTaskID]; ok {
			parentTask.ChildrenIDs = appendUniqueString(parentTask.ChildrenIDs, taskID)
			parentTask.UpdatedAt = now
		}
	}
	return AgentRunStart{
		RunID:     runID,
		TaskID:    taskID,
		Frame:     frame,
		SSE:       BuildAgentSSEFrame(frame),
		Snapshot:  cloneAgentRunSnapshot(snapshot),
		CreatedAt: now,
	}, nil
}

func (s *AgentRuntimeService) AbortRun(runID string) AgentAbortResult {
	if strings.TrimSpace(runID) == "" {
		return AgentAbortResult{Success: false, Aborted: false, Error: "missing_run_id"}
	}
	now := s.now()
	var cancel context.CancelFunc
	s.mu.Lock()
	state, ok := s.runs[runID]
	if !ok {
		s.mu.Unlock()
		return AgentAbortResult{Success: false, RunID: runID, Aborted: false, Error: "run_not_found"}
	}
	state.snapshot.Status = AgentRunStatusAborted
	state.snapshot.AbortRequested = true
	state.snapshot.UpdatedAt = now
	state.snapshot.TerminalFrame = AgentFrameAborted
	if task := s.tasks[state.snapshot.TaskID]; task != nil {
		task.Status = AgentTaskStatusAborted
		task.UpdatedAt = now
	}
	cancel = state.cancel
	s.mu.Unlock()
	cancel()
	return AgentAbortResult{Success: true, RunID: runID, Aborted: true}
}

func (s *AgentRuntimeService) AbortFrame(runID string) AgentSSEPayload {
	return AgentSSEPayload{
		"type":    AgentFrameAborted,
		"success": false,
		"run_id":  runID,
		"aborted": true,
		"message": "Agent run aborted by user",
		"mode":    "go",
	}
}

func (s *AgentRuntimeService) FinishRun(runID, status string, err error) (AgentRunSnapshot, bool) {
	if strings.TrimSpace(runID) == "" {
		return AgentRunSnapshot{}, false
	}
	now := s.now()
	s.mu.Lock()
	defer s.mu.Unlock()
	state, ok := s.runs[runID]
	if !ok {
		if archived, exists := s.history[runID]; exists {
			return cloneAgentRunSnapshot(archived), true
		}
		return AgentRunSnapshot{}, false
	}
	if status == "" {
		status = AgentRunStatusCompleted
	}
	if state.snapshot.AbortRequested {
		status = AgentRunStatusAborted
	}
	state.snapshot.Status = status
	state.snapshot.UpdatedAt = now
	state.snapshot.FinishedAt = &now
	state.snapshot.RegistryPresent = false
	state.snapshot.TerminalFrame = terminalFrameForRunStatus(status)
	if err != nil {
		state.snapshot.Error = err.Error()
		if status == AgentRunStatusCompleted {
			state.snapshot.Status = AgentRunStatusFailed
			state.snapshot.TerminalFrame = AgentFrameDone
		}
	}
	if task := s.tasks[state.snapshot.TaskID]; task != nil {
		task.Status = taskStatusForRunStatus(state.snapshot.Status)
		task.UpdatedAt = now
		task.FinishedAt = &now
	}
	state.cancel()
	s.history[runID] = cloneAgentRunSnapshot(state.snapshot)
	delete(s.runs, runID)
	return cloneAgentRunSnapshot(state.snapshot), true
}

func (s *AgentRuntimeService) CheckAbort(runID string) bool {
	if strings.TrimSpace(runID) == "" {
		return false
	}
	s.mu.RLock()
	state, ok := s.runs[runID]
	if !ok {
		s.mu.RUnlock()
		return false
	}
	aborted := state.snapshot.AbortRequested
	ctx := state.ctx
	s.mu.RUnlock()
	if aborted {
		return true
	}
	select {
	case <-ctx.Done():
		return true
	default:
		return false
	}
}

func (s *AgentRuntimeService) RunDone(runID string) (<-chan struct{}, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	state, ok := s.runs[runID]
	if !ok {
		return nil, false
	}
	return state.ctx.Done(), true
}

func (s *AgentRuntimeService) RunStatus(runID string) (AgentRunSnapshot, bool) {
	if strings.TrimSpace(runID) == "" {
		return AgentRunSnapshot{}, false
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	if state, ok := s.runs[runID]; ok {
		cp := cloneAgentRunSnapshot(state.snapshot)
		cp.RegistryPresent = true
		return cp, true
	}
	if snapshot, ok := s.history[runID]; ok {
		return cloneAgentRunSnapshot(snapshot), true
	}
	return AgentRunSnapshot{}, false
}

func (s *AgentRuntimeService) Task(taskID string) (AgentTask, bool) {
	if strings.TrimSpace(taskID) == "" {
		return AgentTask{}, false
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	task, ok := s.tasks[taskID]
	if !ok {
		return AgentTask{}, false
	}
	return cloneAgentTask(*task), true
}

func (s *AgentRuntimeService) Tasks() []AgentTask {
	s.mu.RLock()
	defer s.mu.RUnlock()
	tasks := make([]AgentTask, 0, len(s.tasks))
	for _, task := range s.tasks {
		tasks = append(tasks, cloneAgentTask(*task))
	}
	sort.Slice(tasks, func(i, j int) bool {
		if tasks[i].CreatedAt.Equal(tasks[j].CreatedAt) {
			return tasks[i].ID < tasks[j].ID
		}
		return tasks[i].CreatedAt.Before(tasks[j].CreatedAt)
	})
	return tasks
}

func (s *AgentRuntimeService) TaskTree() []AgentTaskNode {
	s.mu.RLock()
	defer s.mu.RUnlock()
	childrenByParent := map[string][]string{}
	for _, task := range s.tasks {
		childrenByParent[task.ParentID] = append(childrenByParent[task.ParentID], task.ID)
	}
	for parent := range childrenByParent {
		sort.Strings(childrenByParent[parent])
	}
	var build func(taskID string) AgentTaskNode
	build = func(taskID string) AgentTaskNode {
		task := cloneAgentTask(*s.tasks[taskID])
		node := AgentTaskNode{Task: task}
		for _, childID := range childrenByParent[taskID] {
			if _, ok := s.tasks[childID]; ok {
				node.Children = append(node.Children, build(childID))
			}
		}
		return node
	}
	roots := make([]AgentTaskNode, 0, len(childrenByParent[""]))
	for _, taskID := range childrenByParent[""] {
		if _, ok := s.tasks[taskID]; ok {
			roots = append(roots, build(taskID))
		}
	}
	return roots
}

func (s *AgentRuntimeService) ActiveRunCount() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return len(s.runs)
}

func (s *AgentRuntimeService) ToolDecision(runID, tool string, input map[string]any) AgentToolDecision {
	tool = strings.TrimSpace(tool)
	risk := agentToolRisk(tool)
	decision := AgentToolDecision{
		Success:   false,
		RunID:     runID,
		Tool:      tool,
		Allowed:   false,
		Available: false,
		RiskLevel: risk,
		Input:     cloneAgentMetadata(input),
	}
	if s.CheckAbort(runID) {
		decision.Error = "run_aborted"
		decision.Message = "Agent run was aborted before tool execution."
		return decision
	}
	if agentToolRequiresPermission(tool) {
		decision.RequiresConfirmation = true
		decision.Error = "permission_required"
		decision.Message = "Go backend does not execute side-effecting agent tools without a permission grant."
		return decision
	}
	decision.Error = "tool_unavailable"
	decision.Message = "Go agent runtime is active, but real tool execution is not implemented in this domain worker."
	return decision
}

func (s *AgentRuntimeService) ToolDecisionFrame(runID, tool string, input map[string]any) AgentSSEPayload {
	decision := s.ToolDecision(runID, tool, input)
	frameType := AgentFrameUnavailable
	if decision.RequiresConfirmation {
		frameType = AgentFramePermissionRequired
	}
	return AgentSSEPayload{
		"type":                  frameType,
		"success":               decision.Success,
		"run_id":                decision.RunID,
		"tool":                  decision.Tool,
		"allowed":               decision.Allowed,
		"available":             decision.Available,
		"requires_confirmation": decision.RequiresConfirmation,
		"risk_level":            decision.RiskLevel,
		"error":                 decision.Error,
		"message":               decision.Message,
		"mode":                  "go",
	}
}

func (s *AgentRuntimeService) DoneFrame(snapshot AgentRunSnapshot) AgentSSEPayload {
	return AgentSSEPayload{
		"type":      AgentFrameDone,
		"done":      true,
		"success":   snapshot.Status == AgentRunStatusCompleted,
		"run_id":    snapshot.RunID,
		"task_id":   snapshot.TaskID,
		"status":    snapshot.Status,
		"aborted":   snapshot.Status == AgentRunStatusAborted,
		"error":     snapshot.Error,
		"mode":      "go",
		"available": false,
	}
}

func (s *AgentRuntimeService) UnavailableFrame(runID string) AgentSSEPayload {
	return AgentSSEPayload{
		"type":      AgentFrameUnavailable,
		"success":   false,
		"run_id":    runID,
		"available": false,
		"error":     "agent_tools_unavailable",
		"message":   "Go agent runtime can manage runs, tasks, and aborts; real tool execution is not implemented here.",
		"mode":      "go",
	}
}

func BuildAgentSSEFrame(payload AgentSSEPayload) string {
	b, err := json.Marshal(payload)
	if err != nil {
		fallback, _ := json.Marshal(AgentSSEPayload{
			"type":    "error",
			"success": false,
			"error":   "sse_encode_failed",
			"message": err.Error(),
		})
		b = fallback
	}
	return "data: " + string(b) + "\n\n"
}

func BuildAgentSSEFrames(frames ...AgentSSEPayload) string {
	var b strings.Builder
	for _, frame := range frames {
		b.WriteString(BuildAgentSSEFrame(frame))
	}
	return b.String()
}

func ParseAgentSSEFrame(frame string) (AgentSSEPayload, error) {
	frame = strings.TrimSpace(frame)
	if !strings.HasPrefix(frame, "data: ") {
		return nil, fmt.Errorf("invalid sse frame prefix")
	}
	var payload AgentSSEPayload
	if err := json.Unmarshal([]byte(strings.TrimPrefix(frame, "data: ")), &payload); err != nil {
		return nil, err
	}
	return payload, nil
}

func newAgentRuntimeID(prefix string) string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err == nil {
		return prefix + "-" + hex.EncodeToString(b[:])
	}
	n := agentRuntimeIDCounter.Add(1)
	return fmt.Sprintf("%s-%d-%d", prefix, time.Now().UTC().UnixNano(), n)
}

func agentTaskTitle(message string) string {
	message = strings.TrimSpace(message)
	if message == "" {
		return "Agent run"
	}
	fields := strings.Fields(message)
	title := strings.Join(fields, " ")
	if len(title) > 80 {
		return title[:77] + "..."
	}
	return title
}

func agentToolRisk(tool string) string {
	t := strings.ToLower(strings.TrimSpace(tool))
	switch t {
	case "read_file", "list_files", "file_tree", "search", "grep", "inspect":
		return "low"
	case "write_file", "edit_file", "create_directory", "import_files":
		return "medium"
	case "execute_command", "run_project", "compile", "web_fetch", "pip_install", "npm_install":
		return "high"
	case "delete_file", "rm", "format", "shutdown", "open_external":
		return "critical"
	default:
		return "medium"
	}
}

func agentToolRequiresPermission(tool string) bool {
	switch agentToolRisk(tool) {
	case "medium", "high", "critical":
		return true
	default:
		return false
	}
}

func taskStatusForRunStatus(status string) string {
	switch status {
	case AgentRunStatusCompleted:
		return AgentTaskStatusCompleted
	case AgentRunStatusAborted:
		return AgentTaskStatusAborted
	case AgentRunStatusFailed:
		return AgentTaskStatusFailed
	default:
		return AgentTaskStatusRunning
	}
}

func terminalFrameForRunStatus(status string) string {
	switch status {
	case AgentRunStatusAborted:
		return AgentFrameAborted
	default:
		return AgentFrameDone
	}
}

func appendUniqueString(items []string, value string) []string {
	for _, item := range items {
		if item == value {
			return items
		}
	}
	return append(items, value)
}

func cloneAgentMetadata(in map[string]any) map[string]any {
	if len(in) == 0 {
		return nil
	}
	out := make(map[string]any, len(in))
	for k, v := range in {
		out[k] = v
	}
	return out
}

func cloneAgentRunSnapshot(in AgentRunSnapshot) AgentRunSnapshot {
	in.Metadata = cloneAgentMetadata(in.Metadata)
	if in.FinishedAt != nil {
		t := *in.FinishedAt
		in.FinishedAt = &t
	}
	return in
}

func cloneAgentTask(in AgentTask) AgentTask {
	in.Metadata = cloneAgentMetadata(in.Metadata)
	if in.FinishedAt != nil {
		t := *in.FinishedAt
		in.FinishedAt = &t
	}
	if len(in.ChildrenIDs) > 0 {
		in.ChildrenIDs = append([]string(nil), in.ChildrenIDs...)
	}
	return in
}
