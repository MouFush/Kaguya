package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
	"unicode"
)

const (
	knowledgeRAGStoreVersion = 1
	knowledgeRAGMaxPreview   = 1200
)

type KnowledgeRAGService struct {
	mu       sync.Mutex
	baseDir  string
	dataPath string
	cacheDir string
	now      func() time.Time
}

type KnowledgeRAGStore struct {
	Version   int                    `json:"version"`
	Docs      []KnowledgeRAGDocument `json:"documents"`
	UpdatedAt string                 `json:"updated_at"`
}

type KnowledgeRAGDocument struct {
	ID          string         `json:"id"`
	Title       string         `json:"title"`
	Text        string         `json:"text,omitempty"`
	Source      string         `json:"source,omitempty"`
	Filename    string         `json:"filename,omitempty"`
	ContentType string         `json:"content_type,omitempty"`
	Tags        []string       `json:"tags,omitempty"`
	Metadata    map[string]any `json:"metadata,omitempty"`
	Size        int            `json:"size"`
	Chunks      int            `json:"chunks"`
	CreatedAt   string         `json:"created_at"`
	UpdatedAt   string         `json:"updated_at"`
}

type KnowledgeRAGSearchResult struct {
	ID        string         `json:"id"`
	Title     string         `json:"title"`
	Source    string         `json:"source,omitempty"`
	Filename  string         `json:"filename,omitempty"`
	Score     float64        `json:"score"`
	Matches   int            `json:"matches"`
	Snippet   string         `json:"snippet"`
	Tags      []string       `json:"tags,omitempty"`
	Metadata  map[string]any `json:"metadata,omitempty"`
	CreatedAt string         `json:"created_at"`
	UpdatedAt string         `json:"updated_at"`
}

type KnowledgeRAGStats struct {
	Documents     int      `json:"documents"`
	Chunks        int      `json:"chunks"`
	Characters    int      `json:"characters"`
	Bytes         int      `json:"bytes"`
	Vectors       int      `json:"vectors"`
	Tags          []string `json:"tags"`
	CacheFiles    int      `json:"cache_files"`
	LastUpdatedAt string   `json:"last_updated_at,omitempty"`
}

func NewKnowledgeRAGService(runtimeDir string) (*KnowledgeRAGService, error) {
	if strings.TrimSpace(runtimeDir) == "" {
		return nil, errors.New("runtime dir is required")
	}
	base := filepath.Join(runtimeDir, "knowledge_rag")
	svc := &KnowledgeRAGService{
		baseDir:  base,
		dataPath: filepath.Join(base, "documents.json"),
		cacheDir: filepath.Join(base, "cache"),
		now: func() time.Time {
			return time.Now().UTC()
		},
	}
	if err := os.MkdirAll(svc.cacheDir, 0o700); err != nil {
		return nil, err
	}
	return svc, nil
}

func (svc *KnowledgeRAGService) Register(mux *http.ServeMux) {
	mux.HandleFunc("/rag/documents", svc.handleDocuments)
	mux.HandleFunc("/rag/add_text", svc.handleAddText)
	mux.HandleFunc("/rag/upload_metadata", svc.handleUploadMetadata)
	mux.HandleFunc("/rag/upload-metadata", svc.handleUploadMetadata)
	mux.HandleFunc("/rag/search", svc.handleSearch)
	mux.HandleFunc("/rag/stats", svc.handleStats)
	mux.HandleFunc("/rag/preview", svc.handlePreview)
	mux.HandleFunc("/rag/delete", svc.handleDelete)
	mux.HandleFunc("/rag/clear_cache", svc.handleClearCache)
	mux.HandleFunc("/rag/clear-cache", svc.handleClearCache)
	mux.HandleFunc("/rag/analysis", svc.handleStructuredUnavailable("rag_analysis"))
	mux.HandleFunc("/rag/build-graph", svc.handleStructuredUnavailable("rag_knowledge_graph"))
	mux.HandleFunc("/kb/add", svc.handleAddText)
	mux.HandleFunc("/kb/search", svc.handleSearch)
}

