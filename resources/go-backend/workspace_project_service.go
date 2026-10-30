package main

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"mime"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

var (
	errWorkspacePathEmpty     = errors.New("workspace path is empty")
	errWorkspacePathTraversal = errors.New("workspace path traversal denied")
	errWorkspaceNotTrusted    = errors.New("workspace path is not trusted")
)

type WorkspaceProjectService struct {
	runtimeDir    string
	workspaceRoot string
	stateDir      string
	allowlistPath string
	snapshotDir   string
	mu            sync.Mutex
}

type WorkspacePathDecision struct {
	Allowed     bool   `json:"allowed"`
	Action      string `json:"action"`
	Root        string `json:"root"`
	Target      string `json:"target"`
	TrustedRoot string `json:"trusted_root,omitempty"`
	Reason      string `json:"reason,omitempty"`
}

type TrustedProject struct {
	ID        string `json:"id"`
	Root      string `json:"root"`
	Name      string `json:"name"`
	Source    string `json:"source"`
	Trusted   bool   `json:"trusted"`
	CreatedAt string `json:"created_at"`
	UpdatedAt string `json:"updated_at"`
}

type trustedProjectStore struct {
	Version  int              `json:"version"`
	Projects []TrustedProject `json:"projects"`
}

type ProjectPreview struct {
	Success  bool            `json:"success"`
	Mode     string          `json:"mode"`
	Root     string          `json:"root"`
	Name     string          `json:"name"`
	Exists   bool            `json:"exists"`
	IsDir    bool            `json:"is_dir"`
	Trusted  bool            `json:"trusted"`
	Children []FileTreeEntry `json:"children,omitempty"`
	Message  string          `json:"message"`
}

type FileReadResult struct {
	Path       string `json:"path"`
	Content    string `json:"content"`
	Size       int64  `json:"size"`
	ModifiedAt string `json:"modified_at,omitempty"`
}

type FileWriteResult struct {
	Path       string `json:"path"`
	Bytes      int    `json:"bytes"`
	SnapshotID string `json:"snapshot_id,omitempty"`
	CreatedDir bool   `json:"created_dir,omitempty"`
}

type FileSnapshot struct {
	ID            string `json:"id"`
	Root          string `json:"root"`
	Path          string `json:"path"`
	Target        string `json:"target"`
	Existed       bool   `json:"existed"`
	Mode          uint32 `json:"mode,omitempty"`
	ContentB64    string `json:"content_base64,omitempty"`
	CreatedAt     string `json:"created_at"`
	ContentSHA256 string `json:"content_sha256,omitempty"`
}

type FileTreeEntry struct {
	Name       string          `json:"name"`
	Path       string          `json:"path"`
	AbsPath    string          `json:"abs_path,omitempty"`
	IsDir      bool            `json:"is_dir"`
	Size       int64           `json:"size,omitempty"`
	Mode       string          `json:"mode,omitempty"`
	ModifiedAt string          `json:"modified_at,omitempty"`
	Symlink    bool            `json:"symlink,omitempty"`
	Target     string          `json:"target,omitempty"`
	Denied     bool            `json:"denied,omitempty"`
	Reason     string          `json:"reason,omitempty"`
	Children   []FileTreeEntry `json:"children,omitempty"`
}

type UploadMetadata struct {
	OriginalName string `json:"original_name"`
	RelativePath string `json:"relative_path"`
	Size         int64  `json:"size"`
	ContentType  string `json:"content_type,omitempty"`
	SHA256       string `json:"sha256,omitempty"`
}

type PreparedUpload struct {
	OriginalName string `json:"original_name"`
	RelativePath string `json:"relative_path"`
	Target       string `json:"target"`
	Size         int64  `json:"size"`
	ContentType  string `json:"content_type,omitempty"`
	SHA256       string `json:"sha256,omitempty"`
}

