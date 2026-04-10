package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func TestHandleMeetingsLocalCache(t *testing.T) {
	t.Parallel()

	repoRoot := t.TempDir()
	cachePath := filepath.Join(repoRoot, "meetings_cache.json")
	if err := os.WriteFile(cachePath, []byte(`[{"name":"Randwick","state":"NSW","events":[]}]`), 0o644); err != nil {
		t.Fatalf("write cache: %v", err)
	}

	app := &application{repoRoot: repoRoot}
	req := httptest.NewRequest(http.MethodGet, "/api/meetings?local=1&date=2026-04-10", nil)
	rec := httptest.NewRecorder()

	app.handleMeetings(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d (%s)", rec.Code, rec.Body.String())
	}

	var response struct {
		Date     string            `json:"date"`
		Source   string            `json:"source"`
		Meetings []json.RawMessage `json:"meetings"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("decode response: %v", err)
	}

	if response.Date != "2026-04-10" {
		t.Fatalf("unexpected date %q", response.Date)
	}
	if response.Source != "cache" {
		t.Fatalf("unexpected source %q", response.Source)
	}
	if len(response.Meetings) != 1 {
		t.Fatalf("expected one meeting, got %d", len(response.Meetings))
	}
}

func TestHandleMeetingsRejectsBadDate(t *testing.T) {
	t.Parallel()

	app := &application{repoRoot: t.TempDir()}
	req := httptest.NewRequest(http.MethodGet, "/api/meetings?date=10-04-2026", nil)
	rec := httptest.NewRecorder()

	app.handleMeetings(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}
