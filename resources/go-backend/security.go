package main

import (
	"fmt"
	"path/filepath"
	"strings"
)

func dangerousCommand(argv []string) string {
	base := strings.ToLower(filepath.Base(argv[0]))
	base = strings.TrimSuffix(base, ".exe")
	blocked := map[string]bool{
		"rm": true, "del": true, "erase": true, "rmdir": true, "rd": true,
		"remove-item": true, "ri": true, "move-item": true,
		"format": true, "diskpart": true, "shutdown": true, "reboot": true,
		"mkfs": true, "dd": true, "reg": true, "takeown": true, "icacls": true,
	}
	if blocked[base] {
		return "refusing destructive command " + base
	}
	joined := strings.ToLower(strings.Join(argv, " "))
	for _, token := range []string{"&&", "||", ";", "`", "$(", ">", "<", "|"} {
		if strings.Contains(joined, token) {
			return "shell metacharacters are not allowed"
		}
	}
	return ""
}

func classifyCommand(command string) string {
	argv := strings.Fields(command)
	if len(argv) == 0 {
		return "low"
	}
	base := strings.ToLower(filepath.Base(argv[0]))
	base = strings.TrimSuffix(base, ".exe")
	if len(argv) == 2 && (argv[1] == "--version" || argv[1] == "-v" || argv[1] == "version") {
		return "low"
	}
	switch base {
	case "rm", "del", "erase", "rmdir", "rd", "remove-item", "ri", "format", "diskpart", "shutdown", "reboot", "mkfs", "dd":
		return "critical"
	case "pip", "pip3", "curl", "wget":
		return "high"
	case "python", "python3", "py", "powershell", "pwsh", "cmd", "bash", "sh", "node":
		return "high"
	case "npm":
		if len(argv) > 1 && (argv[1] == "test" || argv[1] == "run") {
			return "medium"
		}
		return "high"
	default:
		if dangerousCommand(argv) != "" {
			return "critical"
		}
		return "low"
	}
}

func classifyTool(tool string) string {
	t := strings.ToLower(tool)
	switch {
	case strings.Contains(t, "delete") || strings.Contains(t, "terminal") || strings.Contains(t, "execute") || strings.Contains(t, "run_project"):
		return "high"
	case strings.Contains(t, "write") || strings.Contains(t, "upload") || strings.Contains(t, "import"):
		return "medium"
	default:
		return "low"
	}
}

func commandArgs(v any) []string {
	switch x := v.(type) {
	case string:
		return strings.Fields(x)
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			if s, ok := item.(string); ok && s != "" {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return x
	default:
		return nil
	}
}

func firstString(payload map[string]any, keys ...string) string {
	for _, key := range keys {
		if v, ok := payload[key]; ok {
			if s, ok := v.(string); ok {
				return strings.TrimSpace(s)
			}
		}
	}
	return ""
}

func boolValue(value any) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return strings.EqualFold(v, "true") || v == "1" || strings.EqualFold(v, "yes")
	case float64:
		return v != 0
	case int:
		return v != 0
	default:
		return false
	}
}

func intValue(value any) int {
	switch v := value.(type) {
	case int:
		return v
	case float64:
		return int(v)
	case string:
		var n int
		if _, err := fmt.Sscanf(v, "%d", &n); err == nil {
			return n
		}
	}
	return 0
}

func maskAPIKey(key string) string {
	if key == "" {
		return ""
	}
	if len(key) <= 8 {
		return strings.Repeat("*", len(key))
	}
	return key[:4] + strings.Repeat("*", len(key)-8) + key[len(key)-4:]
}

func maskedDevice(cfg deviceConfig) map[string]any {
	return map[string]any{
		"success":        true,
		"has_config":     cfg.APIKey != "",
		"device_id":      cfg.DeviceID,
		"provider":       cfg.Provider,
		"api_url":        cfg.APIURL,
		"apiUrl":         cfg.APIURL,
		"model":          cfg.Model,
		"masked_api_key": maskAPIKey(cfg.APIKey),
		"api_key":        maskAPIKey(cfg.APIKey),
		"apiKey":         maskAPIKey(cfg.APIKey),
		"bound":          cfg.APIKey != "",
		"updated":        cfg.Updated,
	}
}

func normalizeProviderDefaults(cfg *deviceConfig) {
	provider := strings.ToLower(cfg.Provider)
	if provider == "kimi" || provider == "moonshot" || strings.Contains(provider, "kimi") {
		if cfg.APIURL == "" {
			cfg.APIURL = "https://api.moonshot.ai/v1"
		}
		if cfg.Model == "" {
			cfg.Model = "kimi-k2.6"
		}
	}
	if provider == "openai" && cfg.APIURL == "" {
		cfg.APIURL = "https://api.openai.com/v1"
	}
	if provider == "deepseek" {
		if cfg.APIURL == "" {
			cfg.APIURL = "https://api.deepseek.com/v1"
		}
		if cfg.Model == "" {
			cfg.Model = "deepseek-chat"
		}
	}
}

func chatCompletionsURL(base string) string {
	base = strings.TrimRight(base, "/")
	if strings.HasSuffix(base, "/chat/completions") {
		return base
	}
	return base + "/chat/completions"
}

func extractAssistantContent(upstream map[string]any) string {
	choices, _ := upstream["choices"].([]any)
	if len(choices) == 0 {
		return ""
	}
	first, _ := choices[0].(map[string]any)
	if first == nil {
		return ""
	}
	message, _ := first["message"].(map[string]any)
	if message == nil {
		return firstString(first, "text", "content")
	}
	return firstString(message, "content")
}
