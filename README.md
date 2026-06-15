# 🏆 FIFA World Cup 2026 — Live Dashboard

Latest stats pulled **every 6 hours**, with a clear "last refreshed" indicator,
**AI summaries**, **current squads**, and **AI predictions** — all in one
Streamlit app.

It's built so the app itself is fast and quota-safe: the app only ever *reads* a
JSON cache. A scheduled job (GitHub Actions every 6 hours, or the **Refresh now**
button) is what pulls fresh stats from API-Football and regenerates the Claude
summaries and predictions.

---

## What you get

| Page | Shows |
|------|-------|
| **Overview** | AI tournament narrative, live-match strip, group standings + AI per-group notes |
| **Matches** | Live scores, recent results, and upcoming fixtures each with an AI predicted winner, scoreline & confidence |
| **Squads** | Current squad for any nation, grouped by position, with per-squad freshness |
| **AI Predictions** | Champion · finalists · dark horse · golden boot, plus a per-match prediction table |

Every page carries a freshness banner: **green** when data is under 6h old,
**amber** once a refresh is due, **red** when there's no cache yet.

---

## Architecture

```
API-Football ──(fetch.py, every 6h)──▶ data/cache/*.json ──(read-only)──▶ Streamlit app
                       │                       ▲
                       └── Claude (ai.py) ─────┘   summaries.json · predictions.json
```

- **`fifa/fetch.py`** — the refresh job. *Quota-aware*: standings & fixtures
  refresh every run (a few calls); squads (48 teams) refresh on a rotating,
  TTL-based schedule so the free 100-requests/day tier is never blown. Falls back
  to bundled **mock data** when no key is set, so the app always renders.
- **`fifa/store.py`** — JSON cache + per-resource timestamps (`meta.json`). JSON,
  not SQLite, so the GitHub Actions commit produces clean text diffs.
- **`fifa/ai.py`** — Claude (`claude-opus-4-8`) writes the summaries and a
  structured prediction object via `messages.parse()` (validated Pydantic schema).
- **`app.py` + `ui/`** — the read-only Streamlit dashboard.

```
fifa2026/
├── app.py                     # Streamlit entry (Overview · Matches · Squads · Predictions)
├── fifa/
│   ├── config.py              # keys, league=1 / season=2026, refresh policy
│   ├── api_football.py        # thin api-sports.io client (+ quota tracking)
│   ├── store.py               # JSON cache + timestamps
│   ├── transform.py           # raw payloads → UI/AI-friendly shapes
│   ├── fetch.py               # the quota-aware refresh job
│   ├── ai.py                  # Claude summaries + structured predictions
│   └── mock.py                # API-shaped sample data (runs with no keys)
├── ui/                        # overview · matches · teams · predictions · components
├── data/cache/                # committed JSON cache (the refresh job writes here)
└── .github/workflows/refresh.yml  # cron: every 6h → fetch --with-ai → commit cache
```

---

## Quick start (local)

```bash
cd ~/fifa2026
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Runs immediately on bundled mock data:
streamlit run app.py

# 2) For real data, add keys and refresh:
cp .env.example .env        # then fill in the two keys
python -m fifa.fetch --with-ai
streamlit run app.py
```

### Getting the keys
- **API-Football** — free at <https://dashboard.api-football.com/> (100 req/day).
  Put it in `.env` as `API_FOOTBALL_KEY`.
- **Claude** — <https://console.claude.com/> → API keys. Put it in `.env` as
  `ANTHROPIC_API_KEY`. (Without it, the app uses deterministic mock AI.)

---

## The every-6-hours refresh (GitHub Actions)

`.github/workflows/refresh.yml` runs `python -m fifa.fetch --with-ai` on a
`0 */6 * * *` cron and commits the refreshed `data/cache/` back to the repo — so
it keeps refreshing even when your machine is off.

1. Push this repo to GitHub.
2. In **Settings → Secrets and variables → Actions**, add:
   - `API_FOOTBALL_KEY`
   - `ANTHROPIC_API_KEY`
3. **Settings → Actions → General → Workflow permissions** → *Read and write*.

Trigger a first run manually from the **Actions** tab (*Refresh FIFA 2026 data →
Run workflow*), or wait for the next 6-hour tick. Deploy the app (e.g. Streamlit
Community Cloud pointed at this repo) and it will pick up each committed refresh.

> Note: GitHub's scheduled runs can be delayed under load and don't run on a
> disabled/forked repo — for a hard guarantee, a hosted cron (Render, Railway,
> Cloud Scheduler) calling the same `fetch` command works identically.

---

## Quota math (why squads rotate)

A full refresh of all 48 squads every 6h = 48 × 4 = **192 calls/day**, over the
free 100/day cap. So squads carry a 24h TTL and only **12 teams** refresh per run
(`FIFA_SQUADS_PER_RUN`), covering all 48 within a day, while
standings/fixtures (a few calls) refresh every run. Tune both in `fifa/config.py`.

---

## CLI reference

```bash
python -m fifa.fetch                 # refresh stats (mock if no key)
python -m fifa.fetch --with-ai       # also regenerate Claude summaries/predictions
python -m fifa.fetch --mock          # force bundled mock data (no network)
python -m fifa.fetch --force-squads  # ignore the squad TTL this run
```
