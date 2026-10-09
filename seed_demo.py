"""Fill the database with fake data for the public demo.

WIPES ALL TABLES. Point DATABASE_URL at your DEMO database (never your real one)
and set DEMO_MODE=true.
"""
import os
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from db import get_engine, init_schema

if os.getenv("DEMO_MODE", "").lower() != "true":
    raise SystemExit("Refusing to seed: set DEMO_MODE=true (this wipes all tables).")

random.seed(7)
now = datetime.now(timezone.utc)
engine = get_engine()
init_schema(engine)

COURSES = [
    ("c1", "CS 61B: Data Structures"),
    ("c2", "STAT 134: Probability"),
    ("c3", "ENGLISH R1B: Reading and Composition"),
]
ARTISTS = ["Demo Artist A", "Demo Artist B", "Demo Artist C", "Demo Artist D", "Demo Artist E"]
TEAMS = ["Warriors", "Lakers", "Celtics", "Nuggets", "Knicks", "Suns", "Bucks", "Heat"]

with engine.begin() as conn:
    conn.exec_driver_sql(
        "TRUNCATE plays, tracks, assignments, courses, games, tasks, sync_runs "
        "RESTART IDENTITY CASCADE"
    )

    for cid, name in COURSES:
        conn.execute(
            text("INSERT INTO courses (id, name, term) VALUES (:i, :n, 'Demo Term')"),
            {"i": cid, "n": name},
        )
        for n in range(1, 9):
            due = now + timedelta(days=random.randint(-21, 21), hours=random.randint(0, 23))
            conn.execute(
                text(
                    "INSERT INTO assignments (id, course_id, title, due_at, status) "
                    "VALUES (:id, :c, :t, :d, :s)"
                ),
                {
                    "id": f"{cid}:{n}",
                    "c": cid,
                    "t": f"Assignment {n}",
                    "d": due,
                    "s": "Submitted" if due < now else "Not submitted",
                },
            )

    track_ids = []
    for i in range(20):
        tid = f"demo-track-{i}"
        track_ids.append(tid)
        conn.execute(
            text(
                "INSERT INTO tracks (id, name, artist, album, duration_ms) "
                "VALUES (:id, :n, :a, 'Demo Album', 200000)"
            ),
            {"id": tid, "n": f"Demo Track {i}", "a": random.choice(ARTISTS)},
        )

    for _ in range(500):
        played = now - timedelta(seconds=random.randint(0, 45 * 24 * 3600))
        conn.execute(
            text(
                "INSERT INTO plays (track_id, played_at) VALUES (:t, :p) "
                "ON CONFLICT DO NOTHING"
            ),
            {"t": random.choice(track_ids), "p": played},
        )

    for i in range(6):
        home, away = random.sample(TEAMS, 2)
        conn.execute(
            text(
                "INSERT INTO games (id, starts_at, home_team, away_team, status) "
                "VALUES (:id, :s, :h, :a, 'scheduled')"
            ),
            {"id": f"demo-game-{i}", "s": now + timedelta(days=i + 1, hours=2), "h": home, "a": away},
        )

    for title in ["Finish problem set", "Email advisor", "Laundry", "Apply to internships"]:
        conn.execute(text("INSERT INTO tasks (title) VALUES (:t)"), {"t": title})

print("Demo data seeded.")
