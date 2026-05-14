package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

type RiskLevel string

const (
	RiskLow      RiskLevel = "low"
	RiskMedium   RiskLevel = "medium"
	RiskHigh     RiskLevel = "high"
	RiskCritical RiskLevel = "critical"
)

type PermissionDecision struct {
	Allowed              bool      `json:"allowed"`
	Reason               string    `json:"reason"`
	RiskLevel            RiskLevel `json:"risk_level"`
	RequiresConfirmation bool      `json:"requires_confirmation"`
	PermissionID         string    `json:"permission_id,omitempty"`
	AuditID              string    `json:"audit_id,omitempty"`
}

type TerminalCommandRequest struct {
	Command    string        `json:"command,omitempty"`
	Argv       []string      `json:"argv,omitempty"`
	WorkingDir string        `json:"working_dir,omitempty"`
	Shell      bool          `json:"shell,omitempty"`
	Timeout    time.Duration `json:"-"`
	TimeoutMs  int           `json:"timeout_ms,omitempty"`
	Env        []string      `json:"env,omitempty"`
}

type TerminalExecutionResult struct {
	Success    bool               `json:"success"`
	Executed   bool               `json:"executed"`
	Decision   PermissionDecision `json:"decision"`
	Command    []string           `json:"command"`
	RiskLevel  RiskLevel          `json:"risk_level"`
	WorkingDir string             `json:"working_dir,omitempty"`
	Stdout     string             `json:"stdout,omitempty"`
	Stderr     string             `json:"stderr,omitempty"`
	ExitCode   int                `json:"exit_code"`
	Timeout    bool               `json:"timeout"`
	Error      string             `json:"error,omitempty"`
	AuditID    string             `json:"audit_id,omitempty"`
	DurationMS int64              `json:"duration_ms"`
}

type TerminalAuditEvent struct {
	AuditID    string         `json:"audit_id"`
	TS         string         `json:"ts"`
	Action     string         `json:"action"`
	Allowed    bool           `json:"allowed"`
	RiskLevel  RiskLevel      `json:"risk_level"`
	Reason     string         `json:"reason,omitempty"`
	Command    []string       `json:"command,omitempty"`
	WorkingDir string         `json:"working_dir,omitempty"`
	ExitCode   int            `json:"exit_code,omitempty"`
	Timeout    bool           `json:"timeout,omitempty"`
	DurationMS int64          `json:"duration_ms,omitempty"`
	Error      string         `json:"error,omitempty"`
	Fields     map[string]any `json:"fields,omitempty"`
}

type TerminalAuditStats struct {
	Total       int            `json:"total"`
	Allowed     int            `json:"allowed"`
	Denied      int            `json:"denied"`
	Timeouts    int            `json:"timeouts"`
	ByRisk      map[string]int `json:"by_risk"`
	ByAction    map[string]int `json:"by_action"`
	LastAuditID string         `json:"last_audit_id,omitempty"`
}

type TerminalAuditStore struct {
	path string
	now  func() time.Time
	mu   sync.Mutex
}

type TerminalPermissionService struct {
	Mode           string
	Audit          *TerminalAuditStore
	DefaultTimeout time.Duration
	MaxOutputBytes int
}

func NewTerminalAuditStore(path string) *TerminalAuditStore {
	return &TerminalAuditStore{path: path, now: time.Now}
}

func NewTerminalPermissionService(auditPath string) *TerminalPermissionService {
	return &TerminalPermissionService{
		Mode:           "ask",
		Audit:          NewTerminalAuditStore(auditPath),
		DefaultTimeout: 30 * time.Second,
		MaxOutputBytes: 64 * 1024,
	}
}

func (s *TerminalPermissionService) Normalize(req TerminalCommandRequest) (TerminalCommandRequest, error) {
	if req.Shell {
		return req, errors.New("shell mode is disabled by default")
	}
	if len(req.Argv) == 0 {
		argv, err := ParseTerminalCommandLine(req.Command)
		if err != nil {
			return req, err
		}
		req.Argv = argv
	}
	req.Argv = cleanArgv(req.Argv)
	if len(req.Argv) == 0 {
		return req, errors.New("empty command")
	}
	if req.Timeout == 0 && req.TimeoutMs > 0 {
		req.Timeout = time.Duration(req.TimeoutMs) * time.Millisecond
	}
	if req.Timeout == 0 {
		req.Timeout = s.DefaultTimeout
	}
	if req.Timeout <= 0 {
		req.Timeout = 30 * time.Second
	}
	return req, nil
}

