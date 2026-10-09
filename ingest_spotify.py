"""Pull recently played tracks from Spotify into Postgres.

Spotify only returns your most recent plays, so history only grows if this runs
on a schedule. Duplicates are skipped via the (track_id, played_at) primary key.

BEFORE YOU BUILD ON THIS: confirm the recently-played endpoint is still available
to Development Mode apps in Spotify's current migration guide / endpoint list.

First run opens a browser for OAuth. Needs SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET,
SPOTIPY_REDIRECT_URI in .env.

TODO (weekend 2): to run unattended in GitHub Actions, store a refresh token as a
secret instead of relying on the local browser flow / token cache.
"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sqlalchemy import text

from db import get_engine, log_sync


def fetch_recent():
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(scope="user-read-recently-played")
    )
    return sp.current_user_recently_played(limit=50)["items"]


def main():
    engine = get_engine()
    try:
        items = fetch_recent()
        with engine.begin() as conn:
            for item in items:
                t = item["track"]
                conn.execute(
                    text(
                        """
                        INSERT INTO tracks (id, name, artist, album, duration_ms)
                        VALUES (:id, :name, :artist, :album, :duration_ms)
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "artist": t["artists"][0]["name"],
                        "album": t["album"]["name"],
                        "duration_ms": t["duration_ms"],
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO plays (track_id, played_at)
                        VALUES (:track_id, :played_at)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"track_id": t["id"], "played_at": item["played_at"]},
                )
        log_sync(engine, "spotify", len(items))
        print(f"Spotify: processed {len(items)} plays.")
    except Exception as exc:
        log_sync(engine, "spotify", 0, str(exc))
        raise


if __name__ == "__main__":
    main()
