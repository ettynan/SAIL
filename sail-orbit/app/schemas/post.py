
"""Pydantic schemas for SAIL Orbit posts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PostContent(BaseModel):
    """Define and validate content shared by post creation and editing."""

    # Require post content between 1 and 5,000 characters.
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Reject whitespace-only posts and remove surrounding whitespace."""
        value = value.strip()

        if not value:
            raise ValueError("Post content cannot be empty or whitespace-only.")

        return value


class PostCreate(PostContent):
    """Validate the content supplied when creating a post."""


class PostUpdate(PostContent):
    """Validate replacement content when editing an existing post."""


class PostResponse(BaseModel):
    """Define the post information returned by the API."""

    # Read attributes directly from SQLAlchemy Post instances.
    model_config = ConfigDict(from_attributes=True)

    # Identify the post and its author.
    id: int
    author_id: int

    # Include the post content and timestamps.
    content: str
    created_at: datetime
    updated_at: datetime