func (s *TerminalPermissionService) Check(req TerminalCommandRequest) PermissionDecision {
	if req.Shell {
		return PermissionDecision{
			Allowed:              false,
			Reason:               "shell mode is disabled; commands must be parsed as argv and executed with shell=false",
			RiskLevel:            RiskCritical,
			RequiresConfirmation: true,
		}
	}
	argv := cleanArgv(req.Argv)
	if len(argv) == 0 {
		return PermissionDecision{Allowed: false, Reason: "empty command", RiskLevel: RiskLow}
	}
	risk := ClassifyTerminalCommand(argv)
	if reason := DangerousTerminalCommandReason(argv); reason != "" {
		return PermissionDecision{
			Allowed:              false,
			Reason:               reason,
			RiskLevel:            RiskCritical,
			RequiresConfirmation: true,
		}
	}
	mode := strings.ToLower(strings.TrimSpace(s.Mode))
	if mode == "" {
		mode = "ask"
	}
	switch mode {
	case "deny", "blocked", "off":
		return PermissionDecision{Allowed: false, Reason: "permission mode denies terminal execution", RiskLevel: risk}
	case "allow":
		return PermissionDecision{Allowed: true, Reason: "permission mode allows terminal execution", RiskLevel: risk}
	default:
		if risk == RiskLow {
			return PermissionDecision{Allowed: true, Reason: "low risk command allowed", RiskLevel: risk}
		}
		return PermissionDecision{
			Allowed:              false,
			Reason:               "command requires explicit confirmation",
			RiskLevel:            risk,
			RequiresConfirmation: true,
			PermissionID:         newAuditID("perm"),
		}
	}
}

func (s *TerminalPermissionService) Execute(ctx context.Context, req TerminalCommandRequest) TerminalExecutionResult {
	start := time.Now()
	normalized, err := s.Normalize(req)
	if err != nil {
		decision := PermissionDecision{Allowed: false, Reason: err.Error(), RiskLevel: RiskCritical, RequiresConfirmation: true}
		event := s.appendAudit("terminal_exec", decision, TerminalAuditEvent{
			Allowed:    false,
			RiskLevel:  decision.RiskLevel,
			Reason:     decision.Reason,
			Command:    req.Argv,
			WorkingDir: req.WorkingDir,
			Error:      err.Error(),
		})
		decision.AuditID = event.AuditID
		return TerminalExecutionResult{
			Success:    false,
			Executed:   false,
			Decision:   decision,
			Command:    req.Argv,
			RiskLevel:  decision.RiskLevel,
			WorkingDir: req.WorkingDir,
			ExitCode:   -1,
			Error:      err.Error(),
			AuditID:    event.AuditID,
			DurationMS: elapsedMS(start),
		}
	}
	decision := s.Check(normalized)
	if !decision.Allowed {
		event := s.appendAudit("terminal_exec", decision, TerminalAuditEvent{
			Allowed:    false,
			RiskLevel:  decision.RiskLevel,
			Reason:     decision.Reason,
			Command:    normalized.Argv,
			WorkingDir: normalized.WorkingDir,
		})
		decision.AuditID = event.AuditID
		return TerminalExecutionResult{
			Success:    false,
			Executed:   false,
			Decision:   decision,
			Command:    normalized.Argv,
			RiskLevel:  decision.RiskLevel,
			WorkingDir: normalized.WorkingDir,
			ExitCode:   -1,
			Error:      decision.Reason,
			AuditID:    event.AuditID,
			DurationMS: elapsedMS(start),
		}
	}
	timeout := normalized.Timeout
	if timeout <= 0 {
		timeout = s.DefaultTimeout
	}
	runCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	stdout := &limitedBuffer{limit: s.outputLimit()}
	stderr := &limitedBuffer{limit: s.outputLimit()}
	cmd := exec.CommandContext(runCtx, normalized.Argv[0], normalized.Argv[1:]...)
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	if normalized.WorkingDir != "" {
		cmd.Dir = normalized.WorkingDir
	}
	if len(normalized.Env) > 0 {
		cmd.Env = append(os.Environ(), normalized.Env...)
	}

	err = cmd.Run()
	timedOut := errors.Is(runCtx.Err(), context.DeadlineExceeded)
	exitCode := 0
	errText := ""
	if err != nil {
		exitCode = -1
		errText = err.Error()
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		}
	}
	if timedOut {
		exitCode = -1
		errText = "command timed out"
	}
	result := TerminalExecutionResult{
		Success:    err == nil && !timedOut,
		Executed:   true,
		Decision:   decision,
		Command:    normalized.Argv,
		RiskLevel:  decision.RiskLevel,
		WorkingDir: normalized.WorkingDir,
		Stdout:     stdout.String(),
		Stderr:     stderr.String(),
		ExitCode:   exitCode,
		Timeout:    timedOut,
		Error:      errText,
		DurationMS: elapsedMS(start),
	}
	event := s.appendAudit("terminal_exec", decision, TerminalAuditEvent{
		Allowed:    decision.Allowed,
		RiskLevel:  decision.RiskLevel,
		Reason:     decision.Reason,
		Command:    normalized.Argv,
		WorkingDir: normalized.WorkingDir,
		ExitCode:   exitCode,
		Timeout:    timedOut,
		DurationMS: result.DurationMS,
		Error:      errText,
	})
	result.AuditID = event.AuditID
	result.Decision.AuditID = event.AuditID
	return result
}