func NewWorkspaceProjectService(runtimeDir, workspaceRoot string) (*WorkspaceProjectService, error) {
	if runtimeDir == "" {
		wd, err := os.Getwd()
		if err != nil {
			return nil, err
		}
		runtimeDir = filepath.Join(wd, "runtime")
	}
	runtimeDir, err := workspaceRealPath(runtimeDir, true)
	if err != nil {
		return nil, err
	}
	if workspaceRoot == "" {
		workspaceRoot = filepath.Join(runtimeDir, "workspaces")
	}
	workspaceRoot, err = workspaceRealPath(workspaceRoot, true)
	if err != nil {
		return nil, err
	}
	stateDir := filepath.Join(runtimeDir, "workspace_project")
	if err := os.MkdirAll(stateDir, 0o700); err != nil {
		return nil, err
	}
	snapshotDir := filepath.Join(stateDir, "snapshots")
	if err := os.MkdirAll(snapshotDir, 0o700); err != nil {
		return nil, err
	}
	return &WorkspaceProjectService{
		runtimeDir:    runtimeDir,
		workspaceRoot: workspaceRoot,
		stateDir:      stateDir,
		allowlistPath: filepath.Join(stateDir, "trusted_projects.json"),
		snapshotDir:   snapshotDir,
	}, nil
}

func (svc *WorkspaceProjectService) WorkspaceRoot() string {
	if svc == nil {
		return ""
	}
	return svc.workspaceRoot
}

func (svc *WorkspaceProjectService) NormalizePath(path string, mustExist bool) (string, error) {
	return workspaceRealPath(path, mustExist)
}

func (svc *WorkspaceProjectService) SafeJoin(root, rel string) (string, error) {
	rootReal, err := workspaceRealPath(root, true)
	if err != nil {
		return "", err
	}
	if rel == "" || rel == "." {
		return rootReal, nil
	}
	if workspaceLooksTraversal(rel) {
		return "", errWorkspacePathTraversal
	}
	candidate := filepath.Clean(filepath.FromSlash(rel))
	if filepath.IsAbs(candidate) {
		candidate, err = workspaceRealPath(candidate, false)
	} else {
		candidate, err = workspaceRealPath(filepath.Join(rootReal, candidate), false)
	}
	if err != nil {
		return "", err
	}
	if !workspacePathInside(rootReal, candidate) {
		return "", fmt.Errorf("%w: %s is outside %s", errWorkspacePathTraversal, candidate, rootReal)
	}
	return candidate, nil
}

func (svc *WorkspaceProjectService) AuthorizePath(action, root, rel string, write bool) (WorkspacePathDecision, error) {
	if svc == nil {
		return WorkspacePathDecision{Allowed: false, Action: action, Reason: "workspace service is nil"}, errors.New("workspace service is nil")
	}
	rootReal, err := svc.resolveRoot(root)
	if err != nil {
		return WorkspacePathDecision{Allowed: false, Action: action, Reason: err.Error()}, err
	}
	target, err := svc.SafeJoin(rootReal, rel)
	if err != nil {
		return WorkspacePathDecision{Allowed: false, Action: action, Root: rootReal, Reason: err.Error()}, err
	}
	trustedRoot, err := svc.authorizedBaseFor(rootReal, target)
	if err != nil {
		return WorkspacePathDecision{Allowed: false, Action: action, Root: rootReal, Target: target, Reason: err.Error()}, err
	}
	return WorkspacePathDecision{
		Allowed:     true,
		Action:      action,
		Root:        rootReal,
		Target:      target,
		TrustedRoot: trustedRoot,
	}, nil
}

func (svc *WorkspaceProjectService) PreviewProject(path string, maxChildren int) (ProjectPreview, error) {
	root, err := workspaceRealPath(path, true)
	if err != nil {
		return ProjectPreview{Success: false, Mode: "preview", Message: err.Error()}, err
	}
	info, err := os.Stat(root)
	if err != nil {
		return ProjectPreview{Success: false, Mode: "preview", Root: root, Message: err.Error()}, err
	}
	preview := ProjectPreview{
		Success: true,
		Mode:    "preview",
		Root:    root,
		Name:    filepath.Base(root),
		Exists:  true,
		IsDir:   info.IsDir(),
		Trusted: svc.IsTrustedProject(root),
		Message: "preview only; call TrustProject after explicit user confirmation",
	}
	if info.IsDir() && maxChildren != 0 {
		children, err := svc.previewChildren(root, maxChildren)
		if err != nil {
			return preview, err
		}
		preview.Children = children
	}
	return preview, nil
}

