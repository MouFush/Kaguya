package main

import (
	"encoding/json"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func newKnowledgeRAGTestService(t *testing.T) (*KnowledgeRAGService, http.Handler) {
	t.Helper()
	svc, err := NewKnowledgeRAGService(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	base := time.Date(2026, 5, 15, 8, 0, 0, 0, time.UTC)
	tick := 0
	svc.now = func() time.Time {
		tick++
		return base.Add(time.Duration(tick) * time.Second)
	}
	mux := http.NewServeMux()
	svc.Register(mux)
	return svc, mux
}

func TestKnowledgeRAGAddSearchDeleteStats(t *testing.T) {
	svc, h := newKnowledgeRAGTestService(t)

	rec := requestJSON(t, h, http.MethodPost, "/rag/add_text", map[string]any{
		"title":    "Kimi API troubleshooting",
		"text":     "Kimi K2.6 provider requires a Moonshot compatible OpenAI chat completions endpoint.",
		"source":   "manual",
		"tags":     []any{"kimi", "api", "kimi"},
		"metadata": map[string]any{"owner": "worker6"},
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("add status=%d body=%s", rec.Code, rec.Body.String())
	}
	added := decodeBody(t, rec)
	docRaw, ok := added["document"].(map[string]any)
	if !ok {
		t.Fatalf("missing document in %v", added)
	}
	docID, _ := docRaw["id"].(string)
	if docID == "" {
		t.Fatalf("missing document id: %v", added)
	}
	if docRaw["chunks"].(float64) != 1 {
		t.Fatalf("expected one chunk, got %v", docRaw["chunks"])
	}

	rec = requestJSON(t, h, http.MethodPost, "/rag/search", map[string]any{
		"query": "moonshot completions",
		"limit": 5,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("search status=%d body=%s", rec.Code, rec.Body.String())
	}
	search := decodeBody(t, rec)
	results, ok := search["results"].([]any)
	if !ok || len(results) != 1 {
		t.Fatalf("expected one search result, got %s", rec.Body.String())
	}
	first, _ := results[0].(map[string]any)
	if first["id"] != docID {
		t.Fatalf("search returned wrong doc: %v", first)
	}
	if first["score"].(float64) <= 0 {
		t.Fatalf("expected positive score, got %v", first["score"])
	}
	if !strings.Contains(strings.ToLower(first["snippet"].(string)), "moonshot") {
		t.Fatalf("snippet did not include match: %v", first["snippet"])
	}

	stats, err := svc.Stats()
	if err != nil {
		t.Fatal(err)
	}
	if stats.Documents != 1 || stats.Chunks != 1 || stats.Characters == 0 {
		t.Fatalf("bad stats: %+v", stats)
	}
	if len(stats.Tags) != 2 || stats.Tags[0] != "api" || stats.Tags[1] != "kimi" {
		t.Fatalf("tags should be sorted and deduped: %+v", stats.Tags)
	}
	if stats.CacheFiles != 1 {
		t.Fatalf("search cache should have one file, got %+v", stats)
	}

	rec = requestJSON(t, h, http.MethodPost, "/rag/delete", map[string]any{"id": docID})
	if rec.Code != http.StatusOK {
		t.Fatalf("delete status=%d body=%s", rec.Code, rec.Body.String())
	}
	deleted := decodeBody(t, rec)
	if deleted["deleted"] != true {
		t.Fatalf("expected deleted=true, got %v", deleted)
	}
	stats, err = svc.Stats()
	if err != nil {
		t.Fatal(err)
	}
	if stats.Documents != 0 || stats.Chunks != 0 {
		t.Fatalf("delete did not update stats: %+v", stats)
	}
}

func TestKnowledgeRAGPersistsDocumentsAsJSON(t *testing.T) {
	svc, _ := newKnowledgeRAGTestService(t)
	doc, err := svc.AddText(map[string]any{
		"title": "Local JSON persistence",
		"text":  "The Go RAG store persists documents without requiring embeddings or model access.",
	})
	if err != nil {
		t.Fatal(err)
	}
	if doc.ID == "" {
		t.Fatal("expected generated id")
	}
	raw, err := os.ReadFile(filepath.Join(svc.baseDir, "documents.json"))
	if err != nil {
		t.Fatal(err)
	}
	if !json.Valid(raw) {
		t.Fatalf("store is not valid JSON: %s", string(raw))
	}
	if !strings.Contains(string(raw), "Local JSON persistence") {
		t.Fatalf("store did not contain document: %s", string(raw))
	}

	reloaded, err := NewKnowledgeRAGService(filepath.Dir(svc.baseDir))
	if err != nil {
		t.Fatal(err)
	}
	docs, err := reloaded.Documents()
	if err != nil {
		t.Fatal(err)
	}
	if len(docs) != 1 || docs[0].ID != doc.ID {
		t.Fatalf("reload mismatch: %+v", docs)
	}
}

func TestKnowledgeRAGUploadMetadataPreviewAndClearCache(t *testing.T) {
	svc, h := newKnowledgeRAGTestService(t)

	rec := requestJSON(t, h, http.MethodPost, "/rag/upload_metadata", map[string]any{
		"filename":     "design.md",
		"source":       "docs/design.md",
		"content_type": "text/markdown",
		"text":         strings.Repeat("Architecture note. ", 90),
		"metadata":     map[string]any{"kind": "design"},
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("metadata status=%d body=%s", rec.Code, rec.Body.String())
	}
	body := decodeBody(t, rec)
	doc := body["document"].(map[string]any)
	id := doc["id"].(string)

	rec = requestJSON(t, h, http.MethodGet, "/rag/preview?id="+id, nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("preview status=%d body=%s", rec.Code, rec.Body.String())
	}
	preview := decodeBody(t, rec)
	if preview["truncated"] != true {
		t.Fatalf("expected truncated preview, got %v", preview)
	}
	if len([]rune(preview["preview"].(string))) > knowledgeRAGMaxPreview {
		t.Fatalf("preview exceeded limit")
	}

	if _, err := svc.Search("architecture", 10); err != nil {
		t.Fatal(err)
	}
	stats, err := svc.Stats()
	if err != nil {
		t.Fatal(err)
	}
	if stats.CacheFiles == 0 {
		t.Fatalf("expected search cache before clear: %+v", stats)
	}
	rec = requestJSON(t, h, http.MethodPost, "/rag/clear_cache", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("clear cache status=%d body=%s", rec.Code, rec.Body.String())
	}
	stats, err = svc.Stats()
	if err != nil {
		t.Fatal(err)
	}
	if stats.CacheFiles != 0 {
		t.Fatalf("cache should be empty after clear: %+v", stats)
	}
}

func TestKnowledgeRAGStructuredUnavailableForGraphAnalysis(t *testing.T) {
	_, h := newKnowledgeRAGTestService(t)
	for _, path := range []string{"/rag/analysis", "/rag/build-graph"} {
		rec := requestJSON(t, h, http.MethodPost, path, map[string]any{})
		if rec.Code != http.StatusServiceUnavailable {
			t.Fatalf("%s status=%d body=%s", path, rec.Code, rec.Body.String())
		}
		got := decodeBody(t, rec)
		if got["success"] != false || got["available"] != false || got["error"] != "feature_unavailable" {
			t.Fatalf("%s returned wrong unavailable shape: %v", path, got)
		}
	}
}

func TestKnowledgeRAGRejectsInvalidInputs(t *testing.T) {
	_, h := newKnowledgeRAGTestService(t)
	rec := requestJSON(t, h, http.MethodPost, "/rag/add_text", map[string]any{"text": "   "})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("empty add should be rejected, got %d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodPost, "/rag/delete", map[string]any{})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("empty delete should be rejected, got %d body=%s", rec.Code, rec.Body.String())
	}
	rec = requestJSON(t, h, http.MethodGet, "/rag/preview?id=missing", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("missing preview should be 404, got %d body=%s", rec.Code, rec.Body.String())
	}
}
