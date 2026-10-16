
"""Pydantic schemas for SAIL Orbit post reactions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReactionCreate(BaseModel):
    """Validate a like or dislike submitted for a post."""

    # Restrict reactions to the two supported values.
    reaction_type: Literal["like", "dislike"]


class ReactionResponse(BaseModel):
    """Define the reaction information returned by the API."""

    # Read attributes directly from SQLAlchemy Reaction instances.
    model_config = ConfigDict(from_attributes=True)

    # Identify the reaction, its owner, and its post.
    id: int
    user_id: int
    post_id: int

    # Include the reaction type and creation timestamp.
    reaction_type: Literal["like", "dislike"]
    created_at: datetime


class ReactionCounts(BaseModel):
    """Report the separate like and dislike totals for a post."""

    likes: int
    dislikes: int