func (svc *WorkspaceProjectService) TrustProject(path, source string) (TrustedProject, error) {
	root, err := workspaceRealPath(path, true)
	if err != nil {
		return TrustedProject{}, err
	}
	info, err := os.Stat(root)
	if err != nil {
		return TrustedProject{}, err
	}
	if !info.IsDir() {
		return TrustedProject{}, fmt.Errorf("%s is not a directory", root)
	}
	if source == "" {
		source = "user_confirmed"
	}
	now := time.Now().UTC().Format(time.RFC3339)
	project := TrustedProject{
		ID:        workspaceStableID(root),
		Root:      root,
		Name:      filepath.Base(root),
		Source:    source,
		Trusted:   true,
		CreatedAt: now,
		UpdatedAt: now,
	}
	svc.mu.Lock()
	defer svc.mu.Unlock()
	store, err := svc.loadTrustedStoreLocked()
	if err != nil {
		return TrustedProject{}, err
	}
	replaced := false
	for i := range store.Projects {
		if workspaceSamePath(store.Projects[i].Root, root) {
			project.CreatedAt = store.Projects[i].CreatedAt
			store.Projects[i] = project
			replaced = true
			break
		}
	}
	if !replaced {
		store.Projects = append(store.Projects, project)
	}
	if err := svc.saveTrustedStoreLocked(store); err != nil {
		return TrustedProject{}, err
	}
	return project, nil
}

func (svc *WorkspaceProjectService) UntrustProject(path string) error {
	root, err := workspaceRealPath(path, false)
	if err != nil {
		return err
	}
	svc.mu.Lock()
	defer svc.mu.Unlock()
	store, err := svc.loadTrustedStoreLocked()
	if err != nil {
		return err
	}
	next := store.Projects[:0]
	for _, project := range store.Projects {
		if !workspaceSamePath(project.Root, root) {
			next = append(next, project)
		}
	}
	store.Projects = next
	return svc.saveTrustedStoreLocked(store)
}

func (svc *WorkspaceProjectService) TrustedProjects() ([]TrustedProject, error) {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	store, err := svc.loadTrustedStoreLocked()
	if err != nil {
		return nil, err
	}
	projects := append([]TrustedProject(nil), store.Projects...)
	sort.Slice(projects, func(i, j int) bool {
		return strings.ToLower(projects[i].Root) < strings.ToLower(projects[j].Root)
	})
	return projects, nil
}

func (svc *WorkspaceProjectService) IsTrustedProject(path string) bool {
	root, err := workspaceRealPath(path, false)
	if err != nil {
		return false
	}
	base, err := svc.authorizedBaseFor(root, root)
	return err == nil && base != ""
}

func (svc *WorkspaceProjectService) ReadFile(root, rel string) (FileReadResult, error) {
	decision, err := svc.AuthorizePath("read_file", root, rel, false)
	if err != nil {
		return FileReadResult{}, err
	}
	info, err := os.Stat(decision.Target)
	if err != nil {
		return FileReadResult{}, err
	}
	if info.IsDir() {
		return FileReadResult{}, fmt.Errorf("%s is a directory", decision.Target)
	}
	b, err := os.ReadFile(decision.Target)
	if err != nil {
		return FileReadResult{}, err
	}
	return FileReadResult{
		Path:       filepath.ToSlash(workspaceRelOrBase(decision.Root, decision.Target)),
		Content:    string(b),
		Size:       info.Size(),
		ModifiedAt: info.ModTime().UTC().Format(time.RFC3339),
	}, nil
}

