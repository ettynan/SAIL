"""Integration tests for SAIL Orbit post APIs.

These tests exercise the real FastAPI endpoints, including authentication,
Pydantic validation, PostgreSQL persistence, and authorization.

Test accounts and their posts are removed before and after each test.
"""

import httpx2
import pytest
from sqlalchemy import select

from app.extensions import SessionLocal
from app.models.user import User
from run import app

TEST_USERS = [
    {
        "username": "orbit_post_author",
        "email": "orbit_post_author@example.com",
        "password": "OrbitTest123!",
    },
    {
        "username": "orbit_post_other",
        "email": "orbit_post_other@example.com",
        "password": "OrbitTest123!",
    },
]


def delete_test_users():
    """Remove post-test accounts and their associated posts."""

    with SessionLocal() as database:
        for account in TEST_USERS:
            user = database.scalar(
                select(User).where(User.username == account["username"])
            )

            if user is not None:
                # Delete posts before their author to satisfy the foreign key.
                for post in user.posts:
                    database.delete(post)

                database.delete(user)

        database.commit()


@pytest.fixture(autouse=True)
def clean_test_users():
    """Provide clean test accounts before and after each test."""

    delete_test_users()
    yield
    delete_test_users()


@pytest.fixture
async def client():
    """Provide an HTTP client connected directly to FastAPI."""

    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


async def register_and_login(client, account_index=0):
    """Register a test account and obtain its JWT through the real API."""

    account = TEST_USERS[account_index]

    registration = await client.post(
        "/auth/register",
        json=account,
    )
    assert registration.status_code == 201

    login = await client.post(
        "/auth/login",
        json={
            "username": account["username"],
            "password": account["password"],
        },
    )
    assert login.status_code == 200

    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_test_post(client, headers, content="Test post content."):
    """Create a post through the API and return its response data."""

    response = await client.post(
        "/posts",
        headers=headers,
        json={"content": content},
    )
    assert response.status_code == 201

    return response.json()


@pytest.mark.anyio
async def test_create_post(client):
    """Verify that an authenticated user can create a post."""

    headers = await register_and_login(client)

    response = await client.post(
        "/posts",
        headers=headers,
        json={"content": "My first Orbit post."},
    )

    assert response.status_code == 201

    data = response.json()
    assert isinstance(data["id"], int)
    assert isinstance(data["author_id"], int)
    assert data["content"] == "My first Orbit post."
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.anyio
async def test_create_post_requires_authentication(client):
    """Verify that anonymous users cannot create posts."""

    response = await client.post(
        "/posts",
        json={"content": "Unauthorized post."},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_post_rejects_invalid_content(client):
    """Verify that empty, whitespace-only, and oversized posts are rejected."""

    headers = await register_and_login(client)

    for content in ["", "   ", "x" * 5001]:
        response = await client.post(
            "/posts",
            headers=headers,
            json={"content": content},
        )

        assert response.status_code == 422


@pytest.mark.anyio
async def test_create_post_trims_whitespace(client):
    """Verify that surrounding whitespace is removed before saving."""

    headers = await register_and_login(client)

    post = await create_test_post(
        client,
        headers,
        content="  Hello Orbit!  ",
    )

    assert post["content"] == "Hello Orbit!"


@pytest.mark.anyio
async def test_list_posts(client):
    """Verify that the public endpoint returns created posts."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.get("/posts")

    assert response.status_code == 200
    assert any(item["id"] == post["id"] for item in response.json())


@pytest.mark.anyio
async def test_get_post(client):
    """Verify that an individual post can be retrieved publicly."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.get(f"/posts/{post['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == post["id"]
    assert response.json()["content"] == post["content"]


@pytest.mark.anyio
async def test_get_nonexistent_post(client):
    """Verify that an unknown post ID returns 404."""

    response = await client.get("/posts/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found."


@pytest.mark.anyio
async def test_update_own_post(client):
    """Verify that a post author can edit their own post."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.patch(
        f"/posts/{post['id']}",
        headers=headers,
        json={"content": "Updated Orbit post."},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Updated Orbit post."


@pytest.mark.anyio
async def test_update_post_rejects_invalid_content(client):
    """Verify that post edits enforce content validation."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.patch(
        f"/posts/{post['id']}",
        headers=headers,
        json={"content": "   "},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_update_post_requires_authentication(client):
    """Verify that anonymous users cannot edit posts."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.patch(
        f"/posts/{post['id']}",
        json={"content": "Unauthorized edit."},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_other_users_post_is_forbidden(client):
    """Verify that one user cannot edit another user's post."""

    author_headers = await register_and_login(client, 0)
    post = await create_test_post(client, author_headers)

    other_headers = await register_and_login(client, 1)

    response = await client.patch(
        f"/posts/{post['id']}",
        headers=other_headers,
        json={"content": "Unauthorized edit."},
    )

    assert response.status_code == 403

    # Confirm that the rejected request did not modify the stored post.
    stored_post = await client.get(f"/posts/{post['id']}")
    assert stored_post.json()["content"] == post["content"]


@pytest.mark.anyio
async def test_delete_own_post(client):
    """Verify that deleting a post preserves it with redacted content."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.delete(
        f"/posts/{post['id']}",
        headers=headers,
    )

    assert response.status_code == 204

    # The deleted post remains accessible with its content hidden.
    response = await client.get(f"/posts/{post['id']}")

    assert response.status_code == 200
    assert response.json()["content"] == "[Deleted]"
    assert response.json()["is_deleted"] is True


@pytest.mark.anyio
async def test_delete_post_requires_authentication(client):
    """Verify that anonymous users cannot delete posts."""

    headers = await register_and_login(client)
    post = await create_test_post(client, headers)

    response = await client.delete(f"/posts/{post['id']}")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_delete_other_users_post_is_forbidden(client):
    """Verify that one user cannot delete another user's post."""

    author_headers = await register_and_login(client, 0)
    post = await create_test_post(client, author_headers)

    other_headers = await register_and_login(client, 1)

    response = await client.delete(
        f"/posts/{post['id']}",
        headers=other_headers,
    )

    assert response.status_code == 403

    # The author's post must still exist after the rejected deletion.
    response = await client.get(f"/posts/{post['id']}")
    assert response.status_code == 200