func (svc *KnowledgeRAGService) AddText(payload map[string]any) (KnowledgeRAGDocument, error) {
	if payload == nil {
		payload = map[string]any{}
	}
	text := strings.TrimSpace(firstString(payload, "text", "content", "document", "body"))
	if text == "" {
		return KnowledgeRAGDocument{}, errors.New("text is required")
	}
	now := svc.now().Format(time.RFC3339Nano)
	doc := KnowledgeRAGDocument{
		ID:          strings.TrimSpace(firstString(payload, "id", "document_id", "doc_id")),
		Title:       strings.TrimSpace(firstString(payload, "title", "name", "filename")),
		Text:        text,
		Source:      strings.TrimSpace(firstString(payload, "source", "url", "path")),
		Filename:    strings.TrimSpace(firstString(payload, "filename", "file_name", "name")),
		ContentType: strings.TrimSpace(firstString(payload, "content_type", "contentType", "mime_type")),
		Tags:        normalizeTags(payload["tags"]),
		Metadata:    normalizeMetadata(payload["metadata"]),
		Size:        len([]rune(text)),
		Chunks:      countKnowledgeChunks(text),
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	if doc.Title == "" {
		doc.Title = titleFromText(text)
	}
	if doc.Filename == "" && doc.Source != "" {
		doc.Filename = filepath.Base(filepath.Clean(doc.Source))
	}
	if doc.ContentType == "" {
		doc.ContentType = "text/plain"
	}
	if doc.ID == "" {
		doc.ID = knowledgeDocID(doc.Title, text, now)
	}
	return svc.UpsertDocument(doc)
}

func (svc *KnowledgeRAGService) AddMetadata(payload map[string]any) (KnowledgeRAGDocument, error) {
	if payload == nil {
		payload = map[string]any{}
	}
	title := strings.TrimSpace(firstString(payload, "title", "name", "filename", "file_name"))
	source := strings.TrimSpace(firstString(payload, "source", "url", "path"))
	filename := strings.TrimSpace(firstString(payload, "filename", "file_name", "name"))
	text := strings.TrimSpace(firstString(payload, "text", "content", "document", "preview"))
	if title == "" && filename == "" && source == "" && text == "" {
		return KnowledgeRAGDocument{}, errors.New("metadata requires title, filename, source, or text")
	}
	now := svc.now().Format(time.RFC3339Nano)
	if title == "" {
		if filename != "" {
			title = filename
		} else if source != "" {
			title = filepath.Base(filepath.Clean(source))
		} else {
			title = titleFromText(text)
		}
	}
	if filename == "" && source != "" {
		filename = filepath.Base(filepath.Clean(source))
	}
	doc := KnowledgeRAGDocument{
		ID:          strings.TrimSpace(firstString(payload, "id", "document_id", "doc_id")),
		Title:       title,
		Text:        text,
		Source:      source,
		Filename:    filename,
		ContentType: strings.TrimSpace(firstString(payload, "content_type", "contentType", "mime_type")),
		Tags:        normalizeTags(payload["tags"]),
		Metadata:    normalizeMetadata(payload["metadata"]),
		Size:        len([]rune(text)),
		Chunks:      countKnowledgeChunks(text),
		CreatedAt:   now,
		UpdatedAt:   now,
	}
	if doc.ContentType == "" {
		doc.ContentType = "application/octet-stream"
	}
	if doc.ID == "" {
		doc.ID = knowledgeDocID(doc.Title, doc.Source+"|"+doc.Filename+"|"+doc.Text, now)
	}
	return svc.UpsertDocument(doc)
}

func (svc *KnowledgeRAGService) UpsertDocument(doc KnowledgeRAGDocument) (KnowledgeRAGDocument, error) {
	svc.mu.Lock()
	defer svc.mu.Unlock()

	store, err := svc.loadStoreLocked()
	if err != nil {
		return KnowledgeRAGDocument{}, err
	}
	if doc.ID == "" {
		doc.ID = knowledgeDocID(doc.Title, doc.Text, svc.now().Format(time.RFC3339Nano))
	}
	if doc.Title == "" {
		doc.Title = titleFromText(doc.Text)
	}
	if doc.CreatedAt == "" {
		doc.CreatedAt = svc.now().Format(time.RFC3339Nano)
	}
	doc.UpdatedAt = svc.now().Format(time.RFC3339Nano)
	doc.Size = len([]rune(doc.Text))
	doc.Chunks = countKnowledgeChunks(doc.Text)
	if doc.Metadata == nil {
		doc.Metadata = map[string]any{}
	}
	if doc.Tags == nil {
		doc.Tags = []string{}
	}

	replaced := false
	for i, existing := range store.Docs {
		if existing.ID == doc.ID {
			if doc.CreatedAt == "" {
				doc.CreatedAt = existing.CreatedAt
			}
			store.Docs[i] = doc
			replaced = true
			break
		}
	}
	if !replaced {
		store.Docs = append(store.Docs, doc)
	}
	store.UpdatedAt = svc.now().Format(time.RFC3339Nano)
	sort.SliceStable(store.Docs, func(i, j int) bool {
		return store.Docs[i].CreatedAt > store.Docs[j].CreatedAt
	})
	if err := svc.saveStoreLocked(store); err != nil {
		return KnowledgeRAGDocument{}, err
	}
	return doc, nil
}

func (svc *KnowledgeRAGService) Documents() ([]KnowledgeRAGDocument, error) {
	svc.mu.Lock()
	defer svc.mu.Unlock()
	store, err := svc.loadStoreLocked()
	if err != nil {
		return nil, err
	}
	return append([]KnowledgeRAGDocument(nil), store.Docs...), nil
}

func (svc *KnowledgeRAGService) Search(query string, limit int) ([]KnowledgeRAGSearchResult, error) {
	query = strings.TrimSpace(query)
	if limit <= 0 {
		limit = 10
	}
	if limit > 100 {
		limit = 100
	}
	docs, err := svc.Documents()
	if err != nil {
		return nil, err
	}
	terms := tokenizeKnowledge(query)
	results := make([]KnowledgeRAGSearchResult, 0, len(docs))
	for _, doc := range docs {
		score, matches := scoreKnowledgeDocument(doc, terms)
		if len(terms) > 0 && matches == 0 {
			continue
		}
		results = append(results, KnowledgeRAGSearchResult{
			ID:        doc.ID,
			Title:     doc.Title,
			Source:    doc.Source,
			Filename:  doc.Filename,
			Score:     score,
			Matches:   matches,
			Snippet:   buildKnowledgeSnippet(doc.Text, terms),
			Tags:      doc.Tags,
			Metadata:  doc.Metadata,
			CreatedAt: doc.CreatedAt,
			UpdatedAt: doc.UpdatedAt,
		})
	}
	sort.SliceStable(results, func(i, j int) bool {
		if results[i].Score == results[j].Score {
			return results[i].UpdatedAt > results[j].UpdatedAt
		}
		return results[i].Score > results[j].Score
	})
	if len(results) > limit {
		results = results[:limit]
	}
	_ = svc.writeSearchCache(query, results)
	return results, nil
}

func (svc *KnowledgeRAGService) Stats() (KnowledgeRAGStats, error) {
	docs, err := svc.Documents()
	if err != nil {
		return KnowledgeRAGStats{}, err
	}
	stats := KnowledgeRAGStats{
		Documents: len(docs),
		Vectors:   0,
		Tags:      []string{},
	}
	tagSet := map[string]bool{}
	for _, doc := range docs {
		stats.Chunks += doc.Chunks
		stats.Characters += len([]rune(doc.Text))
		stats.Bytes += len([]byte(doc.Text))
		if doc.UpdatedAt > stats.LastUpdatedAt {
			stats.LastUpdatedAt = doc.UpdatedAt
		}
		for _, tag := range doc.Tags {
			tag = strings.TrimSpace(tag)
			if tag != "" && !tagSet[tag] {
				tagSet[tag] = true
				stats.Tags = append(stats.Tags, tag)
			}
		}
	}
	sort.Strings(stats.Tags)
	stats.CacheFiles = countFiles(svc.cacheDir)
	return stats, nil
}

func (svc *KnowledgeRAGService) Preview(id string) (map[string]any, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return nil, errors.New("document id is required")
	}
	docs, err := svc.Documents()
	if err != nil {
		return nil, err
	}
	for _, doc := range docs {
		if doc.ID == id {
			text := []rune(doc.Text)
			truncated := false
			if len(text) > knowledgeRAGMaxPreview {
				text = text[:knowledgeRAGMaxPreview]
				truncated = true
			}
			return map[string]any{
				"success":   true,
				"mode":      "go",
				"document":  doc,
				"preview":   string(text),
				"truncated": truncated,
			}, nil
		}
	}
	return nil, os.ErrNotExist
}