func (svc *WorkspaceProjectService) WriteFile(root, rel, content string, isDir bool) (FileWriteResult, error) {
	decision, err := svc.AuthorizePath("write_file", root, rel, true)
	if err != nil {
		return FileWriteResult{}, err
	}
	snapshotID, err := svc.createSnapshot(decision.Root, rel, decision.Target)
	if err != nil {
		return FileWriteResult{}, err
	}
	if isDir {
		if err := os.MkdirAll(decision.Target, 0o755); err != nil {
			return FileWriteResult{}, err
		}
		return FileWriteResult{Path: filepath.ToSlash(workspaceRelOrBase(decision.Root, decision.Target)), SnapshotID: snapshotID, CreatedDir: true}, nil
	}
	if err := os.MkdirAll(filepath.Dir(decision.Target), 0o755); err != nil {
		return FileWriteResult{}, err
	}
	if err := os.WriteFile(decision.Target, []byte(content), 0o644); err != nil {
		return FileWriteResult{}, err
	}
	return FileWriteResult{Path: filepath.ToSlash(workspaceRelOrBase(decision.Root, decision.Target)), Bytes: len(content), SnapshotID: snapshotID}, nil
}

func (svc *WorkspaceProjectService) RevertSnapshot(snapshotID string) (FileWriteResult, error) {
	snapshot, err := svc.loadSnapshot(snapshotID)
	if err != nil {
		return FileWriteResult{}, err
	}
	decision, err := svc.AuthorizePath("revert_file", snapshot.Root, snapshot.Path, true)
	if err != nil {
		return FileWriteResult{}, err
	}
	if !workspaceSamePath(decision.Target, snapshot.Target) {
		return FileWriteResult{}, fmt.Errorf("snapshot target mismatch")
	}
	if snapshot.Existed {
		content, err := base64.StdEncoding.DecodeString(snapshot.ContentB64)
		if err != nil {
			return FileWriteResult{}, err
		}
		if err := os.MkdirAll(filepath.Dir(decision.Target), 0o755); err != nil {
			return FileWriteResult{}, err
		}
		mode := fs.FileMode(snapshot.Mode)
		if mode == 0 {
			mode = 0o644
		}
		if err := os.WriteFile(decision.Target, content, mode); err != nil {
			return FileWriteResult{}, err
		}
		return FileWriteResult{Path: filepath.ToSlash(snapshot.Path), Bytes: len(content), SnapshotID: snapshot.ID}, nil
	}
	if err := os.Remove(decision.Target); err != nil && !os.IsNotExist(err) {
		return FileWriteResult{}, err
	}
	return FileWriteResult{Path: filepath.ToSlash(snapshot.Path), SnapshotID: snapshot.ID}, nil
}

func (svc *WorkspaceProjectService) FileTree(root, rel string, depth int) ([]FileTreeEntry, error) {
	decision, err := svc.AuthorizePath("file_tree", root, rel, false)
	if err != nil {
		return nil, err
	}
	if depth < 0 {
		depth = 0
	}
	return svc.fileTreeEntries(decision.Root, decision.Target, depth)
}

func (svc *WorkspaceProjectService) PrepareUploadEntries(root string, metas []UploadMetadata) ([]PreparedUpload, error) {
	if len(metas) == 0 {
		return nil, nil
	}
	prepared := make([]PreparedUpload, 0, len(metas))
	seen := map[string]bool{}
	for _, meta := range metas {
		rel := meta.RelativePath
		if rel == "" {
			rel = meta.OriginalName
		}
		rel = workspaceSanitizeUploadPath(rel)
		if rel == "" {
			return nil, fmt.Errorf("upload path is empty")
		}
		decision, err := svc.AuthorizePath("upload_file", root, rel, true)
		if err != nil {
			return nil, err
		}
		key := workspaceCanonicalKey(decision.Target)
		if seen[key] {
			return nil, fmt.Errorf("duplicate upload target: %s", rel)
		}
		seen[key] = true
		ct := meta.ContentType
		if ct == "" {
			ct = mime.TypeByExtension(filepath.Ext(rel))
		}
		prepared = append(prepared, PreparedUpload{
			OriginalName: meta.OriginalName,
			RelativePath: filepath.ToSlash(workspaceRelOrBase(decision.Root, decision.Target)),
			Target:       decision.Target,
			Size:         meta.Size,
			ContentType:  ct,
			SHA256:       meta.SHA256,
		})
	}
	return prepared, nil
}

