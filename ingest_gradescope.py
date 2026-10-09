"""Pull your courses and assignments from Gradescope (unofficial, scraper-based).

Gradescope has no public API, so this uses the unofficial `gradescopeapi` library,
which logs in with your email and password. Only use it with YOUR OWN account, and
read Gradescope's terms of service first. If your school uses SSO login, this may
not work.

NOTE: the attribute/method names below are from memory of the library. Check them
against the gradescopeapi README for the version you install and adjust.
"""
import os

from gradescopeapi.classes.connection import GSConnection
from sqlalchemy import text

from db import get_engine, log_sync


def fetch():
    conn = GSConnection()
    conn.login(os.environ["GRADESCOPE_EMAIL"], os.environ["GRADESCOPE_PASSWORD"])
    courses = conn.account.get_courses().get("student", {})
    rows = []
    for course_id, course in courses.items():
        assignments = conn.account.get_assignments(course_id)
        rows.append((course_id, course, assignments))
    return rows


def main():
    engine = get_engine()
    seen = 0
    try:
        with engine.begin() as db:
            for course_id, course, assignments in fetch():
                db.execute(
                    text(
                        """
                        INSERT INTO courses (id, name, term)
                        VALUES (:id, :name, :term)
                        ON CONFLICT (id) DO UPDATE
                        SET name = EXCLUDED.name, term = EXCLUDED.term
                        """
                    ),
                    {
                        "id": str(course_id),
                        "name": getattr(course, "name", str(course_id)),
                        "term": str(getattr(course, "semester", "") or ""),
                    },
                )
                for a in assignments:
                    db.execute(
                        text(
                            """
                            INSERT INTO assignments (id, course_id, title, due_at, status)
                            VALUES (:id, :course_id, :title, :due_at, :status)
                            ON CONFLICT (id) DO UPDATE
                            SET title = EXCLUDED.title,
                                due_at = EXCLUDED.due_at,
                                status = EXCLUDED.status
                            """
                        ),
                        {
                            "id": f"{course_id}:{getattr(a, 'assignment_id', '')}",
                            "course_id": str(course_id),
                            "title": getattr(a, "name", "Untitled"),
                            "due_at": getattr(a, "due_date", None),
                            "status": str(getattr(a, "submissions_status", "") or ""),
                        },
                    )
                    seen += 1
        log_sync(engine, "gradescope", seen)
        print(f"Gradescope: upserted {seen} assignments.")
    except Exception as exc:
        log_sync(engine, "gradescope", 0, str(exc))
        raise


if __name__ == "__main__":
    main()