func (svc *KnowledgeRAGService) Delete(id string) (bool, error) {
	id = strings.TrimSpace(id)
	if id == "" {
		return false, errors.New("document id is required")
	}
	svc.mu.Lock()
	defer svc.mu.Unlock()
	store, err := svc.loadStoreLocked()
	if err != nil {
		return false, err
	}
	next := make([]KnowledgeRAGDocument, 0, len(store.Docs))
	deleted := false
	for _, doc := range store.Docs {
		if doc.ID == id {
			deleted = true
			continue
		}
		next = append(next, doc)
	}
	if !deleted {
		return false, nil
	}
	store.Docs = next
	store.UpdatedAt = svc.now().Format(time.RFC3339Nano)
	return true, svc.saveStoreLocked(store)
}

func (svc *KnowledgeRAGService) ClearCache() (int, error) {
	before := countFiles(svc.cacheDir)
	if err := os.RemoveAll(svc.cacheDir); err != nil {
		return 0, err
	}
	if err := os.MkdirAll(svc.cacheDir, 0o700); err != nil {
		return 0, err
	}
	return before, nil
}

func (svc *KnowledgeRAGService) handleDocuments(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		docs, err := svc.Documents()
		if err != nil {
			writeError(w, http.StatusInternalServerError, "rag_store_failed", err.Error())
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"success":   true,
			"mode":      "go",
			"documents": docs,
			"count":     len(docs),
		})
	case http.MethodPost:
		svc.handleAddText(w, r)
	default:
		methodNotAllowed(w)
	}
}

