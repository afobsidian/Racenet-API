# Horse Racing Racenet API — Go Web App

## Running

```bash
go run .
```

Open `http://localhost:8080`.

- `Use local data` reads `meetings_cache.json` from the repository root.
- Clearing `Use local data` triggers a live fetch through the Python scraper modules, then updates `meetings_cache.json`.

## Validation

```bash
go build ./...
go test ./...
```

## Feature set

- Meeting browser with grouped sidebar — click a meeting to open it, use `↑` / `↓` to step through them.
- Race selector buttons plus `←` / `→` keyboard shortcuts to move between races.
- Date picker with `‹` / `›` day navigation.
- Race overview — countdown (live 1-second refresh), prize, pace, track condition, distance, class, market book overround.
- Insights side pane — Punters Edge, Predictor, Speed, and Stats panels with bar meters.
- Analysis table — predictor / speed / stats table view switchable via dropdown.
- Expandable selection cards — summary chips (win/place odds with movement, barrier, weight + claim, ROI, ordinal prep label with colour-coded score, freshness), expanded body with:
  - Trainer and jockey chips (colour-coded by win-rate thresholds matching the desktop app).
  - Trainer/jockey combo win % (coloured amber ≥ 12%, red ≥ 20%).
  - Preparation profile (1st-up / 2nd-up / 3rd-up / nth-up win %, average time difference, stdev).
  - Predictor ratings breakdown (bar chart for each non-zero component).
  - Win-odds price history chart with ▲ / ▼ movement indicator and place-odds label.
  - Full form runs table — Jockey, Weight (colour-coded vs current weight), Price (open/fluct/SP), Margin, Days between runs, Class (highlighted for Group/LR races), L800/L600/L400/L200 sectionals (click to toggle raw time vs benchmark rank), R Time, W Time, Runner Tempo, Leader Tempo. Spell separator rows appear when a gap ≥ 60 days is detected. `Pos` cell tooltip includes winner/2nd/3rd names and rivals count.
- Filter by runner name; sort by number, edge, predictor, speed, or win odds.
- Right-click any selection summary to copy the selection line to the clipboard.

## Python scraper modules

The live data source is implemented in Python and is still required to run the server.
Install the scraper dependencies (no PySide6 needed):

```bash
python -m pip install requests
```

### Refreshing persisted query hashes

`puntapi.com/graphql-horse-racing` uses persisted-query hashes. The runtime hashes live in `query_hashes.json`. To refresh them:

```bash
python -m pip install playwright
python -m playwright install chromium
python refresh_query_hashes.py
```

For interactive re-capture:

```bash
python refresh_query_hashes.py --headed --interactive
```
