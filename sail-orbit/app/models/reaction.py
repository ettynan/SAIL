"""Reaction model supporting likes and dislikes on posts."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Reaction(Base):
    """Store one like or dislike per user per post."""

    __tablename__ = "reactions"

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_reaction_user_post"),
        CheckConstraint(
            "reaction_type IN ('like', 'dislike')",
            name="ck_reaction_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), index=True)
    reaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Associate each reaction with its user and post.
    user: Mapped["User"] = relationship(back_populates="reactions")
    post: Mapped["Post"] = relationship(back_populates="reactions")