func (svc *KnowledgeRAGService) handleAddText(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	doc, err := svc.AddText(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "missing_text", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":  true,
		"mode":     "go",
		"document": doc,
		"id":       doc.ID,
		"chunks":   doc.Chunks,
	})
}

func (svc *KnowledgeRAGService) handleUploadMetadata(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	var payload map[string]any
	_ = readJSON(r, &payload)
	doc, err := svc.AddMetadata(payload)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_metadata", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":  true,
		"mode":     "go",
		"document": doc,
		"id":       doc.ID,
	})
}

func (svc *KnowledgeRAGService) handleSearch(w http.ResponseWriter, r *http.Request) {
	query := strings.TrimSpace(r.URL.Query().Get("q"))
	limit := 10
	if r.Method == http.MethodPost {
		var payload map[string]any
		_ = readJSON(r, &payload)
		if query == "" {
			query = firstString(payload, "q", "query", "text")
		}
		limit = intFromPayload(payload, "limit", "top_k", "topK")
	}
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	results, err := svc.Search(query, limit)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "search_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"query":   query,
		"results": results,
		"count":   len(results),
	})
}

func (svc *KnowledgeRAGService) handleStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		methodNotAllowed(w)
		return
	}
	stats, err := svc.Stats()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "stats_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"stats":   stats,
	})
}

