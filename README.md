# Personal Dashboard

One place for my assignments, listening history, upcoming NBA games, and to-dos.
Python + Postgres + Streamlit.

**Live demo (sample data):** _add link after deploying_

## What it does
- **Assignments:** pulls courses and due dates from Gradescope.
- **Listening:** stores Spotify play history over time and charts it.
- **NBA:** shows upcoming games.
- **Tasks:** a simple to-do list backed by the same database.
- **Insights:** joins deadlines with listening activity by week.

## Architecture
```
Spotify / Gradescope / NBA source -> ingestion scripts -> Postgres -> Streamlit
```
Each ingestion script is rerunnable and logs to `sync_runs`. Plays are deduplicated
on `(track_id, played_at)`.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill it in
python db.py                # create tables
python ingest_spotify.py
python ingest_gradescope.py
streamlit run app.py
```

### Demo mode
Point `DATABASE_URL` at a separate demo database, set `DEMO_MODE=true`, then
`python seed_demo.py` and deploy. Never seed your real database.

## Tradeoffs and limitations
- Gradescope has no public API, so this uses an unofficial scraper with my own
  credentials. It is personal-use only and not offered to other users.
- Spotify's Development Mode limits apps to a handful of users, so the live data
  version is single-user. The public site runs on sample data.

## Roadmap
- [ ] Scheduled ingestion with GitHub Actions
- [ ] NBA data provider
- [ ] Tests for dedupe logic
