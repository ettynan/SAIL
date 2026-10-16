"""Database tests for SAIL Orbit post reactions.

These tests verify the PostgreSQL reaction schema, constraints,
indexes, and the soft-deletion column added to posts.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.extensions import SessionLocal
from app.schemas.reaction import ReactionCounts, ReactionCreate


def test_reactions_table_and_columns():
    """Verify that the reactions table has the required columns."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        assert inspector.has_table("reactions")

        columns = {
            column["name"]: column for column in inspector.get_columns("reactions")
        }

        assert set(columns) == {
            "id",
            "user_id",
            "post_id",
            "reaction_type",
            "created_at",
        }

        assert columns["user_id"]["nullable"] is False
        assert columns["post_id"]["nullable"] is False
        assert columns["reaction_type"]["nullable"] is False


def test_reaction_unique_constraint():
    """Verify that each user can react only once per post."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        constraints = inspector.get_unique_constraints("reactions")

        assert any(
            constraint["name"] == "uq_reaction_user_post"
            and set(constraint["column_names"]) == {"user_id", "post_id"}
            for constraint in constraints
        )


def test_reaction_type_constraint():
    """Verify that only like and dislike reactions are permitted."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        constraints = inspector.get_check_constraints("reactions")

        assert any(
            constraint["name"] == "ck_reaction_type"
            and "'like'" in constraint["sqltext"]
            and "'dislike'" in constraint["sqltext"]
            for constraint in constraints
        )


def test_reaction_foreign_keys():
    """Verify that reactions reference users and posts."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        foreign_keys = {
            tuple(fk["constrained_columns"]): (
                fk["referred_table"],
                tuple(fk["referred_columns"]),
            )
            for fk in inspector.get_foreign_keys("reactions")
        }

        assert foreign_keys[("user_id",)] == ("users", ("id",))
        assert foreign_keys[("post_id",)] == ("posts", ("id",))


def test_reaction_indexes():
    """Verify indexes exist for reaction lookups."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        indexes = {
            tuple(index["column_names"]) for index in inspector.get_indexes("reactions")
        }

        assert ("user_id",) in indexes
        assert ("post_id",) in indexes


def test_reaction_foreign_keys_do_not_cascade():
    """Verify that reaction relationships do not cascade deletions."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        for foreign_key in inspector.get_foreign_keys("reactions"):
            options = foreign_key.get("options") or {}
            assert options.get("ondelete", "").upper() != "CASCADE"


def test_posts_soft_deletion_column():
    """Verify that posts have a non-nullable soft-deletion column."""

    with SessionLocal() as database:
        inspector = inspect(database.get_bind())

        columns = {column["name"]: column for column in inspector.get_columns("posts")}

        assert "is_deleted" in columns
        assert columns["is_deleted"]["nullable"] is False
        assert columns["is_deleted"]["default"] is not None


@pytest.mark.parametrize("reaction_type", ["like", "dislike"])
def test_reaction_accepts_valid_types(reaction_type):
    """Verify that like and dislike are accepted reaction types."""

    reaction = ReactionCreate(reaction_type=reaction_type)

    assert reaction.reaction_type == reaction_type


@pytest.mark.parametrize("reaction_type", ["love", "neutral", "", "LIKE"])
def test_reaction_rejects_invalid_types(reaction_type):
    """Verify that unsupported reaction types are rejected."""

    with pytest.raises(ValidationError):
        ReactionCreate(reaction_type=reaction_type)


def test_reaction_requires_type():
    """Verify that a reaction cannot be created without a type."""

    with pytest.raises(ValidationError):
        ReactionCreate()


def test_reaction_counts():
    """Verify that like and dislike counts are represented separately."""

    counts = ReactionCounts(likes=5, dislikes=2)

    assert counts.likes == 5
    assert counts.dislikes == 2
