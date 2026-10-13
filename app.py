"""Streamlit dashboard. Run with: streamlit run app.py"""
import os
import re
from datetime import datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine

st.set_page_config(page_title="My Dashboard", layout="wide")

DEMO = os.getenv("DEMO_MODE", "").lower() == "true"
TZ = os.getenv("TZ_NAME", "America/Los_Angeles")


@st.cache_resource
def engine():
    return get_engine()


@st.cache_data(ttl=60)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    p = {"tz": TZ, **(params or {})}
    return pd.read_sql(text(sql), engine(), params=p)


st.title("My Dashboard")
if DEMO:
    st.info("Demo mode: showing sample data. Writes are disabled.")

tab_assign, tab_music, tab_nba, tab_tasks, tab_insights = st.tabs(
    ["Assignments", "Listening", "NBA", "Tasks", "Insights"]
)

# ---------------------------------------------------------------- Assignments
with tab_assign:
    due_soon = query(
        """
        SELECT count(*) AS n FROM assignments
        WHERE due_at BETWEEN now() AND now() + interval '7 days'
        """
    )
    st.metric("Due in the next 7 days", int(due_soon["n"][0]))

    upcoming = query(
        """
        SELECT c.name AS course, a.title, a.status,
               (a.due_at AT TIME ZONE :tz) AS due
        FROM assignments a JOIN courses c ON c.id = a.course_id
        WHERE a.due_at >= now()
        ORDER BY a.due_at LIMIT 50
        """
    )
    st.dataframe(upcoming, use_container_width=True, hide_index=True)

    # ---- Manual deadlines (for courses with no API or calendar feed) ----
    st.divider()
    st.subheader("Add a deadline manually")

    existing_courses = pd.read_sql(
        text("SELECT id, name FROM courses WHERE id LIKE 'manual:%' ORDER BY name"),
        engine(),
    )
    NEW_COURSE = "+ New course"
    course_options = list(existing_courses["name"]) + [NEW_COURSE]

    with st.form("add_assignment", clear_on_submit=True):
        choice = st.selectbox("Course", course_options)
        new_course_name = st.text_input("New course name (only if you picked + New course)")
        a_title = st.text_input("Assignment")
        a_date = st.date_input("Due date", value=None)
        a_time = st.time_input("Due time", value=time(23, 59))
        add_clicked = st.form_submit_button("Add deadline", disabled=DEMO)

    if add_clicked:
        course_name = new_course_name.strip() if choice == NEW_COURSE else choice
        if not course_name or not a_title.strip() or a_date is None:
            st.warning("Course, assignment, and due date are required.")
        else:
            course_id = "manual:" + re.sub(r"[^a-z0-9]+", "-", course_name.lower()).strip("-")
            due_at = datetime.combine(a_date, a_time).replace(tzinfo=ZoneInfo(TZ))
            with engine().begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO courses (id, name, term) VALUES (:i, :n, 'Manual') "
                        "ON CONFLICT (id) DO NOTHING"
                    ),
                    {"i": course_id, "n": course_name},
                )
                conn.execute(
                    text(
                        "INSERT INTO assignments (id, course_id, title, due_at, status) "
                        "VALUES (:id, :c, :t, :d, 'Not submitted')"
                    ),
                    {
                        "id": f"{course_id}:{uuid4().hex[:8]}",
                        "c": course_id,
                        "t": a_title.strip(),
                        "d": due_at,
                    },
                )
            st.cache_data.clear()
            st.rerun()

    manual = pd.read_sql(
        text(
            """
            SELECT a.id, c.name AS course, a.title, a.status,
                   (a.due_at AT TIME ZONE :tz) AS due
            FROM assignments a JOIN courses c ON c.id = a.course_id
            WHERE a.id LIKE 'manual:%'
            ORDER BY a.due_at DESC LIMIT 30
            """
        ),
        engine(),
        params={"tz": TZ},
    )
    if not manual.empty:
        st.caption("Your manual deadlines")
        for _, r in manual.iterrows():
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write(f"{r['course']}: {r['title']} (due {r['due']:%b %d, %I:%M %p}) - {r['status']}")
            if c2.button("Done", key=f"adone_{r['id']}", disabled=DEMO):
                with engine().begin() as conn:
                    conn.execute(
                        text("UPDATE assignments SET status = 'Submitted' WHERE id = :i"),
                        {"i": r["id"]},
                    )
                st.cache_data.clear()
                st.rerun()
            if c3.button("Delete", key=f"adel_{r['id']}", disabled=DEMO):
                with engine().begin() as conn:
                    conn.execute(
                        text("DELETE FROM assignments WHERE id = :i"),
                        {"i": r["id"]},
                    )
                st.cache_data.clear()
                st.rerun()

