package main

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

func (s *Server) workspaceFor(deviceID string) string {
	root := s.workspaceRoot
	if root == "" {
		root = filepath.Join(s.runtimeDir, "workspaces")
	}
	if deviceID == "" {
		deviceID = "default"
	}
	name := filepath.Base(filepath.Clean(deviceID))
	path := filepath.Join(root, name)
	_ = os.MkdirAll(path, 0o755)
	return path
}

func workspaceAndPath(r *http.Request) (string, string, error) {
	if r.Method == http.MethodGet {
		root := r.URL.Query().Get("workspace")
		if root == "" {
			root = r.URL.Query().Get("workspace_root")
		}
		normalized, err := normalizeRoot(root)
		if err != nil {
			return "", "", err
		}
		return normalized, r.URL.Query().Get("path"), nil
	}
	var payload map[string]any
	if err := readJSON(r, &payload); err != nil {
		return "", "", err
	}
	root, err := workspaceRoot(payload)
	if err != nil {
		return "", "", err
	}
	return root, firstString(payload, "path", "file_path", "filePath"), nil
}

func workspaceRoot(payload map[string]any) (string, error) {
	root := firstString(payload, "workspace", "workspace_root", "workspaceRoot", "root")
	return normalizeRoot(root)
}

func normalizeRoot(root string) (string, error) {
	if root == "" {
		wd, err := os.Getwd()
		if err != nil {
			return "", err
		}
		root = wd
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		return "", err
	}
	real, err := filepath.EvalSymlinks(abs)
	if err != nil {
		return "", err
	}
	return filepath.Clean(real), nil
}

func safeJoin(root, rel string) (string, error) {
	root, err := normalizeRoot(root)
	if err != nil {
		return "", err
	}
	if rel == "" || rel == "." {
		return root, nil
	}
	candidate := filepath.Clean(filepath.FromSlash(rel))
	if filepath.IsAbs(candidate) {
		candidate = filepath.Clean(candidate)
	} else {
		candidate = filepath.Join(root, candidate)
	}
	abs, err := filepath.Abs(candidate)
	if err != nil {
		return "", err
	}
	final, err := realCandidate(abs)
	if err != nil {
		return "", err
	}
	if !commonPath(root, final) {
		return "", fmt.Errorf("%s is outside workspace %s", final, root)
	}
	return final, nil
}

func realCandidate(abs string) (string, error) {
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
			return realBase, nil
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", fmt.Errorf("no existing path component for %s", abs)
		}
		missing = append(missing, filepath.Base(current))
		current = parent
	}
}

func commonPath(root, target string) bool {
	root = filepath.Clean(strings.ToLower(root))
	target = filepath.Clean(strings.ToLower(target))
	if runtime.GOOS == "windows" {
		root = strings.TrimRight(root, `\`)
		return target == root || strings.HasPrefix(target, root+`\`)
	}
	root = strings.TrimRight(root, `/`)
	return target == root || strings.HasPrefix(target, root+`/`)
}