func (svc *KnowledgeRAGService) handlePreview(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodPost {
		methodNotAllowed(w)
		return
	}
	id := strings.TrimSpace(r.URL.Query().Get("id"))
	if r.Method == http.MethodPost && id == "" {
		var payload map[string]any
		_ = readJSON(r, &payload)
		id = firstString(payload, "id", "document_id", "doc_id")
	}
	result, err := svc.Preview(id)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			writeError(w, http.StatusNotFound, "document_not_found", "document not found")
			return
		}
		writeError(w, http.StatusBadRequest, "invalid_document", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, result)
}

func (svc *KnowledgeRAGService) handleDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	id := strings.TrimSpace(r.URL.Query().Get("id"))
	if id == "" {
		var payload map[string]any
		_ = readJSON(r, &payload)
		id = firstString(payload, "id", "document_id", "doc_id")
	}
	deleted, err := svc.Delete(id)
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_document", err.Error())
		return
	}
	if !deleted {
		writeJSON(w, http.StatusNotFound, map[string]any{
			"success": false,
			"mode":    "go",
			"deleted": false,
			"error":   "document_not_found",
			"id":      id,
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success": true,
		"mode":    "go",
		"deleted": true,
		"id":      id,
	})
}

func (svc *KnowledgeRAGService) handleClearCache(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		methodNotAllowed(w)
		return
	}
	removed, err := svc.ClearCache()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "clear_cache_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"success":       true,
		"mode":          "go",
		"cache_cleared": true,
		"removed_files": removed,
	})
}

func (svc *KnowledgeRAGService) handleStructuredUnavailable(feature string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"success":   false,
			"mode":      "go",
			"available": false,
			"feature":   feature,
			"error":     "feature_unavailable",
			"reason":    "local JSON RAG store is available, but graph/vector analysis is not implemented in the Go backend yet",
		})
	}
}

func (svc *KnowledgeRAGService) loadStoreLocked() (KnowledgeRAGStore, error) {
	store := KnowledgeRAGStore{
		Version: knowledgeRAGStoreVersion,
		Docs:    []KnowledgeRAGDocument{},
	}
	b, err := os.ReadFile(svc.dataPath)
	if errors.Is(err, os.ErrNotExist) {
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
		store.Version = knowledgeRAGStoreVersion
	}
	if store.Docs == nil {
		store.Docs = []KnowledgeRAGDocument{}
	}
	return store, nil
}

func (svc *KnowledgeRAGService) saveStoreLocked(store KnowledgeRAGStore) error {
	if err := os.MkdirAll(filepath.Dir(svc.dataPath), 0o700); err != nil {
		return err
	}
	if store.Version == 0 {
		store.Version = knowledgeRAGStoreVersion
	}
	store.UpdatedAt = svc.now().Format(time.RFC3339Nano)
	b, err := json.MarshalIndent(store, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(svc.dataPath, b, 0o600)
}

func (svc *KnowledgeRAGService) writeSearchCache(query string, results []KnowledgeRAGSearchResult) error {
	if err := os.MkdirAll(svc.cacheDir, 0o700); err != nil {
		return err
	}
	name := knowledgeCacheName(query)
	payload := map[string]any{
		"query":      query,
		"results":    results,
		"created_at": svc.now().Format(time.RFC3339Nano),
	}
	b, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(svc.cacheDir, name), b, 0o600)
}

func normalizeTags(v any) []string {
	out := []string{}
	seen := map[string]bool{}
	add := func(s string) {
		s = strings.TrimSpace(s)
		if s == "" || seen[s] {
			return
		}
		seen[s] = true
		out = append(out, s)
	}
	switch x := v.(type) {
	case []string:
		for _, s := range x {
			add(s)
		}
	case []any:
		for _, item := range x {
			if s, ok := item.(string); ok {
				add(s)
			}
		}
	case string:
		for _, part := range strings.Split(x, ",") {
			add(part)
		}
	}
	sort.Strings(out)
	return out
}

func normalizeMetadata(v any) map[string]any {
	out := map[string]any{}
	if m, ok := v.(map[string]any); ok {
		for k, val := range m {
			k = strings.TrimSpace(k)
			if k != "" {
				out[k] = val
			}
		}
	}
	return out
}