# ------------------------------------------------------------------ Listening
with tab_music:
    left, right = st.columns(2)

    top_artists = query(
        """
        SELECT t.artist, count(*) AS plays
        FROM plays p JOIN tracks t ON t.id = p.track_id
        WHERE p.played_at >= now() - interval '30 days'
        GROUP BY t.artist ORDER BY plays DESC LIMIT 10
        """
    )
    left.subheader("Top artists (30 days)")
    left.bar_chart(top_artists.set_index("artist"))

    per_day = query(
        """
        SELECT date_trunc('day', played_at AT TIME ZONE :tz)::date AS day,
               count(*) AS plays
        FROM plays GROUP BY 1 ORDER BY 1
        """
    )
    right.subheader("Plays per day")
    right.line_chart(per_day.set_index("day"))

    by_hour = query(
        """
        SELECT extract(hour FROM played_at AT TIME ZONE :tz)::int AS hour,
               count(*) AS plays
        FROM plays GROUP BY 1 ORDER BY 1
        """
    )
    st.subheader("Listening by hour of day")
    st.bar_chart(by_hour.set_index("hour"))

# ------------------------------------------------------------------------ NBA
with tab_nba:
    games = query(
        """
        SELECT (starts_at AT TIME ZONE :tz) AS tipoff,
               away_team AS away, home_team AS home, status
        FROM games WHERE starts_at >= now() ORDER BY starts_at LIMIT 20
        """
    )
    if games.empty:
        st.write("No games loaded yet. Implement `ingest_nba.py` to fill this in.")
    else:
        st.dataframe(games, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------- Tasks
with tab_tasks:
    with st.form("add_task", clear_on_submit=True):
        title = st.text_input("New task")
        due = st.date_input("Due (optional)", value=None)
        submitted = st.form_submit_button("Add", disabled=DEMO)
    if submitted and title.strip():
        with engine().begin() as conn:
            conn.execute(
                text("INSERT INTO tasks (title, due_at) VALUES (:t, :d)"),
                {"t": title.strip(), "d": due},
            )
        st.rerun()

    open_tasks = pd.read_sql(
        text(
            "SELECT id, title, due_at FROM tasks WHERE NOT done "
            "ORDER BY due_at NULLS LAST, created_at"
        ),
        engine(),
    )
    for _, row in open_tasks.iterrows():
        c1, c2 = st.columns([6, 1])
        due_txt = f" (due {row['due_at']:%b %d})" if pd.notna(row["due_at"]) else ""
        c1.write(f"{row['title']}{due_txt}")
        if c2.button("Done", key=f"done_{row['id']}", disabled=DEMO):
            with engine().begin() as conn:
                conn.execute(
                    text("UPDATE tasks SET done = TRUE WHERE id = :i"),
                    {"i": int(row["id"])},
                )
            st.rerun()

# ------------------------------------------------------------------- Insights
with tab_insights:
    st.subheader("Deadlines vs. listening, by week")
    weekly = query(
        """
        WITH weeks AS (
            SELECT generate_series(
                date_trunc('week', now() - interval '8 weeks'),
                date_trunc('week', now()),
                interval '1 week') AS wk
        )
        SELECT w.wk::date AS week,
               (SELECT count(*) FROM assignments a
                 WHERE date_trunc('week', a.due_at) = w.wk) AS assignments_due,
               (SELECT count(*) FROM plays p
                 WHERE date_trunc('week', p.played_at) = w.wk) AS plays
        FROM weeks w ORDER BY w.wk
        """
    ).set_index("week")
    a, b = st.columns(2)
    a.caption("Assignments due")
    a.bar_chart(weekly[["assignments_due"]])
    b.caption("Plays")
    b.line_chart(weekly[["plays"]])

    st.subheader("Last sync per source")
    st.dataframe(
        query(
            "SELECT DISTINCT ON (source) source, ran_at, rows_seen, error "
            "FROM sync_runs ORDER BY source, ran_at DESC"
        ),
        use_container_width=True,
        hide_index=True,
    )