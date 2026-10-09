"""Shared database helpers. Run `python db.py` once to create the tables."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def get_engine():
    url = os.environ["DATABASE_URL"]
    # Neon/Supabase give postgres:// or postgresql:// URLs; SQLAlchemy needs a driver.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return create_engine(url, pool_pre_ping=True)


def init_schema(engine):
    sql = Path(__file__).with_name("schema.sql").read_text()
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)


def log_sync(engine, source, rows_seen, error=None):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO sync_runs (source, rows_seen, error) "
                "VALUES (:source, :rows_seen, :error)"
            ),
            {"source": source, "rows_seen": rows_seen, "error": error},
        )


if __name__ == "__main__":
    init_schema(get_engine())
    print("Schema ready.")
