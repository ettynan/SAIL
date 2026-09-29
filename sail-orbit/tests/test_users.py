"""
Integration tests for SAIL Orbit user APIs.

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
from app.services.auth import verify_password
from run import app


TEST_USERNAME = "orbit_test_user"
TEST_EMAIL = "orbit_test_user@example.com"
TEST_PASSWORD = "OrbitTest123!"
TEST_DISPLAY_NAME = "Orbit Test User"


def delete_test_user():
    """Remove the standard test user from PostgreSQL."""

    with SessionLocal() as database:
        user = database.scalar(
            select(User).where(User.username == TEST_USERNAME)
        )

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
            "display_name": TEST_DISPLAY_NAME,
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
async def test_register_user(client):
    """Verify that valid registration creates a user."""

    # Keep this request here because registration itself is under test.
    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "display_name": TEST_DISPLAY_NAME,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL
    assert data["display_name"] == TEST_DISPLAY_NAME
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data

    # Check PostgreSQL separately so a successful response alone does not
    # count as proof that the account was actually persisted.
    with SessionLocal() as database:
        user = database.scalar(
            select(User).where(User.username == TEST_USERNAME)
        )

        assert user is not None
        assert user.email == TEST_EMAIL
        assert user.password_hash != TEST_PASSWORD
        assert verify_password(TEST_PASSWORD, user.password_hash)


@pytest.mark.anyio
async def test_login_user(client):
    """Verify that valid credentials return a JWT."""

    await register_test_user(client)

    # Keep login here because login itself is under test.
    response = await client.post(
        "/auth/login",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_register_rejects_duplicate_username(client):
    """Verify that registration rejects an existing username."""

    await register_test_user(client)

    # Only the email changes, isolating the duplicate username condition.
    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": "different@example.com",
            "password": TEST_PASSWORD,
            "display_name": "Duplicate Username Test",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Username or email already registered."
    )


@pytest.mark.anyio
async def test_register_rejects_duplicate_email(client):
    """Verify that registration rejects an existing email address."""

    await register_test_user(client)

    # Only the username changes, isolating the duplicate email condition.
    response = await client.post(
        "/auth/register",
        json={
            "username": "different_orbit_user",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "display_name": "Duplicate Email Test",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Username or email already registered."
    )


@pytest.mark.anyio
async def test_register_rejects_short_password(client):
    """Verify that registration rejects a password under 12 characters."""

    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": "Short1!",
            "display_name": TEST_DISPLAY_NAME,
        },
    )

    # Schema validation should reject this before database work occurs.
    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize(
    "password",
    [
        "orbittest123!",
        "ORBITTEST123!",
        "OrbitTestPass!",
        "OrbitTest1234",
    ],
)
async def test_register_rejects_password_missing_required_character_type(
    client,
    password,
):
    """Verify that passwords require all configured character types."""

    # Parameterization tests each rule without duplicating the request.
    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": password,
            "display_name": TEST_DISPLAY_NAME,
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_rejects_invalid_email(client):
    """Verify that registration rejects an invalid email address."""

    response = await client.post(
        "/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": "not-an-email",
            "password": TEST_PASSWORD,
            "display_name": TEST_DISPLAY_NAME,
        },
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_login_rejects_incorrect_password(client):
    """Verify that login rejects an incorrect password."""

    await register_test_user(client)

    # The account exists, isolating the password as the failure condition.
    response = await client.post(
        "/auth/login",
        json={
            "username": TEST_USERNAME,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


@pytest.mark.anyio
async def test_login_rejects_unknown_username(client):
    """Verify that login rejects an unknown username."""

    # Automatic cleanup guarantees that this account does not exist.
    response = await client.post(
        "/auth/login",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


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
    assert data["display_name"] == TEST_DISPLAY_NAME
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