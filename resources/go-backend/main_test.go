package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWorkspaceAuthorizeBlocksPrefixTraversal(t *testing.T) {
	dir := t.TempDir()
	s := &Server{runtimeDir: dir, workspaceRoot: filepath.Join(dir, "workspaces")}
	root := s.workspaceFor("device")
	outside := filepath.Join(filepath.Dir(root), filepath.Base(root)+"2", "x.txt")
	if _, err := s.authorize("device", outside, false); err == nil {
		t.Fatalf("expected outside prefix path to be denied")
	}
}

func TestWorkspaceAuthorizeBlocksDotDot(t *testing.T) {
	dir := t.TempDir()
	s := &Server{runtimeDir: dir, workspaceRoot: filepath.Join(dir, "workspaces")}
	if _, err := s.authorize("device", ".."+string(os.PathSeparator)+"outside.txt", false); err == nil {
		t.Fatalf("expected dotdot path to be denied")
	}
}

func TestVaultMasksAndEncryptsKey(t *testing.T) {
	dir := t.TempDir()
	s := &Server{runtimeDir: dir}
	v := DeviceVault{Provider: "kimi", APIKey: "sk-test-secret-123456", APIURL: "https://api.moonshot.ai/v1", Model: "kimi-k2.6"}
	if err := s.saveVault(v); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(s.vaultPath())
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(raw), v.APIKey) {
		t.Fatalf("vault leaked plaintext key")
	}
	loaded, err := s.loadVault()
	if err != nil {
		t.Fatal(err)
	}
	if loaded.APIKey != v.APIKey {
		t.Fatalf("loaded key mismatch")
	}
}

func TestDangerousCommandClassification(t *testing.T) {
	if classifyCommand("rm -rf /") != "critical" {
		t.Fatalf("rm -rf should be critical")
	}
	if classifyCommand("python script.py") != "high" {
		t.Fatalf("python script should be high")
	}
	if classifyCommand("dir") != "low" {
		t.Fatalf("dir should be low")
	}
}
