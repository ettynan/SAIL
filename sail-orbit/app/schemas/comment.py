
"""Pydantic schemas for SAIL Orbit comments and replies."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommentContent(BaseModel):
    """Define and validate content shared by comment creation and editing."""

    # Require comment content between 1 and 5,000 characters.
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Reject whitespace-only comments and remove surrounding whitespace."""
        value = value.strip()

        if not value:
            raise ValueError("Comment content cannot be empty or whitespace-only.")

        return value


class CommentCreate(CommentContent):
    """Validate content and an optional parent when creating a comment."""

    # A parent ID identifies the comment being replied to.
    # None indicates a top-level comment.
    parent_id: int | None = Field(default=None, gt=0)


class CommentUpdate(CommentContent):
    """Validate replacement content when editing a comment or reply."""


class CommentResponse(BaseModel):
    """Define the comment information returned by the API."""

    # Read attributes directly from SQLAlchemy Comment instances.
    model_config = ConfigDict(from_attributes=True)

    # Identify the comment, its post, author, and optional parent.
    id: int
    post_id: int
    author_id: int
    parent_id: int | None

    # Include content, deletion status, and timestamps.
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
