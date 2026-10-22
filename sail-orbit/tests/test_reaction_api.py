"""Integration tests for the SAIL Orbit reactions API.

Verify reaction ownership, creation, switching, removal, public counts,
authentication, and error handling through FastAPI and PostgreSQL.

Database constraints and schema validation are covered in test_reactions.py.
"""

import httpx2
import pytest
from sqlalchemy import delete, select

from app.extensions import SessionLocal
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.user import User
from run import app

TEST_USERS = [
    {
        "username": "orbit_reaction_author",
        "email": "orbit_reaction_author@example.com",
        "password": "OrbitTest123!",
    },
    {
        "username": "orbit_reaction_other",
        "email": "orbit_reaction_other@example.com",
        "password": "OrbitTest123!",
    },
]


# ---------------------------------------------------------------------------
# Test setup and cleanup
# ---------------------------------------------------------------------------


def delete_test_users():
    """Remove test accounts and their associated posts and reactions."""

    with SessionLocal() as db:
        users = db.scalars(
            select(User).where(User.username.in_(u["username"] for u in TEST_USERS))
        ).all()

        ids = [user.id for user in users]
        if not ids:
            return

        posts = db.scalars(select(Post.id).where(Post.author_id.in_(ids))).all()

        # Remove reactions before deleting their referenced posts and users.
        db.execute(delete(Reaction).where(Reaction.user_id.in_(ids)))

        if posts:
            db.execute(delete(Reaction).where(Reaction.post_id.in_(posts)))
            db.execute(delete(Post).where(Post.id.in_(posts)))

        db.execute(delete(User).where(User.id.in_(ids)))
        db.commit()


@pytest.fixture(autouse=True)
def clean_test_users():
    """Keep test records isolated between runs."""

    delete_test_users()
    yield
    delete_test_users()


@pytest.fixture
async def client():
    """Connect directly to FastAPI without starting an HTTP server."""

    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        yield test_client


async def setup_user(client, index=0):
    """Register and authenticate a test account."""

    account = TEST_USERS[index]
    response = await client.post("/auth/register", json=account)
    assert response.status_code == 201

    response = await client.post(
        "/auth/login",
        json={
            "username": account["username"],
            "password": account["password"],
        },
    )
    assert response.status_code == 200

    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def setup_post(client, headers):
    """Create a post for reaction testing."""

    response = await client.post(
        "/posts",
        headers=headers,
        json={"content": "Reaction test post."},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def react(client, headers, post_id, reaction_type):
    """Submit a reaction and verify the request succeeded."""

    response = await client.put(
        f"/posts/{post_id}/reaction",
        headers=headers,
        json={"reaction_type": reaction_type},
    )
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# Reaction API tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_reaction_lookup_and_ownership(client):
    """Verify users retrieve only their own reactions."""

    author = await setup_user(client)
    other = await setup_user(client, 1)
    post_id = await setup_post(client, author)
    url = f"/posts/{post_id}/reaction"

    # A user who has not reacted receives null, even if the post exists.
    response = await client.get(url, headers=other)
    assert response.status_code == 200
    assert response.json() is None

    created = await react(client, author, post_id, "like")

    response = await client.get(url, headers=author)
    assert response.json()["id"] == created["id"]

    # Another user's reaction must not appear in this account's lookup.
    response = await client.get(url, headers=other)
    assert response.json() is None


@pytest.mark.anyio
async def test_reaction_lifecycle(client):
    """Verify creating, switching, and removing a persisted reaction."""

    headers = await setup_user(client)
    post_id = await setup_post(client, headers)

    created = await react(client, headers, post_id, "like")
    reaction_id = created["id"]

    # Switching must update the existing record rather than insert another.
    switched = await react(client, headers, post_id, "dislike")
    assert switched["id"] == reaction_id
    assert switched["reaction_type"] == "dislike"

    # A separate database session verifies the update was committed.
    with SessionLocal() as db:
        stored = db.get(Reaction, reaction_id)
        assert stored.reaction_type == "dislike"

    # Selecting the same reaction again removes it.
    removed = await react(client, headers, post_id, "dislike")
    assert removed is None

    with SessionLocal() as db:
        assert db.get(Reaction, reaction_id) is None


@pytest.mark.anyio
async def test_public_reaction_counts(client):
    """Verify counts reflect reactions from multiple users."""

    author = await setup_user(client)
    other = await setup_user(client, 1)
    post_id = await setup_post(client, author)
    url = f"/posts/{post_id}/reactions"

    # Counts are public, so these requests intentionally omit authentication.
    response = await client.get(url)
    assert response.json() == {"likes": 0, "dislikes": 0}

    await react(client, author, post_id, "like")
    await react(client, other, post_id, "dislike")

    response = await client.get(url)
    assert response.json() == {"likes": 1, "dislikes": 1}

    # Switching moves a count; removing a reaction reduces the total.
    await react(client, author, post_id, "dislike")
    await react(client, other, post_id, "dislike")

    response = await client.get(url)
    assert response.json() == {"likes": 0, "dislikes": 1}


@pytest.mark.anyio
async def test_reaction_authentication_and_validation(client):
    """Verify protected endpoints and HTTP request validation."""

    headers = await setup_user(client)
    post_id = await setup_post(client, headers)
    url = f"/posts/{post_id}/reaction"

    # Personal reaction lookup and modification require authentication.
    assert (await client.get(url)).status_code == 401
    assert (await client.put(url, json={"reaction_type": "like"})).status_code == 401

    # Verify FastAPI enforces the existing Pydantic request schema.
    for payload in ({"reaction_type": "love"}, {}):
        response = await client.put(url, headers=headers, json=payload)
        assert response.status_code == 422


@pytest.mark.anyio
async def test_reaction_unavailable_posts(client):
    """Verify nonexistent and soft-deleted posts reject reactions."""

    headers = await setup_user(client)
    post_id = await setup_post(client, headers)

    # A nonexistent post must return 404 for retrieval and modification.
    missing = "/posts/999999999/reaction"
    assert (await client.get(missing, headers=headers)).status_code == 404
    assert (
        await client.put(missing, headers=headers, json={"reaction_type": "like"})
    ).status_code == 404

    # Soft-deleted posts remain in PostgreSQL but cannot accept reactions.
    deletion = await client.delete(f"/posts/{post_id}", headers=headers)
    assert deletion.status_code == 204

    url = f"/posts/{post_id}/reaction"
    assert (await client.get(url, headers=headers)).status_code == 404
    assert (
        await client.put(url, headers=headers, json={"reaction_type": "like"})
    ).status_code == 404