func (svc *WorkspaceProjectService) BuildUploadMetadata(originalName, relativePath string, size int64, content []byte) UploadMetadata {
	if relativePath == "" {
		relativePath = originalName
	}
	meta := UploadMetadata{
		OriginalName: originalName,
		RelativePath: workspaceSanitizeUploadPath(relativePath),
		Size:         size,
		ContentType:  mime.TypeByExtension(filepath.Ext(relativePath)),
	}
	if content != nil {
		sum := sha256.Sum256(content)
		meta.SHA256 = hex.EncodeToString(sum[:])
		meta.Size = int64(len(content))
	}
	return meta
}

func (svc *WorkspaceProjectService) resolveRoot(root string) (string, error) {
	if root == "" {
		return svc.workspaceRoot, nil
	}
	return workspaceRealPath(root, true)
}

func (svc *WorkspaceProjectService) authorizedBaseFor(root, target string) (string, error) {
	workspaceRoot, err := workspaceRealPath(svc.workspaceRoot, true)
	if err != nil {
		return "", err
	}
	if workspacePathInside(workspaceRoot, root) && workspacePathInside(workspaceRoot, target) {
		return workspaceRoot, nil
	}
	projects, err := svc.TrustedProjects()
	if err != nil {
		return "", err
	}
	for _, project := range projects {
		if !project.Trusted {
			continue
		}
		projectRoot, err := workspaceRealPath(project.Root, true)
		if err != nil {
			continue
		}
		if workspacePathInside(projectRoot, root) && workspacePathInside(projectRoot, target) {
			return projectRoot, nil
		}
	}
	return "", errWorkspaceNotTrusted
}

func (svc *WorkspaceProjectService) loadTrustedStoreLocked() (trustedProjectStore, error) {
	store := trustedProjectStore{Version: 1}
	b, err := os.ReadFile(svc.allowlistPath)
	if os.IsNotExist(err) {
		return store, nil
	}
	if err != nil {
		return store, err
	}
	if len(strings.TrimSpace(string(b))) == 0 {
		return store, nil
	}
	if err := json.Unmarshal(b, &store); err != nil {
		return store, err
	}
	if store.Version == 0 {
		store.Version = 1
	}
	filtered := store.Projects[:0]
	for _, project := range store.Projects {
		root, err := workspaceRealPath(project.Root, true)
		if err != nil {
			continue
		}
		project.Root = root
		project.ID = workspaceStableID(root)
		filtered = append(filtered, project)
	}
	store.Projects = filtered
	return store, nil
}

func (svc *WorkspaceProjectService) saveTrustedStoreLocked(store trustedProjectStore) error {
	if err := os.MkdirAll(filepath.Dir(svc.allowlistPath), 0o700); err != nil {
		return err
	}
	b, err := json.MarshalIndent(store, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(svc.allowlistPath, b, 0o600)
}

func (svc *WorkspaceProjectService) previewChildren(root string, maxChildren int) ([]FileTreeEntry, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, err
	}
	if maxChildren > 0 && len(entries) > maxChildren {
		entries = entries[:maxChildren]
	}
	out := make([]FileTreeEntry, 0, len(entries))
	for _, entry := range entries {
		path := filepath.Join(root, entry.Name())
		info, err := entry.Info()
		if err != nil {
			out = append(out, FileTreeEntry{Name: entry.Name(), Path: entry.Name(), Denied: true, Reason: err.Error()})
			continue
		}
		out = append(out, FileTreeEntry{
			Name:       entry.Name(),
			Path:       entry.Name(),
			AbsPath:    path,
			IsDir:      info.IsDir(),
			Size:       info.Size(),
			Mode:       info.Mode().String(),
			ModifiedAt: info.ModTime().UTC().Format(time.RFC3339),
		})
	}
	sortFileTreeEntries(out)
	return out, nil
}

