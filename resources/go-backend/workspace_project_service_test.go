package main

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func newWorkspaceProjectServiceForTest(t *testing.T) (*WorkspaceProjectService, string, string) {
	t.Helper()
	runtimeDir := t.TempDir()
	workspaceRoot := filepath.Join(runtimeDir, "workspaces")
	if err := os.MkdirAll(workspaceRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	svc, err := NewWorkspaceProjectService(runtimeDir, workspaceRoot)
	if err != nil {
		t.Fatal(err)
	}
	project := filepath.Join(workspaceRoot, "device")
	if err := os.MkdirAll(project, 0o755); err != nil {
		t.Fatal(err)
	}
	return svc, workspaceRoot, project
}

func TestWorkspaceProjectServiceDesktopModeDoesNotBypassRead(t *testing.T) {
	t.Setenv("KAGUYA_DESKTOP_MODE", "1")
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	outsideRoot := filepath.Join(filepath.Dir(workspaceRoot), "outside")
	if err := os.MkdirAll(outsideRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	outsideFile := filepath.Join(outsideRoot, "secret.txt")
	if err := os.WriteFile(outsideFile, []byte("secret"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.ReadFile(project, outsideFile); err == nil {
		t.Fatal("desktop mode must not allow absolute read outside workspace")
	}
}

func TestWorkspaceProjectServiceDesktopModeDoesNotBypassWrite(t *testing.T) {
	t.Setenv("KAGUYA_ELECTRON", "1")
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	outsideRoot := filepath.Join(filepath.Dir(workspaceRoot), "outside-write")
	if err := os.MkdirAll(outsideRoot, 0o755); err != nil {
		t.Fatal(err)
	}
	outsideFile := filepath.Join(outsideRoot, "owned.txt")
	if _, err := svc.WriteFile(project, outsideFile, "pwned", false); err == nil {
		t.Fatal("electron mode must not allow absolute write outside workspace")
	}
	if _, err := os.Stat(outsideFile); !os.IsNotExist(err) {
		t.Fatalf("outside file should not be created, stat err=%v", err)
	}
}

func TestWorkspaceProjectServiceBlocksStartsWithSiblingByCommonPath(t *testing.T) {
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	sibling := workspaceRoot + "2"
	if err := os.MkdirAll(sibling, 0o755); err != nil {
		t.Fatal(err)
	}
	siblingFile := filepath.Join(sibling, "x.txt")
	if err := os.WriteFile(siblingFile, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.AuthorizePath("read_file", project, siblingFile, false); err == nil {
		t.Fatal("startswith sibling path must be denied")
	}
}

func TestWorkspaceProjectServiceBlocksDotDotTraversal(t *testing.T) {
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	outside := filepath.Join(filepath.Dir(workspaceRoot), "outside-dotdot.txt")
	if err := os.WriteFile(outside, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.ReadFile(project, ".."+string(os.PathSeparator)+".."+string(os.PathSeparator)+"outside-dotdot.txt"); err == nil {
		t.Fatal("dotdot traversal must be denied")
	}
}

func TestWorkspaceProjectServiceBlocksSymlinkEscape(t *testing.T) {
	if runtime.GOOS == "windows" {
		// Windows symlink creation often requires Developer Mode/admin rights; skip only this platform capability.
		t.Skip("windows symlink creation is environment-dependent")
	}
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	outside := filepath.Join(filepath.Dir(workspaceRoot), "outside-symlink")
	if err := os.MkdirAll(outside, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(outside, "secret.txt"), []byte("secret"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(outside, filepath.Join(project, "link-out")); err != nil {
		t.Skipf("symlink unavailable: %v", err)
	}
	if _, err := svc.ReadFile(project, filepath.Join("link-out", "secret.txt")); err == nil {
		t.Fatal("symlink escape read must be denied")
	}
	tree, err := svc.FileTree(project, ".", 1)
	if err != nil {
		t.Fatal(err)
	}
	foundDenied := false
	for _, entry := range tree {
		if entry.Name == "link-out" && entry.Denied && strings.Contains(entry.Reason, "outside") {
			foundDenied = true
		}
	}
	if !foundDenied {
		t.Fatalf("file tree should mark escaping symlink denied: %#v", tree)
	}
}

func TestWorkspaceProjectServiceOpenProjectPreviewDoesNotTrust(t *testing.T) {
	svc, workspaceRoot, project := newWorkspaceProjectServiceForTest(t)
	externalProject := filepath.Join(filepath.Dir(workspaceRoot), "external-project")
	if err := os.MkdirAll(externalProject, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(externalProject, "main.go"), []byte("package main"), 0o644); err != nil {
		t.Fatal(err)
	}
	preview, err := svc.PreviewProject(externalProject, 5)
	if err != nil {
		t.Fatal(err)
	}
	if preview.Trusted {
		t.Fatal("preview must not implicitly trust external project")
	}
	if _, err := svc.ReadFile(externalProject, "main.go"); err == nil {
		t.Fatal("previewed external project must remain unreadable before explicit trust")
	}
	if _, err := svc.ReadFile(project, "missing.txt"); err == nil {
		t.Fatal("workspace read of missing file should still fail normally")
	}
}

func TestWorkspaceProjectServiceTrustedImportAllowsChildrenOnly(t *testing.T) {
	svc, workspaceRoot, _ := newWorkspaceProjectServiceForTest(t)
	externalProject := filepath.Join(filepath.Dir(workspaceRoot), "trusted-project")
	siblingProject := filepath.Join(filepath.Dir(workspaceRoot), "trusted-project-sibling")
	if err := os.MkdirAll(externalProject, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(siblingProject, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(externalProject, "README.md"), []byte("trusted"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(siblingProject, "README.md"), []byte("sibling"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.TrustProject(externalProject, "desktop_picker_confirmed"); err != nil {
		t.Fatal(err)
	}
	read, err := svc.ReadFile(externalProject, "README.md")
	if err != nil {
		t.Fatal(err)
	}
	if read.Content != "trusted" {
		t.Fatalf("unexpected content %q", read.Content)
	}
	if _, err := svc.ReadFile(externalProject, filepath.Join("..", filepath.Base(siblingProject), "README.md")); err == nil {
		t.Fatal("trusted project must not allow sibling traversal")
	}
	reloaded, err := NewWorkspaceProjectService(svc.runtimeDir, svc.workspaceRoot)
	if err != nil {
		t.Fatal(err)
	}
	if !reloaded.IsTrustedProject(externalProject) {
		t.Fatal("trusted project allowlist should persist across service reload")
	}
}

func TestWorkspaceProjectServiceReadWriteAndRevertExistingFile(t *testing.T) {
	svc, _, project := newWorkspaceProjectServiceForTest(t)
	target := filepath.Join(project, "src", "main.txt")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte("old"), 0o644); err != nil {
		t.Fatal(err)
	}
	write, err := svc.WriteFile(project, "src/main.txt", "new", false)
	if err != nil {
		t.Fatal(err)
	}
	if write.SnapshotID == "" {
		t.Fatal("write should create snapshot id")
	}
	read, err := svc.ReadFile(project, "src/main.txt")
	if err != nil {
		t.Fatal(err)
	}
	if read.Content != "new" {
		t.Fatalf("write failed, content=%q", read.Content)
	}
	if _, err := svc.RevertSnapshot(write.SnapshotID); err != nil {
		t.Fatal(err)
	}
	read, err = svc.ReadFile(project, "src/main.txt")
	if err != nil {
		t.Fatal(err)
	}
	if read.Content != "old" {
		t.Fatalf("revert failed, content=%q", read.Content)
	}
}

func TestWorkspaceProjectServiceRevertRemovesNewFile(t *testing.T) {
	svc, _, project := newWorkspaceProjectServiceForTest(t)
	write, err := svc.WriteFile(project, "new/file.txt", "new", false)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(project, "new", "file.txt")); err != nil {
		t.Fatal(err)
	}
	if _, err := svc.RevertSnapshot(write.SnapshotID); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(project, "new", "file.txt")); !os.IsNotExist(err) {
		t.Fatalf("new file should be removed after revert, stat err=%v", err)
	}
}

func TestWorkspaceProjectServiceFileTreeSortsAndReportsMetadata(t *testing.T) {
	svc, _, project := newWorkspaceProjectServiceForTest(t)
	if err := os.MkdirAll(filepath.Join(project, "bdir"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(project, "afile.txt"), []byte("a"), 0o644); err != nil {
		t.Fatal(err)
	}
	tree, err := svc.FileTree(project, ".", 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(tree) != 2 {
		t.Fatalf("expected 2 entries, got %#v", tree)
	}
	if !tree[0].IsDir || tree[0].Name != "bdir" {
		t.Fatalf("directories should sort first: %#v", tree)
	}
	if tree[1].Name != "afile.txt" || tree[1].Size != 1 {
		t.Fatalf("file metadata missing: %#v", tree[1])
	}
}

func TestWorkspaceProjectServicePrepareUploadEntries(t *testing.T) {
	svc, _, project := newWorkspaceProjectServiceForTest(t)
	meta := svc.BuildUploadMetadata("note.txt", "docs/note.txt", 0, []byte("hello"))
	prepared, err := svc.PrepareUploadEntries(project, []UploadMetadata{meta})
	if err != nil {
		t.Fatal(err)
	}
	if len(prepared) != 1 {
		t.Fatalf("expected one prepared upload")
	}
	if prepared[0].RelativePath != "docs/note.txt" {
		t.Fatalf("unexpected relative path %q", prepared[0].RelativePath)
	}
	if prepared[0].SHA256 == "" {
		t.Fatal("upload metadata should include sha256 when content is provided")
	}
}

func TestWorkspaceProjectServicePrepareUploadRejectsTraversalAndDuplicates(t *testing.T) {
	svc, _, project := newWorkspaceProjectServiceForTest(t)
	if _, err := svc.PrepareUploadEntries(project, []UploadMetadata{{OriginalName: "evil.txt", RelativePath: "../evil.txt"}}); err != nil {
		t.Fatalf("upload helper should sanitize leading traversal rather than write outside: %v", err)
	}
	prepared, err := svc.PrepareUploadEntries(project, []UploadMetadata{{OriginalName: "evil.txt", RelativePath: "../evil.txt"}})
	if err != nil {
		t.Fatal(err)
	}
	if prepared[0].RelativePath != "evil.txt" {
		t.Fatalf("traversal path should be sanitized to base file, got %q", prepared[0].RelativePath)
	}
	if _, err := svc.PrepareUploadEntries(project, []UploadMetadata{
		{OriginalName: "a.txt", RelativePath: "same.txt"},
		{OriginalName: "b.txt", RelativePath: "same.txt"},
	}); err == nil {
		t.Fatal("duplicate upload targets must be rejected")
	}
}
