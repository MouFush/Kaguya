package main

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func newDeterministicAgentRuntime() *AgentRuntimeService {
	svc := NewAgentRuntimeService()
	base := time.Date(2026, 5, 15, 8, 0, 0, 0, time.UTC)
	var ticks int
	svc.now = func() time.Time {
		ticks++
		return base.Add(time.Duration(ticks) * time.Second)
	}
	var ids int
	svc.newID = func(prefix string) string {
		ids++
		return prefix + "-test-" + string(rune('a'+ids-1))
	}
	return svc
}

func decodeAgentSSEPayload(t *testing.T, frame string) AgentSSEPayload {
	t.Helper()
	got, err := ParseAgentSSEFrame(frame)
	if err != nil {
		t.Fatalf("parse sse frame: %v: %q", err, frame)
	}
	return got
}

func TestAgentRuntimeRunStartedFirstFrame(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	start, err := svc.StartRun(context.Background(), AgentRunRequest{
		Message:        "build a task",
		DeviceID:       "device-1",
		SessionID:      "session-1",
		PermissionMode: "ask",
		MaxIterations:  3,
	})
	if err != nil {
		t.Fatal(err)
	}
	if start.RunID == "" || start.TaskID == "" {
		t.Fatalf("missing ids: %#v", start)
	}
	payload := decodeAgentSSEPayload(t, start.SSE)
	if payload["type"] != AgentFrameRunStarted {
		t.Fatalf("first frame type=%#v payload=%#v", payload["type"], payload)
	}
	if payload["run_id"] != start.RunID {
		t.Fatalf("run_id mismatch: %#v", payload)
	}
	if payload["task_id"] != start.TaskID {
		t.Fatalf("task_id mismatch: %#v", payload)
	}
	if payload["status"] != AgentRunStatusRunning {
		t.Fatalf("status mismatch: %#v", payload)
	}
	if svc.ActiveRunCount() != 1 {
		t.Fatalf("active run count=%d", svc.ActiveRunCount())
	}
	status, ok := svc.RunStatus(start.RunID)
	if !ok || !status.RegistryPresent || status.Status != AgentRunStatusRunning {
		t.Fatalf("bad run status ok=%v status=%#v", ok, status)
	}
}

func TestAgentRuntimeAbortUnknown(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	got := svc.AbortRun("missing-run")
	if got.Success || got.Aborted || got.Error != "run_not_found" {
		t.Fatalf("unexpected abort unknown result: %#v", got)
	}
	empty := svc.AbortRun("")
	if empty.Success || empty.Aborted || empty.Error != "missing_run_id" {
		t.Fatalf("unexpected empty abort result: %#v", empty)
	}
}

func TestAgentRuntimeAbortActive(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	start, err := svc.StartRun(context.Background(), AgentRunRequest{Message: "abort me"})
	if err != nil {
		t.Fatal(err)
	}
	done, ok := svc.RunDone(start.RunID)
	if !ok {
		t.Fatal("run context not found before abort")
	}
	got := svc.AbortRun(start.RunID)
	if !got.Success || !got.Aborted || got.RunID != start.RunID {
		t.Fatalf("unexpected abort active result: %#v", got)
	}
	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatal("abort did not cancel run context")
	}
	if !svc.CheckAbort(start.RunID) {
		t.Fatal("CheckAbort returned false for aborted active run")
	}
	frame := svc.AbortFrame(start.RunID)
	if frame["type"] != AgentFrameAborted || frame["run_id"] != start.RunID || frame["aborted"] != true {
		t.Fatalf("bad abort frame: %#v", frame)
	}
	status, ok := svc.RunStatus(start.RunID)
	if !ok || status.Status != AgentRunStatusAborted || !status.AbortRequested {
		t.Fatalf("bad aborted status ok=%v status=%#v", ok, status)
	}
}

