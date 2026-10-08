"""
Integration tests for SAIL Orbit user profile APIs.

These tests send requests through FastAPI instead of calling endpoint
functions directly. This verifies that routing, validation, authentication,
database access, and responses work together through the app's real
API boundary.

Reusable fixtures and helpers handle repeated test setup. Operations that are
the actual subject of a test remain visible in that test. Protected endpoint
tests obtain JWTs through the real login endpoint because JWT internals are
already tested separately in tests/test_auth.py.
"""

import httpx2
import pytest
from sqlalchemy import select

from app.extensions import SessionLocal
from app.models.user import User
from run import app

TEST_USERNAME = "orbit_test_user"
TEST_EMAIL = "orbit_test_user@example.com"
TEST_PASSWORD = "OrbitTest123!"


def delete_test_user():
    """Remove the standard test user from PostgreSQL."""

    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == TEST_USERNAME))

        if user is not None:
            database.delete(user)
            database.commit()


@pytest.fixture(autouse=True)
def clean_test_user():
    """Give each test a clean database state before and after execution."""

    delete_test_user()
    yield
    delete_test_user()


@pytest.fixture
async def client():
    """Provide an HTTP client connected directly to the FastAPI application."""

    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


async def register_test_user(client):
    """Create the standard account through the real registration endpoint."""

    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201
    return response


async def login_test_user(client):
    """Log in through the real API and return its response."""

    response = await client.post(
        "/auth/login",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 200
    return response


@pytest.mark.anyio
async def test_get_own_profile(client):
    """Verify that an authenticated user can retrieve their own profile."""

    await register_test_user(client)

    # Use a JWT from the real login endpoint to test the same authentication
    # boundary that an Orbit client will use.
    login_response = await login_test_user(client)
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL
    assert data["bio"] is None
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Profile retrieval must never expose authentication secrets.
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_get_own_profile_requires_authentication(client):
    """Verify that a user must authenticate before retrieving their profile."""

    # Make the request without a Bearer token to verify that the protected
    # endpoint cannot be accessed anonymously.
    response = await client.get("/users/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_update_own_profile(client):
    """Verify that an authenticated user can update their profile."""

    await register_test_user(client)

    # Use a JWT from the real login endpoint so this test exercises the same
    # authentication path used by an Orbit client.
    login_response = await login_test_user(client)
    access_token = login_response.json()["access_token"]

    # Update the user-editable bio through the authenticated endpoint.
    response = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "bio": "Updated profile bio.",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["bio"] == "Updated profile bio."

    # Account and authorization fields must remain unchanged by a profile edit.
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL
    assert data["role"] == "user"
    assert data["is_active"] is True

    # Profile responses must never expose authentication secrets.
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_update_own_profile_can_clear_bio(client):
    """Verify that a user can explicitly clear an existing bio."""

    await register_test_user(client)
    login_response = await login_test_user(client)
    access_token = login_response.json()["access_token"]

    # Give the account a bio before testing whether an explicit null value
    # removes it.
    response = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"bio": "Temporary bio."},
    )
    assert response.status_code == 200

    # An explicit null differs from omitting bio entirely. It should clear
    # the stored value.
    response = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"bio": None},
    )

    assert response.status_code == 200
    assert response.json()["bio"] is None


@pytest.mark.anyio
async def test_update_own_profile_cannot_change_protected_fields(client):
    """Verify that profile updates cannot change protected account fields."""

    await register_test_user(client)
    login_response = await login_test_user(client)
    access_token = login_response.json()["access_token"]

    # Attempt to change authorization and account-status fields.
    # Neither field should change.
    response = await client.patch(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "role": "admin",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["role"] == "user"
    assert data["is_active"] is True


@pytest.mark.anyio
async def test_update_own_profile_requires_authentication(client):
    """Verify that a user must authenticate before updating their profile."""

    # No Bearer token is supplied, so the authentication dependency should
    # reject the request before any profile change occurs.
    response = await client.patch(
        "/users/me",
        json={},
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_public_profile(client):
    """Verify that a user's public profile can be retrieved by username."""

    await register_test_user(client)

    response = await client.get(f"/users/{TEST_USERNAME}")

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == TEST_USERNAME
    assert data["bio"] is None
    assert "id" in data
    assert "created_at" in data

    # Public profiles must not expose private account, authorization, or
    # authentication information.
    assert "email" not in data
    assert "role" not in data
    assert "is_active" not in data
    assert "updated_at" not in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_get_public_profile_rejects_unknown_user(client):
    """Verify that requesting an unknown public profile returns 404."""

    response = await client.get("/users/user_that_does_not_exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."