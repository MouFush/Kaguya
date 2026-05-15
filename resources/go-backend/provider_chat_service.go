package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const (
	pcsDefaultTimeout = 90 * time.Second
	pcsMaxBodyBytes   = 16 << 20
)

type providerChatService struct {
	client *http.Client
}

type providerChatOptions struct {
	OpenAICompatibleResponse bool
	Stream                   bool
}

type providerChatResult struct {
	StatusCode  int
	ContentType string
	Body        []byte
	JSON        map[string]any
	Events      []map[string]any
}

type providerChatError struct {
	Success    bool   `json:"success"`
	Mode       string `json:"mode"`
	Provider   string `json:"provider,omitempty"`
	Model      string `json:"model,omitempty"`
	Error      string `json:"error"`
	Message    string `json:"message"`
	StatusCode int    `json:"status_code,omitempty"`
	Detail     string `json:"detail,omitempty"`
}

type providerChatDefault struct {
	Canonical string
	APIURL    string
	Model     string
}

func newProviderChatService(client *http.Client) providerChatService {
	if client == nil {
		client = http.DefaultClient
	}
	return providerChatService{client: client}
}

func pcsNormalizeExternalProviderConfig(payload map[string]any, existing deviceConfig) deviceConfig {
	if payload == nil {
		payload = map[string]any{}
	}
	cfg := deviceConfig{
		DeviceID: firstString(payload, "device_id", "deviceId"),
		Provider: firstString(payload, "provider"),
		APIURL:   firstString(payload, "api_url", "apiUrl", "base_url", "baseUrl"),
		APIKey:   firstString(payload, "api_key", "apiKey", "key"),
		Model:    firstString(payload, "model"),
		Updated:  time.Now().UTC().Format(time.RFC3339),
	}
	for _, key := range []string{"external_api", "externalApi", "config", "provider_config", "providerConfig"} {
		nested, ok := payload[key].(map[string]any)
		if !ok {
			continue
		}
		n := pcsNormalizeExternalProviderConfig(nested, deviceConfig{})
		if cfg.DeviceID == "" {
			cfg.DeviceID = n.DeviceID
		}
		if cfg.Provider == "" {
			cfg.Provider = n.Provider
		}
		if cfg.APIURL == "" {
			cfg.APIURL = n.APIURL
		}
		if cfg.APIKey == "" {
			cfg.APIKey = n.APIKey
		}
		if cfg.Model == "" {
			cfg.Model = n.Model
		}
	}
	if cfg.DeviceID == "" {
		cfg.DeviceID = existing.DeviceID
	}
	if cfg.Provider == "" {
		cfg.Provider = existing.Provider
	}
	if cfg.APIURL == "" {
		cfg.APIURL = existing.APIURL
	}
	if cfg.APIKey == "" || (existing.APIKey != "" && cfg.APIKey == maskAPIKey(existing.APIKey)) {
		cfg.APIKey = existing.APIKey
	}
	if cfg.Model == "" {
		cfg.Model = existing.Model
	}
	pcsApplyProviderDefaults(&cfg)
	return cfg
}

func pcsApplyProviderDefaults(cfg *deviceConfig) {
	defaults, ok := pcsProviderDefault(cfg.Provider)
	if !ok {
		return
	}
	if cfg.Provider == "" {
		cfg.Provider = defaults.Canonical
	}
	if cfg.APIURL == "" {
		cfg.APIURL = defaults.APIURL
	}
	if cfg.Model == "" {
		cfg.Model = defaults.Model
	}
}

func pcsProviderDefault(provider string) (providerChatDefault, bool) {
	p := strings.ToLower(strings.TrimSpace(provider))
	switch {
	case p == "kimi" || p == "moonshot" || strings.Contains(p, "kimi") || strings.Contains(p, "moonshot"):
		return providerChatDefault{Canonical: "kimi", APIURL: "https://api.moonshot.ai/v1", Model: "kimi-k2.6"}, true
	case p == "deepseek" || strings.Contains(p, "deepseek"):
		return providerChatDefault{Canonical: "deepseek", APIURL: "https://api.deepseek.com/v1", Model: "deepseek-chat"}, true
	case p == "openai" || strings.Contains(p, "openai"):
		return providerChatDefault{Canonical: "openai", APIURL: "https://api.openai.com/v1", Model: "gpt-4o-mini"}, true
	default:
		return providerChatDefault{}, false
	}
}