func (svc *WorkspaceProjectService) createSnapshot(root, rel, target string) (string, error) {
	if err := os.MkdirAll(svc.snapshotDir, 0o700); err != nil {
		return "", err
	}
	now := time.Now().UTC()
	snapshot := FileSnapshot{
		ID:        workspaceStableID(target + "|" + now.Format(time.RFC3339Nano)),
		Root:      root,
		Path:      filepath.ToSlash(workspaceRelOrBase(root, target)),
		Target:    target,
		CreatedAt: now.Format(time.RFC3339),
	}
	info, err := os.Stat(target)
	if err == nil {
		if info.IsDir() {
			snapshot.Existed = true
			snapshot.Mode = uint32(info.Mode())
		} else {
			b, readErr := os.ReadFile(target)
			if readErr != nil {
				return "", readErr
			}
			sum := sha256.Sum256(b)
			snapshot.Existed = true
			snapshot.Mode = uint32(info.Mode())
			snapshot.ContentB64 = base64.StdEncoding.EncodeToString(b)
			snapshot.ContentSHA256 = hex.EncodeToString(sum[:])
		}
	} else if !os.IsNotExist(err) {
		return "", err
	}
	b, err := json.MarshalIndent(snapshot, "", "  ")
	if err != nil {
		return "", err
	}
	if err := os.WriteFile(svc.snapshotPath(snapshot.ID), b, 0o600); err != nil {
		return "", err
	}
	return snapshot.ID, nil
}

func (svc *WorkspaceProjectService) loadSnapshot(id string) (FileSnapshot, error) {
	if strings.TrimSpace(id) == "" {
		return FileSnapshot{}, fmt.Errorf("snapshot id is empty")
	}
	b, err := os.ReadFile(svc.snapshotPath(id))
	if err != nil {
		return FileSnapshot{}, err
	}
	var snapshot FileSnapshot
	if err := json.Unmarshal(b, &snapshot); err != nil {
		return FileSnapshot{}, err
	}
	if snapshot.ID != id {
		return FileSnapshot{}, fmt.Errorf("snapshot id mismatch")
	}
	return snapshot, nil
}

func (svc *WorkspaceProjectService) snapshotPath(id string) string {
	return filepath.Join(svc.snapshotDir, workspaceSafeFilename(id)+".json")
}

func (svc *WorkspaceProjectService) fileTreeEntries(root, target string, depth int) ([]FileTreeEntry, error) {
	entries, err := os.ReadDir(target)
	if err != nil {
		return nil, err
	}
	out := make([]FileTreeEntry, 0, len(entries))
	for _, dirEntry := range entries {
		path := filepath.Join(target, dirEntry.Name())
		entry := svc.fileTreeEntry(root, path, depth)
		out = append(out, entry)
	}
	sortFileTreeEntries(out)
	return out, nil
}

func (svc *WorkspaceProjectService) fileTreeEntry(root, path string, depth int) FileTreeEntry {
	rel := filepath.ToSlash(workspaceRelOrBase(root, path))
	lstat, err := os.Lstat(path)
	if err != nil {
		return FileTreeEntry{Name: filepath.Base(path), Path: rel, AbsPath: path, Denied: true, Reason: err.Error()}
	}
	entry := FileTreeEntry{
		Name:       filepath.Base(path),
		Path:       rel,
		AbsPath:    path,
		Size:       lstat.Size(),
		Mode:       lstat.Mode().String(),
		ModifiedAt: lstat.ModTime().UTC().Format(time.RFC3339),
	}
	if lstat.Mode()&os.ModeSymlink != 0 {
		entry.Symlink = true
		target, err := filepath.EvalSymlinks(path)
		if err != nil {
			entry.Denied = true
			entry.Reason = err.Error()
			return entry
		}
		entry.Target = target
		if !workspacePathInside(root, target) {
			entry.Denied = true
			entry.Reason = "symlink target outside workspace"
			return entry
		}
		stat, err := os.Stat(path)
		if err != nil {
			entry.Denied = true
			entry.Reason = err.Error()
			return entry
		}
		entry.IsDir = stat.IsDir()
		entry.Size = stat.Size()
	} else {
		entry.IsDir = lstat.IsDir()
	}
	if entry.IsDir && depth > 0 && !entry.Denied {
		children, err := svc.fileTreeEntries(root, path, depth-1)
		if err != nil {
			entry.Denied = true
			entry.Reason = err.Error()
		} else {
			entry.Children = children
		}
	}
	return entry
}

