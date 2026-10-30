package main

import (
    "net/http"
    "strings"
    "time"
)

func (s *Server) ragDocuments(w http.ResponseWriter, r *http.Request) {
	if s.proxy != nil {
		s.proxy.ServeHTTP(w, r)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "documents": []any{}, "mode": "go", "available": false, "reason": "python_worker_unavailable"})
}

func (s *Server) ragAddText(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusServiceUnavailable, "rag_worker_unavailable", "RAG indexing is delegated to the Python worker")
}

func (s *Server) kbAdd(w http.ResponseWriter, r *http.Request) {
	var payload map[string]any
	_ = readJSON(r, &payload)
	if payload == nil {
		payload = map[string]any{}
	}
	text := firstString(payload, "text", "content", "document")
	if strings.TrimSpace(text) == "" {
		writeError(w, http.StatusBadRequest, "missing_text", "text is required")
		return
	}
	item := map[string]any{
		"id":         "kb-" + time.Now().UTC().Format("20060102150405.000000000"),
		"text":       text,
		"created_at": time.Now().UTC().Format(time.RFC3339),
	}
	items, _ := s.loadCollection("knowledge_base")
	items = append(items, item)
	if err := s.saveCollection("knowledge_base", items); err != nil {
		writeError(w, http.StatusInternalServerError, "save_failed", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "item": item})
}

func (s *Server) kbSearch(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query().Get("q")
	if query == "" {
		var payload map[string]any
		_ = readJSON(r, &payload)
		query = firstString(payload, "q", "query", "text")
	}
	items, _ := s.loadCollection("knowledge_base")
	results := []map[string]any{}
	for _, item := range items {
		text := strings.ToLower(firstString(item, "text", "content"))
		if query == "" || strings.Contains(text, strings.ToLower(query)) {
			results = append(results, item)
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "mode": "go", "query": query, "results": results})
}