func tokenizeKnowledge(text string) []string {
	text = strings.ToLower(strings.TrimSpace(text))
	if text == "" {
		return nil
	}
	parts := strings.FieldsFunc(text, func(r rune) bool {
		return unicode.IsSpace(r) || unicode.IsPunct(r) || unicode.IsSymbol(r)
	})
	out := []string{}
	seen := map[string]bool{}
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" || seen[part] {
			continue
		}
		seen[part] = true
		out = append(out, part)
	}
	return out
}

func scoreKnowledgeDocument(doc KnowledgeRAGDocument, terms []string) (float64, int) {
	if len(terms) == 0 {
		return 1, 0
	}
	title := strings.ToLower(doc.Title)
	body := strings.ToLower(doc.Text)
	source := strings.ToLower(doc.Source + " " + doc.Filename + " " + strings.Join(doc.Tags, " "))
	score := 0.0
	matches := 0
	for _, term := range terms {
		termMatches := 0
		if strings.Contains(title, term) {
			score += 4
			termMatches++
		}
		bodyCount := strings.Count(body, term)
		if bodyCount > 0 {
			score += 1 + math.Log(float64(bodyCount)+1)
			termMatches += bodyCount
		}
		if strings.Contains(source, term) {
			score += 1.5
			termMatches++
		}
		matches += termMatches
	}
	score += float64(matches) * 0.05
	return math.Round(score*1000) / 1000, matches
}

func buildKnowledgeSnippet(text string, terms []string) string {
	runes := []rune(strings.TrimSpace(text))
	if len(runes) == 0 {
		return ""
	}
	start := 0
	lower := strings.ToLower(string(runes))
	for _, term := range terms {
		if idx := strings.Index(lower, strings.ToLower(term)); idx >= 0 {
			start = len([]rune(lower[:idx])) - 80
			if start < 0 {
				start = 0
			}
			break
		}
	}
	end := start + 260
	if end > len(runes) {
		end = len(runes)
	}
	snippet := strings.TrimSpace(string(runes[start:end]))
	if start > 0 {
		snippet = "..." + snippet
	}
	if end < len(runes) {
		snippet += "..."
	}
	return snippet
}

func countKnowledgeChunks(text string) int {
	text = strings.TrimSpace(text)
	if text == "" {
		return 0
	}
	runes := len([]rune(text))
	chunks := runes / 1000
	if runes%1000 != 0 {
		chunks++
	}
	if chunks < 1 {
		chunks = 1
	}
	return chunks
}

func titleFromText(text string) string {
	text = strings.TrimSpace(text)
	if text == "" {
		return "Untitled document"
	}
	lines := strings.Split(text, "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		runes := []rune(line)
		if len(runes) > 80 {
			line = string(runes[:80])
		}
		return line
	}
	return "Untitled document"
}

func knowledgeDocID(title, text, salt string) string {
	sum := sha256.Sum256([]byte(title + "\n" + text + "\n" + salt))
	return "rag-" + hex.EncodeToString(sum[:])[:16]
}

func knowledgeCacheName(query string) string {
	sum := sha256.Sum256([]byte(query))
	return "search-" + hex.EncodeToString(sum[:])[:16] + ".json"
}

func intFromPayload(payload map[string]any, keys ...string) int {
	for _, key := range keys {
		v, ok := payload[key]
		if !ok {
			continue
		}
		switch x := v.(type) {
		case int:
			return x
		case int64:
			return int(x)
		case float64:
			return int(x)
		case json.Number:
			i, _ := x.Int64()
			return int(i)
		case string:
			var i int
			if _, err := fmt.Sscanf(x, "%d", &i); err == nil {
				return i
			}
		}
	}
	return 0
}

func countFiles(root string) int {
	count := 0
	_ = filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil || d == nil || d.IsDir() {
			return nil
		}
		count++
		return nil
	})
	return count
}
