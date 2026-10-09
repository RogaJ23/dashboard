-- Run once via `python db.py`. Safe to re-run.

CREATE TABLE IF NOT EXISTS courses (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    term        TEXT
);

CREATE TABLE IF NOT EXISTS assignments (
    id          TEXT PRIMARY KEY,              -- "<course_id>:<assignment_id>"
    course_id   TEXT REFERENCES courses(id),
    title       TEXT NOT NULL,
    due_at      TIMESTAMPTZ,
    status      TEXT
);

CREATE TABLE IF NOT EXISTS tracks (
    id          TEXT PRIMARY KEY,              -- Spotify track id
    name        TEXT NOT NULL,
    artist      TEXT NOT NULL,
    album       TEXT,
    duration_ms INTEGER
);

-- Composite key = the dedupe rule: the same play is never stored twice.
CREATE TABLE IF NOT EXISTS plays (
    track_id    TEXT REFERENCES tracks(id),
    played_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (track_id, played_at)
);

CREATE TABLE IF NOT EXISTS games (
    id          TEXT PRIMARY KEY,
    starts_at   TIMESTAMPTZ NOT NULL,
    home_team   TEXT NOT NULL,
    away_team   TEXT NOT NULL,
    status      TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    due_at      TIMESTAMPTZ,
    done        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL,                 -- 'spotify' | 'gradescope' | 'nba'
    ran_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    rows_seen   INTEGER NOT NULL DEFAULT 0,
    error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_plays_played_at ON plays (played_at);
CREATE INDEX IF NOT EXISTS idx_assignments_due ON assignments (due_at);
