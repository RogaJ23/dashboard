#!/bin/bash
# Runs the Spotify sync every time, and the Gradescope sync at most once per day.
# Called by the macOS schedule (see install_schedule.sh). Safe to run by hand too.

cd "$(dirname "$0")" || exit 1
mkdir -p logs

if [ ! -f .venv/bin/activate ]; then
  echo "$(date '+%F %T') ERROR: .venv not found in $(pwd)" >> logs/sync.log
  exit 1
fi
source .venv/bin/activate

echo "=== $(date '+%F %T') sync start ===" >> logs/sync.log

# Spotify: every run (the API only returns your most recent plays)
python ingest_spotify.py >> logs/sync.log 2>&1 \
  || echo "$(date '+%F %T') Spotify sync FAILED" >> logs/sync.log

# Gradescope: once per calendar day, only marked done if it succeeded
TODAY="$(date +%F)"
if [ "$(cat .last_gradescope 2>/dev/null)" != "$TODAY" ]; then
  if python ingest_gradescope.py >> logs/sync.log 2>&1; then
    echo "$TODAY" > .last_gradescope
  else
    echo "$(date '+%F %T') Gradescope sync FAILED (will retry next run)" >> logs/sync.log
  fi
fi

echo "=== $(date '+%F %T') sync end ===" >> logs/sync.log
