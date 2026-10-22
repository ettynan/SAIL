"""Integration tests for the SAIL Orbit comments API.

Verify comment creation, threaded replies, retrieval, editing, deletion,
authentication, and ownership through the actual FastAPI endpoints.

Database schema and Pydantic validation are tested in test_comments.py.
"""

import httpx2
import pytest
from sqlalchemy import delete, select, update

from app.extensions import SessionLocal
from app.models.comment import Comment
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.user import User
from run import app

# ---------------------------------------------------------------------------
# Test configuration
# ---------------------------------------------------------------------------

# Dedicated accounts keep integration tests separate from application data.
# Two users are required to verify comment ownership and permissions.
TEST_USERS = [
    {
        "username": "orbit_comment_author",
        "email": "orbit_comment_author@example.com",
        "password": "OrbitTest123!",
    },
    {
        "username": "orbit_comment_other",
        "email": "orbit_comment_other@example.com",
        "password": "OrbitTest123!",
    },
]


# ---------------------------------------------------------------------------
# Fixtures and database cleanup
# ---------------------------------------------------------------------------


def delete_test_users():
    """Remove test accounts and their associated posts and comments."""

    with SessionLocal() as db:
        users = db.scalars(
            select(User).where(User.username.in_([u["username"] for u in TEST_USERS]))
        ).all()

        user_ids = [user.id for user in users]

        if not user_ids:
            return

        post_ids = db.scalars(select(Post.id).where(Post.author_id.in_(user_ids))).all()

        # Break parent/reply relationships before removing comments.
        # This avoids foreign-key violations in nested discussions.
        if post_ids:
            db.execute(
                update(Comment)
                .where(Comment.post_id.in_(post_ids))
                .values(parent_id=None)
            )
            db.execute(delete(Comment).where(Comment.post_id.in_(post_ids)))

        # Remove any comments test users made on other posts.
        db.execute(delete(Comment).where(Comment.author_id.in_(user_ids)))

        # Reactions reference both users and posts.
        db.execute(delete(Reaction).where(Reaction.user_id.in_(user_ids)))

        if post_ids:
            db.execute(delete(Reaction).where(Reaction.post_id.in_(post_ids)))
            db.execute(delete(Post).where(Post.id.in_(post_ids)))

        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()


@pytest.fixture(autouse=True)
def clean_test_users():
    """Ensure each test begins and ends with a clean database state."""

    delete_test_users()
    yield
    delete_test_users()


@pytest.fixture
async def client():
    """Send requests directly through FastAPI without starting a server."""

    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Shared API helpers
# ---------------------------------------------------------------------------


