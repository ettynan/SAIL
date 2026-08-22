"""User database model for Triage."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class User(Base):
    """Represent a Triage user account."""

    # Name of the PostgreSQL table represented by this model.
    __tablename__ = "users"

    # Primary key used internally to uniquely identify each user.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Account identity fields. Usernames and email addresses must be unique.
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # Store the password hash rather than the user's actual password.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Public profile information.
    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Control account permissions and whether the account can be used.
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Record when the account is created and most recently updated.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )