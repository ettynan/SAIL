
"""Define post Like/Dislike reaction endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.user import User
from app.schemas.reaction import ReactionCounts, ReactionCreate, ReactionResponse
from app.services.auth import get_current_user

# Group reaction operations under the /posts URL prefix.
router = APIRouter(prefix="/posts", tags=["Reactions"])


@router.put(
    "/{post_id}/reaction",
    response_model=ReactionResponse | None,
)
def set_reaction(
    post_id: int,
    reaction_data: ReactionCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Add, switch, or remove the current user's reaction to a post."""

    post = database.get(Post, post_id)

    if post is None or post.is_deleted:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    # Find the authenticated user's existing reaction, if any.
    reaction = (
        database.query(Reaction)
        .filter(
            Reaction.post_id == post_id,
            Reaction.user_id == current_user.id,
        )
        .first()
    )

    if reaction is None:
        # Add a reaction when the user has not reacted previously.
        reaction = Reaction(
            post_id=post_id,
            user_id=current_user.id,
            reaction_type=reaction_data.reaction_type,
        )
        database.add(reaction)

    elif reaction.reaction_type == reaction_data.reaction_type:
        # Selecting the same reaction again removes it.
        database.delete(reaction)
        database.commit()
        return None

    else:
        # Selecting the opposite reaction changes the existing reaction.
        reaction.reaction_type = reaction_data.reaction_type

    database.commit()
    database.refresh(reaction)

    return reaction


@router.get(
    "/{post_id}/reactions",
    response_model=ReactionCounts,
)
def get_reaction_counts(
    post_id: int,
    database: Session = Depends(get_db),
):
    """Return separate Like and Dislike counts for a post."""

    post = database.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=404,
            detail="Post not found.",
        )

    # Count reactions by type without retrieving every reaction record.
    counts = (
        database.query(Reaction.reaction_type, func.count(Reaction.id))
        .filter(Reaction.post_id == post_id)
        .group_by(Reaction.reaction_type)
        .all()
    )

    totals = dict(counts)

    return ReactionCounts(
        likes=totals.get("like", 0),
        dislikes=totals.get("dislike", 0),
    )