func TestAgentRuntimeRegistryCleanup(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	start, err := svc.StartRun(context.Background(), AgentRunRequest{Message: "cleanup"})
	if err != nil {
		t.Fatal(err)
	}
	svc.AbortRun(start.RunID)
	snapshot, ok := svc.FinishRun(start.RunID, AgentRunStatusCompleted, nil)
	if !ok {
		t.Fatal("finish did not find active run")
	}
	if snapshot.Status != AgentRunStatusAborted {
		t.Fatalf("aborted run should remain aborted, got %#v", snapshot)
	}
	if snapshot.RegistryPresent {
		t.Fatalf("finished snapshot still says registry present: %#v", snapshot)
	}
	if svc.ActiveRunCount() != 0 {
		t.Fatalf("registry cleanup failed; active=%d", svc.ActiveRunCount())
	}
	archived, ok := svc.RunStatus(start.RunID)
	if !ok || archived.RegistryPresent || archived.Status != AgentRunStatusAborted {
		t.Fatalf("bad archived status ok=%v status=%#v", ok, archived)
	}
	task, ok := svc.Task(start.TaskID)
	if !ok || task.Status != AgentTaskStatusAborted || task.FinishedAt == nil {
		t.Fatalf("bad task after cleanup ok=%v task=%#v", ok, task)
	}
}

func TestAgentRuntimeTaskTree(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	parent, err := svc.StartRun(context.Background(), AgentRunRequest{Message: "parent"})
	if err != nil {
		t.Fatal(err)
	}
	child, err := svc.StartRun(context.Background(), AgentRunRequest{Message: "child", ParentTaskID: parent.TaskID})
	if err != nil {
		t.Fatal(err)
	}
	tree := svc.TaskTree()
	if len(tree) != 1 {
		t.Fatalf("expected one root, got %#v", tree)
	}
	if tree[0].Task.ID != parent.TaskID {
		t.Fatalf("wrong root task: %#v", tree[0])
	}
	if len(tree[0].Children) != 1 || tree[0].Children[0].Task.ID != child.TaskID {
		t.Fatalf("wrong child tree: %#v", tree[0].Children)
	}
	parentTask, ok := svc.Task(parent.TaskID)
	if !ok || len(parentTask.ChildrenIDs) != 1 || parentTask.ChildrenIDs[0] != child.TaskID {
		t.Fatalf("parent child index not maintained ok=%v task=%#v", ok, parentTask)
	}
}

func TestAgentRuntimeToolDecisionDoesNotExecuteTools(t *testing.T) {
	svc := newDeterministicAgentRuntime()
	start, err := svc.StartRun(context.Background(), AgentRunRequest{Message: "tool"})
	if err != nil {
		t.Fatal(err)
	}
	writeDecision := svc.ToolDecision(start.RunID, "write_file", map[string]any{"path": "x"})
	if writeDecision.Allowed || !writeDecision.RequiresConfirmation || writeDecision.Error != "permission_required" {
		t.Fatalf("side-effecting tool was not permission gated: %#v", writeDecision)
	}
	readDecision := svc.ToolDecision(start.RunID, "read_file", nil)
	if readDecision.Allowed || readDecision.RequiresConfirmation || readDecision.Error != "tool_unavailable" {
		t.Fatalf("read tool should be unavailable, not executed: %#v", readDecision)
	}
	frame := svc.ToolDecisionFrame(start.RunID, "execute_command", map[string]any{"command": "echo hi"})
	if frame["type"] != AgentFramePermissionRequired || frame["risk_level"] != "high" {
		t.Fatalf("bad permission frame: %#v", frame)
	}
}

func TestBuildAgentSSEFramesAreJSONDataFrames(t *testing.T) {
	frames := BuildAgentSSEFrames(
		AgentSSEPayload{"type": AgentFrameRunStarted, "run_id": "run-a"},
		AgentSSEPayload{"type": AgentFrameDone, "run_id": "run-a", "done": true},
	)
	parts := strings.Split(strings.TrimSpace(frames), "\n\n")
	if len(parts) != 2 {
		t.Fatalf("expected 2 frames, got %d: %q", len(parts), frames)
	}
	for _, part := range parts {
		if !strings.HasPrefix(part, "data: ") {
			t.Fatalf("bad sse prefix: %q", part)
		}
		var payload map[string]any
		if err := json.Unmarshal([]byte(strings.TrimPrefix(part, "data: ")), &payload); err != nil {
			t.Fatalf("frame is not json: %v: %q", err, part)
		}
	}
}