async def register_and_login(client, index=0):
    """Register a test user and return their JWT authorization header."""

    account = TEST_USERS[index]

    registration = await client.post("/auth/register", json=account)
    assert registration.status_code == 201

    login = await client.post(
        "/auth/login",
        json={
            "username": account["username"],
            "password": account["password"],
        },
    )
    assert login.status_code == 200

    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def create_post(client, headers):
    """Create a post through the API and return its ID."""

    response = await client.post(
        "/posts",
        headers=headers,
        json={"content": "Comment integration test."},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_comment(client, headers, post_id, content, parent_id=None):
    """Create a comment or reply and return its serialized representation."""

    response = await client.post(
        f"/posts/{post_id}/comments",
        headers=headers,
        json={"content": content, "parent_id": parent_id},
    )
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------------------
# Comment creation and retrieval
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_comment(client):
    """Verify comment creation and PostgreSQL persistence."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    comment = await create_comment(client, headers, post_id, "First comment.")

    # A top-level comment belongs to the post and has no parent.
    assert comment["post_id"] == post_id
    assert comment["parent_id"] is None
    assert comment["content"] == "First comment."

    # Query PostgreSQL independently to verify the API committed the record.
    with SessionLocal() as db:
        stored = db.get(Comment, comment["id"])
        assert stored is not None
        assert stored.content == "First comment."


@pytest.mark.anyio
async def test_create_nested_replies(client):
    """Verify that replies retain the correct parent relationships."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    # Construct a three-level discussion.
    parent = await create_comment(client, headers, post_id, "Parent")
    reply = await create_comment(client, headers, post_id, "Reply", parent["id"])
    nested = await create_comment(client, headers, post_id, "Nested reply", reply["id"])

    # Each reply must reference its immediate parent, not the root.
    assert reply["parent_id"] == parent["id"]
    assert nested["parent_id"] == reply["id"]


@pytest.mark.anyio
async def test_list_comments(client):
    """Verify that comments and replies are publicly accessible."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    parent = await create_comment(client, headers, post_id, "Parent")
    reply = await create_comment(client, headers, post_id, "Reply", parent["id"])

    # Reading comments does not require authentication.
    response = await client.get(f"/posts/{post_id}/comments")

    assert response.status_code == 200

    comments = {item["id"]: item for item in response.json()}

    assert len(comments) == 2
    assert comments[parent["id"]]["content"] == "Parent"
    assert comments[reply["id"]]["parent_id"] == parent["id"]


# ---------------------------------------------------------------------------
# Authentication and ownership
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_comment_requires_authentication(client):
    """Verify that anonymous users cannot create comments."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    # Deliberately omit the JWT header.
    response = await client.post(
        f"/posts/{post_id}/comments",
        json={"content": "Anonymous comment"},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_only_author_can_edit_comment(client):
    """Verify that only the comment author can modify its content."""

    owner = await register_and_login(client, 0)
    other = await register_and_login(client, 1)

    post_id = await create_post(client, owner)
    comment = await create_comment(client, other, post_id, "Original content")

    # The post owner must not be able to edit another user's comment.
    denied = await client.patch(
        f"/posts/comments/{comment['id']}",
        headers=owner,
        json={"content": "Unauthorized edit"},
    )
    assert denied.status_code == 403

    # The actual comment author can make the same request successfully.
    allowed = await client.patch(
        f"/posts/comments/{comment['id']}",
        headers=other,
        json={"content": "Updated content"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["content"] == "Updated content"


@pytest.mark.anyio
async def test_only_author_can_delete_comment(client):
    """Verify that users cannot delete another author's comments."""

    owner = await register_and_login(client, 0)
    other = await register_and_login(client, 1)

    post_id = await create_post(client, owner)
    comment = await create_comment(client, other, post_id, "Other user's comment")

    # Owning the post does not grant ownership of its comments.
    response = await client.delete(
        f"/posts/comments/{comment['id']}",
        headers=owner,
    )

    assert response.status_code == 403

    # A rejected deletion must leave the stored record unchanged.
    with SessionLocal() as db:
        assert db.get(Comment, comment["id"]).is_deleted is False


# ---------------------------------------------------------------------------
# Editing and soft deletion
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_edit_comment(client):
    """Verify that comment edits persist in PostgreSQL."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)
    comment = await create_comment(client, headers, post_id, "Original")

    response = await client.patch(
        f"/posts/comments/{comment['id']}",
        headers=headers,
        json={"content": "Updated"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Updated"

    # Confirm the updated content was committed to the database.
    with SessionLocal() as db:
        assert db.get(Comment, comment["id"]).content == "Updated"


@pytest.mark.anyio
async def test_delete_comment_preserves_replies(client):
    """Verify that soft deletion retains the discussion structure."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    parent = await create_comment(client, headers, post_id, "Parent")
    reply = await create_comment(client, headers, post_id, "Reply", parent["id"])

    deletion = await client.delete(
        f"/posts/comments/{parent['id']}",
        headers=headers,
    )
    assert deletion.status_code == 204

    response = await client.get(f"/posts/{post_id}/comments")
    comments = {item["id"]: item for item in response.json()}

    # The parent remains as a deleted placeholder.
    assert comments[parent["id"]]["content"] == "[Deleted]"
    assert comments[parent["id"]]["is_deleted"] is True

    # Replies retain their original content and parent relationship.
    assert comments[reply["id"]]["content"] == "Reply"
    assert comments[reply["id"]]["parent_id"] == parent["id"]


@pytest.mark.anyio
async def test_deleted_comment_cannot_be_edited(client):
    """Verify that deleted comments cannot be modified."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)
    comment = await create_comment(client, headers, post_id, "Original")

    await client.delete(
        f"/posts/comments/{comment['id']}",
        headers=headers,
    )

    # Soft-deleted comments remain stored but are no longer editable.
    response = await client.patch(
        f"/posts/comments/{comment['id']}",
        headers=headers,
        json={"content": "Updated"},
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Missing and deleted posts
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_comment_rejects_missing_post(client):
    """Verify that comments require an existing post."""

    headers = await register_and_login(client)

    response = await client.post(
        "/posts/999999999/comments",
        headers=headers,
        json={"content": "Orphan comment"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_deleted_post_rejects_new_comments(client):
    """Verify that deleted posts cannot receive additional comments."""

    headers = await register_and_login(client)
    post_id = await create_post(client, headers)

    # Soft-delete the post through the existing posts API.
    deletion = await client.delete(
        f"/posts/{post_id}",
        headers=headers,
    )
    assert deletion.status_code == 204

    # Deleted posts remain in the database for historical purposes,
    # but their discussions cannot accept new comments.
    response = await client.post(
        f"/posts/{post_id}/comments",
        headers=headers,
        json={"content": "New comment"},
    )

    assert response.status_code == 404
