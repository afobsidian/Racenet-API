package main

import (
	"context"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

//go:embed web/*
var webAssets embed.FS

const liveFetchScript = `
import json
import sys
from dataclasses import asdict
from datetime import datetime

from cache_utils import save_meetings_cache
from scraper import MeetingsScraper


request = json.load(sys.stdin)
scraper = MeetingsScraper()
scrape_date = datetime.strptime(request["date"], "%Y-%m-%d")
cache_path = request["cache_path"]
meetings = scraper.get_meetings(scrape_date)
save_meetings_cache(cache_path, meetings)
print(json.dumps([asdict(meeting) for meeting in meetings]))
`

type application struct {
	repoRoot string
}

type meetingsResponse struct {
	Date     string          `json:"date"`
	Source   string          `json:"source"`
	Meetings json.RawMessage `json:"meetings"`
}

func main() {
	repoRoot, err := os.Getwd()
	if err != nil {
		log.Fatal(err)
	}

	app := &application{repoRoot: repoRoot}
	addr := ":" + defaultPort()

	log.Printf("starting Racenet web app on %s", addr)
	log.Fatal(http.ListenAndServe(addr, app.routes()))
}

func defaultPort() string {
	port := strings.TrimSpace(os.Getenv("PORT"))
	if port == "" {
		return "8080"
	}
	return port
}

func (app *application) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/", app.handleIndex)
	mux.HandleFunc("/api/health", app.handleHealth)
	mux.HandleFunc("/api/meetings", app.handleMeetings)

	staticAssets, err := fs.Sub(webAssets, "web")
	if err != nil {
		panic(err)
	}
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.FS(staticAssets))))
	return app.withCORS(mux)
}

func (app *application) withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (app *application) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	indexHTML, err := webAssets.ReadFile("web/index.html")
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write(indexHTML)
}

func (app *application) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func (app *application) handleMeetings(w http.ResponseWriter, r *http.Request) {
	dateText := strings.TrimSpace(r.URL.Query().Get("date"))
	if dateText == "" {
		dateText = time.Now().Format("2006-01-02")
	}
	if _, err := time.Parse("2006-01-02", dateText); err != nil {
		http.Error(w, "invalid date, expected YYYY-MM-DD", http.StatusBadRequest)
		return
	}

	useLocal := parseBoolQuery(r.URL.Query().Get("local"), true)

	var (
		payload json.RawMessage
		source  string
		err     error
	)

	if useLocal {
		payload, err = app.loadMeetingsCache()
		source = "cache"
	} else {
		payload, err = app.fetchLiveMeetings(r.Context(), dateText)
		source = "live"
	}

	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	response := meetingsResponse{
		Date:     dateText,
		Source:   source,
		Meetings: payload,
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(response)
}

func parseBoolQuery(value string, defaultValue bool) bool {
	if value == "" {
		return defaultValue
	}
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return defaultValue
	}
}

func (app *application) loadMeetingsCache() (json.RawMessage, error) {
	cachePath := filepath.Join(app.repoRoot, "meetings_cache.json")
	payload, err := os.ReadFile(cachePath)
	if err != nil {
		return nil, err
	}
	if !json.Valid(payload) {
		return nil, errors.New("meetings_cache.json is not valid JSON")
	}
	return json.RawMessage(payload), nil
}

func (app *application) fetchLiveMeetings(parent context.Context, dateText string) (json.RawMessage, error) {
	ctx, cancel := context.WithTimeout(parent, 5*time.Minute)
	defer cancel()

	cachePath := filepath.Join(app.repoRoot, "meetings_cache.json")
	requestPayload, err := json.Marshal(map[string]string{
		"date":       dateText,
		"cache_path": cachePath,
	})
	if err != nil {
		return nil, err
	}

	cmd := exec.CommandContext(ctx, "python", "-c", liveFetchScript)
	cmd.Dir = app.repoRoot
	cmd.Stdin = strings.NewReader(string(requestPayload))
	output, err := cmd.CombinedOutput()
	if err != nil {
		trimmed := strings.TrimSpace(string(output))
		if trimmed == "" {
			trimmed = err.Error()
		}
		return nil, fmt.Errorf("live fetch failed: %s", trimmed)
	}

	payload := json.RawMessage(output)
	if !json.Valid(payload) {
		return nil, errors.New("live fetch returned invalid JSON")
	}
	return payload, nil
}
