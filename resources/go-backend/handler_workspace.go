package main

import (
    "net/http"
    "io"
    "mime/multipart"
    "os"
    "path/filepath"
    "sort"
    "strings"
)

func (s *Server) browsableDirs(w http.ResponseWriter, r *http.Request) {
	root := s.workspaceFor(s.deviceID())
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"dirs":    []map[string]any{{"path": root, "trusted": true, "scope": "workspace"}},
	})
}

func (s *Server) importEnv(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "env_import_unavailable", "environment import requires explicit Python worker support")
}

func (s *Server) importFiles(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "import_requires_picker", "file import must be performed through the desktop picker and workspace upload API")
}

func (s *Server) openProject(w http.ResponseWriter, r *http.Request) {
	var payload map[string]any
	_ = readJSON(r, &payload)
	root, err := workspaceRoot(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_workspace", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":               true,
		"mode":                  "go",
		"path":                  root,
		"trusted":               false,
		"requires_confirmation": true,
		"message":               "Go backend can preview this project path but does not trust it until the desktop picker confirms import.",
	})
}

func (s *Server) projectOutput(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "output": "", "running": false})
}

func (s *Server) projectStatus(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "running": false, "processes": []any{}})
}

func (s *Server) revertFile(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "history_unavailable", "file history is not configured in the Go backend")
}

func (s *Server) projectCommand(action string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		risk := classifyTool(action)
		if s.permissions.Mode != "allow" && risk != "low" {
			s.audit(action, map[string]any{"allowed": false, "risk_level": risk, "reason": "permission_required"})
			writeJSON(w, http.StatusForbidden, map[string]any{
				"success":               false,
				"allowed":               false,
				"requires_confirmation": true,
				"risk_level":            risk,
				"error":                 "permission_required",
			})
			return
		}
		writeError(w, http.StatusServiceUnavailable, action+"_unavailable", "project execution is delegated to the Python worker")
	}
}

func (s *Server) projectStop(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "stopped": false, "reason": "no_go_managed_process"})
}

func (s *Server) fileTree(w http.ResponseWriter, r *http.Request) {
	root, rel, err := workspaceAndPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	entries, err := os.ReadDir(target)
	if err != nil {
		writeError(w, http.StatusBadRequest, "read_dir_failed", err.Error())
		return
	}
	type entry struct {
		Name  string `json:"name"`
		Path  string `json:"path"`
		IsDir bool   `json:"is_dir"`
		Size  int64  `json:"size,omitempty"`
	}
	items := make([]entry, 0, len(entries))
	for _, e := range entries {
		info, _ := e.Info()
		size := int64(0)
		if info != nil {
			size = info.Size()
		}
		childRel, _ := filepath.Rel(root, filepath.Join(target, e.Name()))
		items = append(items, entry{Name: e.Name(), Path: filepath.ToSlash(childRel), IsDir: e.IsDir(), Size: size})
	}
	sort.Slice(items, func(i, j int) bool {
		if items[i].IsDir != items[j].IsDir {
			return items[i].IsDir
		}
		return strings.ToLower(items[i].Name) < strings.ToLower(items[j].Name)
	})
	writeJSON(w, http.StatusOK, map[string]any{"root": root, "path": filepath.ToSlash(rel), "entries": items})
}

func (s *Server) readFile(w http.ResponseWriter, r *http.Request) {
	root, rel, err := workspaceAndPath(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_path", err.Error())
		return
	}
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	b, err := os.ReadFile(target)
	if err != nil {
		writeError(w, http.StatusBadRequest, "read_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"path": filepath.ToSlash(rel), "content": string(b)})
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
	root, err := workspaceRoot(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	rel := firstString(payload, "path", "file_path", "filePath")
	if rel == "" {
		writeError(w, http.StatusBadRequest, "missing_path", "path/file_path is required")
		return
	}
	target, err := safeJoin(root, rel)
	if err != nil {
		writeError(w, http.StatusForbidden, "outside_workspace", err.Error())
		return
	}
	content := firstString(payload, "content")
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		writeError(w, http.StatusInternalServerError, "mkdir_failed", err.Error())
		return
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		writeError(w, http.StatusInternalServerError, "write_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "path": filepath.ToSlash(rel)})
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
	rootRaw := r.FormValue("workspace")
	if rootRaw == "" {
		rootRaw = r.FormValue("workspace_root")
	}
	root, err := normalizeRoot(rootRaw)
	if err != nil {
		writeError(w, http.StatusBadRequest, "bad_workspace", err.Error())
		return
	}
	count := 0
	pathOverrides := r.MultipartForm.Value["paths"]
	fileIndex := 0
	for _, headers := range r.MultipartForm.File {
		for _, header := range headers {
			rel := header.Filename
			if fileIndex < len(pathOverrides) && pathOverrides[fileIndex] != "" {
				rel = pathOverrides[fileIndex]
			}
			if err := s.saveUploadedFile(root, header, rel); err != nil {
				writeError(w, http.StatusForbidden, "upload_failed", err.Error())
				return
			}
			fileIndex++
			count++
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "uploaded": count})
}

func (s *Server) saveUploadedFile(root string, header *multipart.FileHeader, relativeName string) error {
	src, err := header.Open()
	if err != nil {
		return err
	}
	defer src.Close()
	name := filepath.Clean(filepath.FromSlash(relativeName))
	if filepath.IsAbs(name) {
		name = filepath.Base(name)
	}
	target, err := safeJoin(root, name)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	dst, err := os.OpenFile(target, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer dst.Close()
	_, err = io.Copy(dst, src)
	return err
}