func pcsMaskedProviderConfig(cfg deviceConfig) map[string]any {
	return map[string]any{
		"success":        true,
		"provider":       cfg.Provider,
		"api_url":        cfg.APIURL,
		"apiUrl":         cfg.APIURL,
		"model":          cfg.Model,
		"has_config":     cfg.APIKey != "",
		"masked_api_key": maskAPIKey(cfg.APIKey),
		"api_key":        maskAPIKey(cfg.APIKey),
		"apiKey":         maskAPIKey(cfg.APIKey),
	}
}

func (p providerChatService) complete(ctx context.Context, cfg deviceConfig, payload map[string]any, opts providerChatOptions) (providerChatResult, error) {
	if cfg.APIKey == "" {
		return providerChatResult{StatusCode: http.StatusServiceUnavailable, JSON: pcsErrorJSON(http.StatusServiceUnavailable, cfg, "missing_api_key", "External provider API key is not configured.", "")}, nil
	}
	if cfg.APIURL == "" {
		return providerChatResult{StatusCode: http.StatusBadRequest, JSON: pcsErrorJSON(http.StatusBadRequest, cfg, "missing_api_url", "External provider API URL is not configured.", "")}, nil
	}
	upstreamPayload, err := pcsOpenAICompatiblePayload(payload, cfg, opts.Stream)
	if err != nil {
		return providerChatResult{StatusCode: http.StatusBadRequest, JSON: pcsErrorJSON(http.StatusBadRequest, cfg, "invalid_payload", err.Error(), "")}, nil
	}
	reqBody, err := json.Marshal(upstreamPayload)
	if err != nil {
		return providerChatResult{StatusCode: http.StatusBadRequest, JSON: pcsErrorJSON(http.StatusBadRequest, cfg, "invalid_payload", err.Error(), "")}, nil
	}
	ctx, cancel := context.WithTimeout(ctx, pcsDefaultTimeout)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, chatCompletionsURL(cfg.APIURL), bytes.NewReader(reqBody))
	if err != nil {
		return providerChatResult{StatusCode: http.StatusBadRequest, JSON: pcsErrorJSON(http.StatusBadRequest, cfg, "invalid_api_url", err.Error(), "")}, nil
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", pcsAcceptHeader(opts.Stream))
	req.Header.Set("Authorization", "Bearer "+cfg.APIKey)
	resp, err := p.client.Do(req)
	if err != nil {
		return providerChatResult{StatusCode: http.StatusBadGateway, JSON: pcsErrorJSON(http.StatusBadGateway, cfg, "provider_request_failed", "External provider request failed.", err.Error())}, nil
	}
	defer resp.Body.Close()
	if opts.Stream || strings.Contains(resp.Header.Get("Content-Type"), "text/event-stream") {
		return p.readStreamResponse(resp, cfg)
	}
	return p.readJSONResponse(resp, cfg, opts)
}

func (p providerChatService) serve(w http.ResponseWriter, r *http.Request, cfg deviceConfig, payload map[string]any, opts providerChatOptions) {
	result, err := p.complete(r.Context(), cfg, payload, opts)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, pcsErrorJSON(http.StatusBadGateway, cfg, "provider_request_failed", "External provider request failed.", err.Error()))
		return
	}
	if len(result.Events) > 0 {
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		for _, event := range result.Events {
			b, _ := json.Marshal(event)
			_, _ = fmt.Fprintf(w, "data: %s\n\n", b)
		}
		return
	}
	if result.ContentType != "" && result.JSON == nil {
		w.Header().Set("Content-Type", result.ContentType)
		w.WriteHeader(result.StatusCode)
		_, _ = w.Write(result.Body)
		return
	}
	writeJSON(w, result.StatusCode, result.JSON)
}

