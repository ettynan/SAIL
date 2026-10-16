"""Database tests for SAIL Orbit comments and replies.

These tests verify the PostgreSQL schema, foreign keys, indexes,
and deletion constraints created by the comments migration.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.extensions import SessionLocal
from app.schemas.comment import CommentCreate, CommentUpdate


def test_comments_table_and_columns():
    """Verify that the comments table has the required columns."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        assert inspector.has_table("comments")

        columns = {
            column["name"]: column for column in inspector.get_columns("comments")
        }

        assert set(columns) == {
            "id",
            "post_id",
            "author_id",
            "parent_id",
            "content",
            "created_at",
            "updated_at",
            "is_deleted",
        }

        assert columns["parent_id"]["nullable"] is True
        assert columns["is_deleted"]["nullable"] is False
        assert columns["post_id"]["nullable"] is False
        assert columns["author_id"]["nullable"] is False
        assert columns["content"]["nullable"] is False


def test_comment_foreign_keys():
    """Verify that comments reference posts, authors, and parent comments."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        foreign_keys = {
            tuple(fk["constrained_columns"]): (
                fk["referred_table"],
                tuple(fk["referred_columns"]),
            )
            for fk in inspector.get_foreign_keys("comments")
        }

        assert foreign_keys[("post_id",)] == ("posts", ("id",))
        assert foreign_keys[("author_id",)] == ("users", ("id",))
        assert foreign_keys[("parent_id",)] == ("comments", ("id",))


def test_comment_indexes():
    """Verify indexes exist for post, author, and parent lookups."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        indexes = {
            tuple(index["column_names"]) for index in inspector.get_indexes("comments")
        }

        assert ("post_id",) in indexes
        assert ("author_id",) in indexes
        assert ("parent_id",) in indexes


def test_comment_foreign_keys_do_not_cascade():
    """Verify that comment relationships do not cascade deletions."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        for foreign_key in inspector.get_foreign_keys("comments"):
            options = foreign_key.get("options") or {}
            assert options.get("ondelete", "").upper() != "CASCADE"


def test_create_comment_with_valid_content():
    """Verify that valid comment content is accepted."""

    comment = CommentCreate(content="My first Orbit comment.")

    assert comment.content == "My first Orbit comment."
    assert comment.parent_id is None


def test_create_reply_with_parent_id():
    """Verify that a reply can reference an existing comment ID."""

    reply = CommentCreate(content="This is a reply.", parent_id=12)

    assert reply.content == "This is a reply."
    assert reply.parent_id == 12


def test_comment_content_trims_whitespace():
    """Verify that surrounding whitespace is removed from comment content."""

    comment = CommentCreate(content="  Hello Orbit!  ")
    update = CommentUpdate(content="  Updated comment.  ")

    assert comment.content == "Hello Orbit!"
    assert update.content == "Updated comment."


@pytest.mark.parametrize("content", ["", "   ", "\n\t", "x" * 5001])
def test_comment_rejects_invalid_content(content):
    """Verify that empty, whitespace-only, and oversized comments are rejected."""

    with pytest.raises(ValidationError):
        CommentCreate(content=content)

    with pytest.raises(ValidationError):
        CommentUpdate(content=content)


@pytest.mark.parametrize("parent_id", [0, -1])
def test_comment_rejects_invalid_parent_id(parent_id):
    """Verify that reply parent IDs must be positive integers."""

    with pytest.raises(ValidationError):
        CommentCreate(content="Test reply.", parent_id=parent_id)


def test_comment_accepts_maximum_length():
    """Verify that comments containing exactly 5,000 characters are accepted."""

    comment = CommentCreate(content="x" * 5000)

    assert len(comment.content) == 5000
