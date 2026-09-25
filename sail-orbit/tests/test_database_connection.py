"""Verify Orbit can connect to the configured database."""

from sqlalchemy import text

from app.extensions import engine


def test_database_connection():
    """Verify that Orbit can connect to the configured PostgreSQL database."""

    with engine.connect() as connection:
        result = connection.execute(text("SELECT current_user, current_database();"))
        row = result.fetchone()

    # A returned row confirms that PostgreSQL accepted the connection and
    # successfully executed the query.
    assert row is not None


if __name__ == "__main__":
    print(test_database_connection())