func (p providerChatService) readJSONResponse(resp *http.Response, cfg deviceConfig, opts providerChatOptions) (providerChatResult, error) {
	body, _ := io.ReadAll(io.LimitReader(resp.Body, pcsMaxBodyBytes))
	body = pcsRedactSecrets(body, cfg.APIKey)
	if resp.StatusCode >= 400 {
		return providerChatResult{
			StatusCode: resp.StatusCode,
			JSON:       pcsErrorJSON(resp.StatusCode, cfg, "provider_error", "External provider returned an error.", string(body)),
		}, nil
	}
	var upstream map[string]any
	if err := json.Unmarshal(body, &upstream); err != nil {
		return providerChatResult{StatusCode: resp.StatusCode, ContentType: resp.Header.Get("Content-Type"), Body: body}, nil
	}
	pcsSanitizeMap(upstream, cfg.APIKey)
	if opts.OpenAICompatibleResponse {
		return providerChatResult{StatusCode: resp.StatusCode, JSON: upstream}, nil
	}
	return providerChatResult{
		StatusCode: http.StatusOK,
		JSON: map[string]any{
			"success":  true,
			"mode":     "go",
			"provider": cfg.Provider,
			"model":    cfg.Model,
			"response": extractAssistantContent(upstream),
			"raw":      upstream,
		},
	}, nil
}

func (p providerChatService) readStreamResponse(resp *http.Response, cfg deviceConfig) (providerChatResult, error) {
	events := []map[string]any{}
	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, pcsMaxBodyBytes))
		body = pcsRedactSecrets(body, cfg.APIKey)
		return providerChatResult{StatusCode: resp.StatusCode, JSON: pcsErrorJSON(resp.StatusCode, cfg, "provider_error", "External provider returned an error.", string(body))}, nil
	}
	scanner := bufio.NewScanner(io.LimitReader(resp.Body, pcsMaxBodyBytes))
	scanner.Buffer(make([]byte, 0, 64*1024), 2<<20)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, ":") {
			continue
		}
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if data == "[DONE]" {
			events = append(events, map[string]any{"type": "done", "done": true, "success": true})
			continue
		}
		data = string(pcsRedactSecrets([]byte(data), cfg.APIKey))
		var chunk map[string]any
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			events = append(events, map[string]any{"type": "raw", "data": data})
			continue
		}
		pcsSanitizeMap(chunk, cfg.APIKey)
		events = append(events, pcsStreamEventFromChunk(chunk, cfg))
	}
	if err := scanner.Err(); err != nil {
		return providerChatResult{StatusCode: http.StatusBadGateway, JSON: pcsErrorJSON(http.StatusBadGateway, cfg, "provider_stream_failed", "External provider stream failed.", err.Error())}, nil
	}
	if len(events) == 0 || events[len(events)-1]["type"] != "done" {
		events = append(events, map[string]any{"type": "done", "done": true, "success": true})
	}
	return providerChatResult{StatusCode: http.StatusOK, Events: events}, nil
}

func pcsOpenAICompatiblePayload(payload map[string]any, cfg deviceConfig, stream bool) (map[string]any, error) {
	if payload == nil {
		payload = map[string]any{}
	}
	out := map[string]any{}
	for k, v := range payload {
		switch k {
		case "api_key", "apiKey", "api_url", "apiUrl", "base_url", "baseUrl", "provider", "external_api", "externalApi", "config", "provider_config", "providerConfig":
			continue
		default:
			out[k] = v
		}
	}
	if out["messages"] == nil {
		message := firstString(payload, "message", "prompt", "input")
		if message == "" {
			return nil, errors.New("messages or message is required")
		}
		out["messages"] = []map[string]any{{"role": "user", "content": message}}
	}
	if out["model"] == nil || out["model"] == "" {
		out["model"] = cfg.Model
	}
	if stream {
		out["stream"] = true
	}
	return out, nil
}