func ParseTerminalCommandLine(command string) ([]string, error) {
	command = strings.TrimSpace(command)
	if command == "" {
		return nil, nil
	}
	var args []string
	var current strings.Builder
	inSingle := false
	inDouble := false
	escaped := false
	hadToken := false
	for _, r := range command {
		switch {
		case escaped:
			current.WriteRune(r)
			escaped = false
			hadToken = true
		case r == '\\' && !inSingle:
			escaped = true
			hadToken = true
		case r == '\'' && !inDouble:
			inSingle = !inSingle
			hadToken = true
		case r == '"' && !inSingle:
			inDouble = !inDouble
			hadToken = true
		case isTerminalSpace(r) && !inSingle && !inDouble:
			if hadToken {
				args = append(args, current.String())
				current.Reset()
				hadToken = false
			}
		default:
			current.WriteRune(r)
			hadToken = true
		}
	}
	if escaped {
		current.WriteRune('\\')
	}
	if inSingle || inDouble {
		return nil, errors.New("unterminated quote in command")
	}
	if hadToken {
		args = append(args, current.String())
	}
	return cleanArgv(args), nil
}

func ClassifyTerminalCommandLine(command string) RiskLevel {
	argv, err := ParseTerminalCommandLine(command)
	if err != nil {
		return RiskCritical
	}
	return ClassifyTerminalCommand(argv)
}

func ClassifyTerminalCommand(argv []string) RiskLevel {
	argv = cleanArgv(argv)
	if len(argv) == 0 {
		return RiskLow
	}
	if DangerousTerminalCommandReason(argv) != "" {
		return RiskCritical
	}
	base := normalizedCommandBase(argv[0])
	if len(argv) == 2 && isVersionArg(argv[1]) {
		return RiskLow
	}
	if isReadOnlyCommand(base, argv) {
		return RiskLow
	}
	switch base {
	case "go":
		if len(argv) > 1 && inSet(argv[1], "test", "build", "vet", "fmt", "version", "env") {
			if argv[1] == "version" || argv[1] == "env" {
				return RiskLow
			}
			return RiskMedium
		}
		return RiskHigh
	case "pytest", "ruff", "mypy", "eslint", "tsc":
		return RiskMedium
	case "npm", "pnpm", "yarn":
		if len(argv) > 1 && inSet(argv[1], "test", "run", "build", "lint") {
			return RiskMedium
		}
		return RiskHigh
	case "git":
		if len(argv) > 1 && inSet(argv[1], "status", "log", "diff", "show", "branch") {
			return RiskLow
		}
		return RiskHigh
	case "pip", "pip3", "uv", "curl", "wget":
		return RiskHigh
	case "python", "python3", "py", "node", "deno", "ruby", "perl", "cmd", "powershell", "pwsh", "bash", "sh":
		if len(argv) > 1 && isVersionArg(argv[1]) {
			return RiskLow
		}
		return RiskHigh
	default:
		if looksLikeScript(argv[0]) {
			return RiskHigh
		}
		return RiskLow
	}
}

