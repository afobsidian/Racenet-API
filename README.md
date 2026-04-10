# Horse Racing Racenet API scraper

## Go Web Interface (Phase 2)

The repository now also includes a Go web application that renders the existing
meeting data in a dark web UI and keeps the current Racenet-backed scraper as
the live data source.

Run it from the repository root with:

```bash
go run .
```

Then open `http://localhost:8080`.

- `Use local data` reads `meetings_cache.json`.
- Clearing `Use local data` triggers a live fetch through the existing Python
  scraper modules, then updates `meetings_cache.json`.

### Phase 2 feature set

- **Date navigation** — `‹` / `›` buttons step the date picker one day at a time.
- **Keyboard shortcuts** — `←` / `→` arrow keys switch races; `↑` / `↓` switch meetings (works when no form field is focused).
- **Selection filter** — type in the search box above the selection list to filter runners by name.
- **Selection sort** — sort the list by barrier number, punters edge, predictor score, speed rating, or win odds.
- **Countdown auto-refresh** — the race countdown updates every second.
- **Market book percentage** — a chip on the event overview shows the win-book overround, coloured green / amber / red.
- **Preparation profile** — first-up, second-up, third-up, and nth-up win percentages with average time differences are shown inside each expanded selection (when data is available).
- **Predictor component breakdown** — individual predictor rating components are shown as a bar chart inside each expanded selection (when any component is non-zero).
- **Price history** — win-odds fluctuation chart with movement indicator inside each expanded selection (when two or more price points exist).
- **Enhanced form runs** — the runs table now includes a `Price` column (open/fluct/SP), a `Rivals` column (competitors that have since won), and position-at-distance tooltips on the `Pos` cell. The `Date` cell tooltip shows the video comment / race note for that run.

## Install

To create virtual env to run, navigate to directory containing "requirements.txt" and perform the following:

- `python -m pip install virtualenv`
- `python -m venv .venv`

To activate the virtual env environment, perform the following:

- `.venv\Scripts\Activate.ps1`

To install the requirements for the program run:

- `python -m pip install -r requirements.txt`

To run the program with or without a virtual env, once the requirements are installed, perform the following in the directory with the "main.py" file:

- `python main.py`

## Linux Display Requirements

- This is a desktop PySide6 application, so on Linux it needs an active X11 or Wayland session.
- Running `python main.py` inside a headless container or shell without `DISPLAY` or `WAYLAND_DISPLAY` will now exit with a clear error instead of crashing inside Qt.
- If you only need a non-interactive startup/import check in a headless environment, run with `QT_QPA_PLATFORM=offscreen python main.py`.

## Local Cache

- Live extraction now writes a safe JSON cache to `meetings_cache.json`.
- When `Use local data` is enabled in the UI, the app reads from that cache file instead of evaluating Python objects from disk.
- If the cache file does not exist yet, disable `Use local data` once to fetch and create it.

## Refreshing Persisted Query Hashes

- `puntapi.com/graphql-horse-racing` currently requires either a raw GraphQL document or a persisted-query hash. In practice this app still depends on the persisted-query hashes.
- The runtime hashes now live in `query_hashes.json`, with the previous values kept as defaults in `api_queries.py` if the file is missing or incomplete.
- To refresh the hashes automatically with Playwright, install the extra dependency and Chromium browser:

```bash
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

- Then run the refresher script:

```bash
python refresh_query_hashes.py
```

- If some operations are not captured by the auto crawl, rerun in visible interactive mode and click through the relevant Racenet pages before pressing Enter in the terminal:

```bash
python refresh_query_hashes.py --headed --interactive
```
