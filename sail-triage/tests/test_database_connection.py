"""Verify Triage can connect to the configured database."""

from sqlalchemy import text

from app.extensions import engine


def test_database_connection():
    """Connect to PostgreSQL and return the current database user."""

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_user, current_database();")
        )

        return result.fetchone()


if __name__ == "__main__":
    print(test_database_connection())