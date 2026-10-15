
"""Define post creation, retrieval, editing, and deletion endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostUpdate, PostResponse
from app.services.auth import get_current_user

# Group post operations under the /posts URL prefix.
router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Create a post belonging to the authenticated user."""

    # The author is determined by the authenticated access token rather
    # than accepting an author ID supplied by the client.
    post = Post(
        author_id=current_user.id,
        content=post_data.content,
    )

    # Save the post and reload database-generated values.
    database.add(post)
    database.commit()
    database.refresh(post)

    return post


@router.get("", response_model=list[PostResponse])
def list_posts(
    database: Session = Depends(get_db),
):
    """Return posts ordered from newest to oldest."""

    # Order by creation time and use the post ID to break timestamp ties.
    return (
        database.query(Post)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .all()
    )


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    database: Session = Depends(get_db),
):
    """Retrieve a post by its database ID."""

    post = database.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    return post


@router.patch("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Allow a post's author to edit its content."""

    post = database.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    # Prevent users from modifying posts belonging to other accounts.
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot edit another user's post.",
        )

    # PostUpdate validates the replacement content before it is saved.
    post.content = post_data.content

    database.commit()
    database.refresh(post)

    return post


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Allow a post's author to delete their post."""

    post = database.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    # Only the account that created the post may delete it.
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete another user's post.",
        )

    database.delete(post)
    database.commit()
