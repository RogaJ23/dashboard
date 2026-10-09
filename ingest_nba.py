"""Load upcoming NBA games into Postgres.

The database side is done. You still need to pick a data provider and implement
fetch_upcoming_games(). Before choosing one, check its free-tier limits and terms
of use (especially if the dashboard will be public).

fetch_upcoming_games() must return a list of dicts shaped like:
    {"id": "...", "starts_at": datetime/ISO string,
     "home_team": "...", "away_team": "...", "status": "scheduled"}
"""
from sqlalchemy import text

from db import get_engine, log_sync


def fetch_upcoming_games():
    raise NotImplementedError("Pick an NBA data provider and implement this.")


def main():
    engine = get_engine()
    try:
        games = fetch_upcoming_games()
        with engine.begin() as conn:
            for g in games:
                conn.execute(
                    text(
                        """
                        INSERT INTO games (id, starts_at, home_team, away_team, status)
                        VALUES (:id, :starts_at, :home_team, :away_team, :status)
                        ON CONFLICT (id) DO UPDATE
                        SET starts_at = EXCLUDED.starts_at, status = EXCLUDED.status
                        """
                    ),
                    g,
                )
        log_sync(engine, "nba", len(games))
        print(f"NBA: upserted {len(games)} games.")
    except Exception as exc:
        log_sync(engine, "nba", 0, str(exc))
        raise


if __name__ == "__main__":
    main()