func DangerousTerminalCommandReason(argv []string) string {
	argv = cleanArgv(argv)
	if len(argv) == 0 {
		return ""
	}
	joined := strings.ToLower(strings.Join(argv, " "))
	for _, token := range []string{"&&", "||", ";", "`", "$(", "|", ">", "<"} {
		if containsToken(argv, token) || strings.Contains(joined, token) {
			return "shell metacharacters are not allowed with shell=false"
		}
	}
	base := normalizedCommandBase(argv[0])
	switch base {
	case "rm", "del", "erase", "rmdir", "rd", "remove-item", "ri", "format", "diskpart", "shutdown", "reboot", "mkfs", "dd", "takeown", "icacls", "reg":
		return "destructive command is denied: " + base
	case "powershell", "pwsh":
		if strings.Contains(joined, "invoke-expression") || strings.Contains(joined, "iex") ||
			strings.Contains(joined, "downloadstring") || strings.Contains(joined, "invoke-webrequest") ||
			strings.Contains(joined, "iwr ") || strings.Contains(joined, "start-process") {
			return "download-and-execute PowerShell patterns are denied"
		}
	case "curl", "wget":
		if strings.Contains(joined, "| sh") || strings.Contains(joined, "| bash") || strings.Contains(joined, " -o- ") {
			return "download-and-pipe execution patterns are denied"
		}
	}
	for _, arg := range argv[1:] {
		lower := strings.ToLower(arg)
		if base == "rm" && strings.Contains(lower, "rf") {
			return "recursive forced deletion is denied"
		}
		if inSet(lower, "/s", "/q") && inSet(base, "del", "erase", "rmdir", "rd") {
			return "recursive Windows deletion is denied"
		}
	}
	return ""
}

func (s *TerminalAuditStore) Append(event TerminalAuditEvent) (TerminalAuditEvent, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.path == "" {
		return TerminalAuditEvent{}, errors.New("audit path is required")
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return TerminalAuditEvent{}, err
	}
	if event.AuditID == "" {
		event.AuditID = newAuditID("audit")
	}
	if event.TS == "" {
		now := time.Now
		if s.now != nil {
			now = s.now
		}
		event.TS = now().UTC().Format(time.RFC3339Nano)
	}
	b, err := json.Marshal(event)
	if err != nil {
		return TerminalAuditEvent{}, err
	}
	f, err := os.OpenFile(s.path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return TerminalAuditEvent{}, err
	}
	defer f.Close()
	if _, err := f.Write(append(b, '\n')); err != nil {
		return TerminalAuditEvent{}, err
	}
	return event, nil
}

func (s *TerminalAuditStore) Read(limit int) ([]TerminalAuditEvent, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return readTerminalAuditEvents(s.path, limit)
}

func (s *TerminalAuditStore) Stats() (TerminalAuditStats, error) {
	events, err := s.Read(0)
	if err != nil {
		return TerminalAuditStats{}, err
	}
	stats := TerminalAuditStats{ByRisk: map[string]int{}, ByAction: map[string]int{}}
	for _, event := range events {
		stats.Total++
		if event.Allowed {
			stats.Allowed++
		} else {
			stats.Denied++
		}
		if event.Timeout {
			stats.Timeouts++
		}
		if event.RiskLevel != "" {
			stats.ByRisk[string(event.RiskLevel)]++
		}
		if event.Action != "" {
			stats.ByAction[event.Action]++
		}
		stats.LastAuditID = event.AuditID
	}
	return stats, nil
}

func (s *TerminalAuditStore) Clear() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.path == "" {
		return errors.New("audit path is required")
	}
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return err
	}
	return os.WriteFile(s.path, nil, 0o600)
}

