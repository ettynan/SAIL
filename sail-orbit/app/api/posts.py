"""Define post creation, retrieval, editing, and deletion endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.post import Post
from app.models.user import User
from app.schemas.post import PostCreate, PostResponse, PostUpdate
from app.services.auth import get_current_user

# Group post operations under the /posts URL prefix.
router = APIRouter(prefix="/posts", tags=["Posts"])


def serialize_post(post: Post) -> PostResponse:
    """Return post details while hiding soft-deleted content."""

    return PostResponse(
        id=post.id,
        author_id=post.author_id,
        content="[Deleted]" if post.is_deleted else post.content,
        is_deleted=post.is_deleted,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


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

    # Determine authorship from the authenticated access token.
    post = Post(
        author_id=current_user.id,
        content=post_data.content,
    )

    database.add(post)
    database.commit()
    database.refresh(post)

    return serialize_post(post)


@router.get("", response_model=list[PostResponse])
def list_posts(
    database: Session = Depends(get_db),
):
    """Return posts ordered from newest to oldest."""

    # Include deleted posts to preserve their position in discussions.
    posts = database.query(Post).order_by(Post.created_at.desc(), Post.id.desc()).all()

    return [serialize_post(post) for post in posts]


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

    return serialize_post(post)


@router.patch("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Allow a post's author to edit its content."""

    post = database.get(Post, post_id)

    if post is None or post.is_deleted:
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

    post.content = post_data.content

    database.commit()
    database.refresh(post)

    return serialize_post(post)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Soft-delete a post while preserving its discussion history."""

    post = database.get(Post, post_id)

    if post is None or post.is_deleted:
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

    # Retain the post and its comments instead of removing database records.
    post.is_deleted = True
    database.commit()
