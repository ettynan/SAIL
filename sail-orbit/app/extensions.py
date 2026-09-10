"""Configure database access for SAIL Orbit."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config


# Create the shared connection point between SQLAlchemy and PostgreSQL.
engine = create_engine(
    Config.DATABASE_URL,
    pool_pre_ping=True,
)

# Create database sessions used to execute queries and transactions.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """Provide a database session for one API request, then close it."""
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()