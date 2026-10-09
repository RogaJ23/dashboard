"""Streamlit dashboard. Run with: streamlit run app.py"""
import os

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
