package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"errors"
	"os/user"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func (s *Server) vaultPath() string {
	root := s.runtimeDir
	if root == "" {
		root = s.cfg.RuntimeDir
	}
	return filepath.Join(root, "device_vault.enc")
}

func (s *Server) saveVault(v DeviceVault) error {
	return s.saveDeviceConfig(deviceConfig{DeviceID: s.deviceID(), Provider: v.Provider, APIURL: v.APIURL, APIKey: v.APIKey, Model: v.Model, Updated: time.Now().UTC().Format(time.RFC3339)})
}

func (s *Server) loadVault() (DeviceVault, error) {
	cfg, err := s.loadDeviceConfig()
	if err != nil {
		return DeviceVault{}, err
	}
	return DeviceVault{Provider: cfg.Provider, APIURL: cfg.APIURL, APIKey: cfg.APIKey, Model: cfg.Model}, nil
}

func encryptLocal(runtimeDir string, plain []byte) ([]byte, error) {
	block, err := aes.NewCipher(localKey(runtimeDir))
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return nil, err
	}
	raw := gcm.Seal(nonce, nonce, plain, nil)
	return []byte(base64.StdEncoding.EncodeToString(raw)), nil
}

func decryptLocal(runtimeDir string, encoded []byte) ([]byte, error) {
	raw, err := base64.StdEncoding.DecodeString(strings.TrimSpace(string(encoded)))
	if err != nil {
		return nil, err
	}
	block, err := aes.NewCipher(localKey(runtimeDir))
	if err != nil {
		return nil, err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, err
	}
	if len(raw) < gcm.NonceSize() {
		return nil, errors.New("vault too short")
	}
	return gcm.Open(nil, raw[:gcm.NonceSize()], raw[gcm.NonceSize():], nil)
}

func localKey(runtimeDir string) []byte {
	current, _ := user.Current()
	username := ""
	if current != nil {
		username = current.Username
	}
	sum := sha256.Sum256([]byte(filepath.Clean(runtimeDir) + "|" + hostName() + "|" + runtime.GOOS + "|" + username))
	return sum[:]
}