func pcsStreamEventFromChunk(chunk map[string]any, cfg deviceConfig) map[string]any {
	content := pcsExtractStreamContent(chunk)
	event := map[string]any{
		"type":     "delta",
		"success":  true,
		"provider": cfg.Provider,
		"model":    cfg.Model,
		"delta":    content,
		"raw":      chunk,
	}
	if content == "" {
		event["type"] = "chunk"
	}
	return event
}

func pcsExtractStreamContent(chunk map[string]any) string {
	choices, _ := chunk["choices"].([]any)
	if len(choices) == 0 {
		return ""
	}
	first, _ := choices[0].(map[string]any)
	if first == nil {
		return ""
	}
	delta, _ := first["delta"].(map[string]any)
	if delta != nil {
		return firstString(delta, "content")
	}
	message, _ := first["message"].(map[string]any)
	if message != nil {
		return firstString(message, "content")
	}
	return firstString(first, "text", "content")
}

func pcsAcceptHeader(stream bool) string {
	if stream {
		return "text/event-stream"
	}
	return "application/json"
}

func pcsErrorJSON(status int, cfg deviceConfig, code, message, detail string) map[string]any {
	err := providerChatError{
		Success:    false,
		Mode:       "go",
		Provider:   cfg.Provider,
		Model:      cfg.Model,
		Error:      code,
		Message:    pcsRedactString(message, cfg.APIKey),
		StatusCode: status,
		Detail:     pcsRedactString(detail, cfg.APIKey),
	}
	b, _ := json.Marshal(err)
	var out map[string]any
	_ = json.Unmarshal(b, &out)
	if out["detail"] == "" {
		delete(out, "detail")
	}
	out["api_url"] = cfg.APIURL
	out["apiUrl"] = cfg.APIURL
	out["available"] = false
	return out
}

func pcsRedactString(value, secret string) string {
	return string(pcsRedactSecrets([]byte(value), secret))
}

func pcsRedactSecrets(body []byte, secret string) []byte {
	text := string(body)
	if secret != "" {
		text = strings.ReplaceAll(text, secret, maskAPIKey(secret))
	}
	for _, marker := range []string{"api_key", "apiKey", "authorization", "Authorization"} {
		text = pcsRedactJSONLikeField(text, marker)
	}
	return []byte(text)
}

func pcsRedactJSONLikeField(text, field string) string {
	cursor := 0
	for {
		next := strings.Index(text[cursor:], `"`+field+`"`)
		if next < 0 {
			return text
		}
		idx := cursor + next
		if idx < 0 {
			return text
		}
		colon := strings.Index(text[idx:], ":")
		if colon < 0 {
			return text
		}
		valueStart := idx + colon + 1
		for valueStart < len(text) && (text[valueStart] == ' ' || text[valueStart] == '\t') {
			valueStart++
		}
		if valueStart >= len(text) || text[valueStart] != '"' {
			cursor = idx + len(field) + 2
			continue
		}
		valueEnd := valueStart + 1
		escaped := false
		for valueEnd < len(text) {
			ch := text[valueEnd]
			if escaped {
				escaped = false
			} else if ch == '\\' {
				escaped = true
			} else if ch == '"' {
				break
			}
			valueEnd++
		}
		if valueEnd >= len(text) {
			return text
		}
		text = text[:valueStart+1] + "[redacted]" + text[valueEnd:]
		cursor = valueStart + len("[redacted]") + 2
	}
}

func pcsSanitizeMap(value map[string]any, secret string) {
	for key, item := range value {
		lower := strings.ToLower(key)
		if lower == "api_key" || lower == "apikey" || lower == "authorization" {
			value[key] = "[redacted]"
			continue
		}
		switch typed := item.(type) {
		case string:
			value[key] = pcsRedactString(typed, secret)
		case map[string]any:
			pcsSanitizeMap(typed, secret)
		case []any:
			pcsSanitizeSlice(typed, secret)
		}
	}
}

func pcsSanitizeSlice(value []any, secret string) {
	for i, item := range value {
		switch typed := item.(type) {
		case string:
			value[i] = pcsRedactString(typed, secret)
		case map[string]any:
			pcsSanitizeMap(typed, secret)
		case []any:
			pcsSanitizeSlice(typed, secret)
		}
	}
}