func (s *TerminalPermissionService) appendAudit(action string, decision PermissionDecision, event TerminalAuditEvent) TerminalAuditEvent {
	if s.Audit == nil {
		return TerminalAuditEvent{}
	}
	event.Action = action
	event.Allowed = decision.Allowed
	if event.RiskLevel == "" {
		event.RiskLevel = decision.RiskLevel
	}
	if event.Reason == "" {
		event.Reason = decision.Reason
	}
	written, err := s.Audit.Append(event)
	if err != nil {
		return TerminalAuditEvent{Error: err.Error()}
	}
	return written
}

func readTerminalAuditEvents(path string, limit int) ([]TerminalAuditEvent, error) {
	f, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		return []TerminalAuditEvent{}, nil
	}
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var events []TerminalAuditEvent
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		var event TerminalAuditEvent
		if err := json.Unmarshal(line, &event); err != nil {
			return nil, fmt.Errorf("decode audit line %d: %w", lineNo, err)
		}
		events = append(events, event)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if limit > 0 && len(events) > limit {
		events = events[len(events)-limit:]
	}
	return events, nil
}

type limitedBuffer struct {
	limit int
	buf   bytes.Buffer
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	if b.limit <= 0 {
		return len(p), nil
	}
	remaining := b.limit - b.buf.Len()
	if remaining > 0 {
		if len(p) > remaining {
			_, _ = b.buf.Write(p[:remaining])
		} else {
			_, _ = b.buf.Write(p)
		}
	}
	return len(p), nil
}

func (b *limitedBuffer) String() string {
	return b.buf.String()
}

func (s *TerminalPermissionService) outputLimit() int {
	if s.MaxOutputBytes <= 0 {
		return 64 * 1024
	}
	return s.MaxOutputBytes
}

func cleanArgv(argv []string) []string {
	out := make([]string, 0, len(argv))
	for _, arg := range argv {
		if strings.TrimSpace(arg) == "" {
			continue
		}
		out = append(out, arg)
	}
	return out
}

func normalizedCommandBase(cmd string) string {
	base := strings.ToLower(filepath.Base(strings.TrimSpace(cmd)))
	base = strings.TrimSuffix(base, ".exe")
	base = strings.TrimSuffix(base, ".cmd")
	base = strings.TrimSuffix(base, ".bat")
	return base
}

func isReadOnlyCommand(base string, argv []string) bool {
	switch base {
	case "ls", "dir", "pwd", "whoami", "hostname", "date", "echo", "cat", "type", "where", "which":
		return true
	}
	if len(argv) > 1 && isVersionArg(argv[1]) {
		return true
	}
	return false
}

func isVersionArg(arg string) bool {
	return inSet(strings.ToLower(arg), "--version", "-v", "version", "-version")
}

func looksLikeScript(path string) bool {
	lower := strings.ToLower(path)
	for _, suffix := range []string{".ps1", ".sh", ".bat", ".cmd", ".py", ".js", ".mjs", ".rb", ".pl"} {
		if strings.HasSuffix(lower, suffix) {
			return true
		}
	}
	return false
}

func containsToken(argv []string, token string) bool {
	for _, arg := range argv {
		if arg == token {
			return true
		}
	}
	return false
}

func inSet(value string, options ...string) bool {
	for _, option := range options {
		if value == option {
			return true
		}
	}
	return false
}

func isTerminalSpace(r rune) bool {
	return r == ' ' || r == '\t' || r == '\n' || r == '\r'
}

func newAuditID(prefix string) string {
	var b [8]byte
	if _, err := io.ReadFull(rand.Reader, b[:]); err != nil {
		return fmt.Sprintf("%s-%d", prefix, time.Now().UnixNano())
	}
	return prefix + "-" + hex.EncodeToString(b[:])
}

func elapsedMS(start time.Time) int64 {
	return time.Since(start).Milliseconds()
}

func SortedAuditRiskKeys(stats TerminalAuditStats) []string {
	keys := make([]string, 0, len(stats.ByRisk))
	for key := range stats.ByRisk {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func terminalPlatformShellName() string {
	if runtime.GOOS == "windows" {
		return "cmd"
	}
	return "sh"
}