func workspaceRealPath(path string, mustExist bool) (string, error) {
	if strings.TrimSpace(path) == "" {
		return "", errWorkspacePathEmpty
	}
	path = filepath.Clean(filepath.FromSlash(path))
	abs, err := filepath.Abs(path)
	if err != nil {
		return "", err
	}
	if mustExist {
		real, err := filepath.EvalSymlinks(abs)
		if err != nil {
			return "", err
		}
		return filepath.Clean(real), nil
	}
	return workspaceResolveExistingPrefix(abs)
}

func workspaceResolveExistingPrefix(abs string) (string, error) {
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
			return filepath.Clean(realBase), nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("no existing path component for %s", abs)
		}
		missing = append(missing, filepath.Base(current))
		current = parent
	}
}

func workspacePathInside(root, target string) bool {
	if root == "" || target == "" {
		return false
	}
	root = filepath.Clean(root)
	target = filepath.Clean(target)
	if runtime.GOOS == "windows" {
		root = strings.ToLower(root)
		target = strings.ToLower(target)
	}
	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false
	}
	return rel == "." || (rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator)) && !filepath.IsAbs(rel))
}

func workspaceSamePath(a, b string) bool {
	a = filepath.Clean(a)
	b = filepath.Clean(b)
	if runtime.GOOS == "windows" {
		return strings.EqualFold(a, b)
	}
	return a == b
}

func workspaceLooksTraversal(rel string) bool {
	if strings.TrimSpace(rel) == "" {
		return false
	}
	cleaned := filepath.Clean(filepath.FromSlash(rel))
	if cleaned == ".." || strings.HasPrefix(cleaned, ".."+string(os.PathSeparator)) {
		return true
	}
	parts := strings.FieldsFunc(rel, func(r rune) bool {
		return r == '/' || r == '\\'
	})
	for _, part := range parts {
		if part == ".." {
			return true
		}
	}
	return false
}

func workspaceRelOrBase(root, target string) string {
	rel, err := filepath.Rel(root, target)
	if err != nil || rel == "." || strings.HasPrefix(rel, "..") {
		return filepath.Base(target)
	}
	return rel
}

func workspaceStableID(value string) string {
	sum := sha256.Sum256([]byte(filepath.Clean(value)))
	return hex.EncodeToString(sum[:])[:24]
}

func workspaceSafeFilename(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "empty"
	}
	var b strings.Builder
	for _, r := range value {
		switch {
		case r >= 'a' && r <= 'z':
			b.WriteRune(r)
		case r >= 'A' && r <= 'Z':
			b.WriteRune(r)
		case r >= '0' && r <= '9':
			b.WriteRune(r)
		case r == '-' || r == '_':
			b.WriteRune(r)
		default:
			b.WriteByte('_')
		}
	}
	return b.String()
}

func workspaceCanonicalKey(path string) string {
	path = filepath.Clean(path)
	if runtime.GOOS == "windows" {
		path = strings.ToLower(path)
	}
	return path
}

func workspaceSanitizeUploadPath(path string) string {
	path = strings.TrimSpace(path)
	if path == "" {
		return ""
	}
	path = strings.ReplaceAll(path, "\\", "/")
	cleaned := filepath.ToSlash(filepath.Clean(filepath.FromSlash(path)))
	for strings.HasPrefix(cleaned, "../") || cleaned == ".." {
		cleaned = strings.TrimPrefix(cleaned, "../")
		if cleaned == ".." {
			cleaned = ""
			break
		}
		cleaned = filepath.ToSlash(filepath.Clean(filepath.FromSlash(cleaned)))
	}
	if filepath.IsAbs(filepath.FromSlash(cleaned)) {
		cleaned = filepath.Base(filepath.FromSlash(cleaned))
	}
	cleaned = strings.TrimPrefix(cleaned, "/")
	if cleaned == "." {
		return ""
	}
	return cleaned
}

func sortFileTreeEntries(entries []FileTreeEntry) {
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Denied != entries[j].Denied {
			return !entries[i].Denied
		}
		if entries[i].IsDir != entries[j].IsDir {
			return entries[i].IsDir
		}
		return strings.ToLower(entries[i].Name) < strings.ToLower(entries[j].Name)
	})
}
