
"""Post database model for SAIL Orbit."""

from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base
if TYPE_CHECKING:
    from app.models.user import User


class Post(Base):
    """Represent a post created by a SAIL Orbit user."""

    # Name of the PostgreSQL table represented by this model.
    __tablename__ = "posts"

    # Primary key used internally to uniquely identify each post.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Associate each post with the user who created it.
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Store the text content of the post.
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Record when the post was created and most recently updated.
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

    # Allow SQLAlchemy to access the user who authored the post.
    author: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
    )
