
"""Define comment and reply endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services.auth import get_current_user

# Group comment operations under the /posts URL prefix.
router = APIRouter(prefix="/posts", tags=["Comments"])


def serialize_comment(comment: Comment) -> CommentResponse:
    """Return comment details while hiding soft-deleted content."""

    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        author_id=comment.author_id,
        parent_id=comment.parent_id,
        content="[Deleted]" if comment.is_deleted else comment.content,
        is_deleted=comment.is_deleted,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Create a comment or reply on an existing post."""

    post = database.get(Post, post_id)

    if post is None or post.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    # Replies must reference a comment belonging to the same post.
    if comment_data.parent_id is not None:
        parent = database.get(Comment, comment_data.parent_id)

        if parent is None or parent.post_id != post_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found.",
            )

    # Determine authorship from the authenticated user.
    comment = Comment(
        post_id=post_id,
        author_id=current_user.id,
        parent_id=comment_data.parent_id,
        content=comment_data.content,
    )

    database.add(comment)
    database.commit()
    database.refresh(comment)

    return serialize_comment(comment)


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentResponse],
)
def list_comments(
    post_id: int,
    database: Session = Depends(get_db),
):
    """Return comments and replies in chronological order."""

    post = database.get(Post, post_id)

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found.",
        )

    # Preserve deleted comments and replies in their original positions.
    comments = (
        database.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at, Comment.id)
        .all()
    )

    return [serialize_comment(comment) for comment in comments]


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    comment_id: int,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Allow an author to edit their own comment or reply."""

    comment = database.get(Comment, comment_id)

    if comment is None or comment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )

    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot edit another user's comment.",
        )

    comment.content = comment_data.content

    database.commit()
    database.refresh(comment)

    return serialize_comment(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Soft-delete a comment while preserving its replies."""

    comment = database.get(Comment, comment_id)

    if comment is None or comment.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found.",
        )

    if comment.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete another user's comment.",
        )

    # Preserve the comment record and its reply relationships.
    comment.is_deleted = True
    database.commit()
