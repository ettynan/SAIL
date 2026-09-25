"""Tests for SAIL Orbit user registration."""

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


def delete_test_user():
    """Remove the registration test user from PostgreSQL."""
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == TEST_USERNAME))

        if user is not None:
            database.delete(user)
            database.commit()


# Tell pytest to run this asynchronous test using AnyIO.
@pytest.mark.anyio
async def test_register_user():
    """Verify that a valid registration request creates a user."""
    delete_test_user()

    # ASGITransport connects the HTTP client directly to the FastAPI
    # application without requiring a separate web server.
    transport = httpx2.ASGITransport(app=app)

    try:
        # AsyncClient lets the test make asynchronous HTTP requests
        # directly against the SAIL Orbit application.
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Orbit Test User",
                },
            )

        # Verify the API reports successful account creation.
        assert response.status_code == 201

        data = response.json()
        assert data["username"] == TEST_USERNAME
        assert data["email"] == TEST_EMAIL
        assert data["display_name"] == "Orbit Test User"
        assert data["role"] == "user"
        assert data["is_active"] is True

        # Sensitive password information must never be returned by the API.
        assert "password" not in data
        assert "password_hash" not in data

        # Verify that registration actually created the PostgreSQL record.
        with SessionLocal() as database:
            user = database.scalar(select(User).where(User.username == TEST_USERNAME))

            assert user is not None
            assert user.email == TEST_EMAIL

            # PostgreSQL should contain only the password hash, never the
            # plaintext password submitted during registration.
            assert user.password_hash != TEST_PASSWORD
            assert verify_password(
                TEST_PASSWORD,
                user.password_hash,
            )

    finally:
        # Always remove the test account, even when the test fails.
        delete_test_user()


@pytest.mark.anyio
async def test_login_user():
    """Verify that valid credentials authenticate a user and return a JWT."""
    # Start with a clean database state so an account left by an earlier test
    # cannot affect registration or authentication results.
    delete_test_user()

    # ASGITransport connects the HTTP client directly to the FastAPI
    # application, allowing the API endpoints to be tested without starting
    # a separate Uvicorn web server.
    transport = httpx2.ASGITransport(app=app)

    try:
        # Create a known test account through the actual registration
        # endpoint. This ensures the login test uses an account created by
        # the application, including its normal password-hashing process.
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            registration_response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Orbit Test User",
                },
            )

            # Confirm registration succeeded before attempting authentication.
            assert registration_response.status_code == 201

            # Submit the known username and plaintext password to the login
            # endpoint. The endpoint retrieves the account and verifies the
            # password against the stored password hash.
            response = await client.post(
                "/auth/login",
                json={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD,
                },
            )

        # A successful login should return HTTP 200 and a JWT access token
        # that can be used for authenticated requests.
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data

        # The token type identifies how the access token will be supplied in
        # the Authorization header when protected endpoints are added.
        assert data["token_type"] == "bearer"

    finally:
        # Remove the test account regardless of whether the test passes or
        # fails so repeated test runs begin with the same database state.
        delete_test_user()


@pytest.mark.anyio
async def test_register_rejects_duplicate_username():
    """Verify that registration rejects a username already in use."""
    delete_test_user()

    # Connect the HTTP client directly to the FastAPI application.
    transport = httpx2.ASGITransport(app=app)

    try:
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            # Create the first account so its username is already registered.
            first_response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Orbit Test User",
                },
            )

            assert first_response.status_code == 201

            # Attempt to register another account using the same username but
            # a different email address.
            duplicate_response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": "different@example.com",
                    "password": TEST_PASSWORD,
                    "display_name": "Duplicate Username Test",
                },
            )

        # The API should reject the duplicate username with HTTP 409 Conflict.
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == (
            "Username or email already registered."
        )

    finally:
        # Remove the test account regardless of whether the test passes.
        delete_test_user()


@pytest.mark.anyio
async def test_register_rejects_duplicate_email():
    """Verify that registration rejects an email address already in use."""
    delete_test_user()

    # Connect the HTTP client directly to the FastAPI application.
    transport = httpx2.ASGITransport(app=app)

    try:
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            # Create the first account so its email address is already
            # registered.
            first_response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Orbit Test User",
                },
            )

            assert first_response.status_code == 201

            # Attempt to register another account using a different username
            # but the same email address.
            duplicate_response = await client.post(
                "/auth/register",
                json={
                    "username": "different_orbit_user",
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Duplicate Email Test",
                },
            )

        # The API should reject the duplicate email with HTTP 409 Conflict.
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"] == (
            "Username or email already registered."
        )

    finally:
        # Remove the original test account regardless of whether the test
        # passes or fails.
        delete_test_user()


@pytest.mark.anyio
async def test_register_rejects_short_password():
    """Verify that registration rejects a password shorter than 12 characters."""
    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        # Submit an otherwise valid registration request with a password that
        # fails Orbit's minimum-length requirement.
        response = await client.post(
            "/auth/register",
            json={
                "username": TEST_USERNAME,
                "email": TEST_EMAIL,
                "password": "Short1!",
                "display_name": "Orbit Test User",
            },
        )

    # Pydantic should reject the request before registration reaches the
    # database and FastAPI should return HTTP 422 Unprocessable Entity.
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
async def test_register_rejects_password_missing_required_character_type(password):
    """Verify that passwords must contain all required character types."""
    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        # Each supplied password is long enough but deliberately omits one
        # required type: uppercase, lowercase, number, or special character.
        response = await client.post(
            "/auth/register",
            json={
                "username": TEST_USERNAME,
                "email": TEST_EMAIL,
                "password": password,
                "display_name": "Orbit Test User",
            },
        )

    # Schema validation should reject each invalid password before any user
    # account is created.
    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_rejects_invalid_email():
    """Verify that registration rejects an invalid email address."""
    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        # Submit an otherwise valid registration request with an email address
        # that does not satisfy the EmailStr validation used by UserRegistration.
        response = await client.post(
            "/auth/register",
            json={
                "username": TEST_USERNAME,
                "email": "not-an-email",
                "password": TEST_PASSWORD,
                "display_name": "Orbit Test User",
            },
        )

    # Pydantic should reject the request before registration reaches the
    # database.
    assert response.status_code == 422


@pytest.mark.anyio
async def test_login_rejects_incorrect_password():
    """Verify that login rejects an incorrect password."""
    delete_test_user()
    transport = httpx2.ASGITransport(app=app)

    try:
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            # Create a known account using the normal registration process.
            registration_response = await client.post(
                "/auth/register",
                json={
                    "username": TEST_USERNAME,
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "display_name": "Orbit Test User",
                },
            )

            assert registration_response.status_code == 201

            # Attempt to authenticate the account with an incorrect password.
            response = await client.post(
                "/auth/login",
                json={
                    "username": TEST_USERNAME,
                    "password": "WrongPassword123!",
                },
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password."

    finally:
        delete_test_user()


@pytest.mark.anyio
async def test_login_rejects_unknown_username():
    """Verify that login rejects a username that does not exist."""
    delete_test_user()
    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        # Attempt authentication using credentials for an account that is
        # known not to exist in the test database.
        response = await client.post(
            "/auth/login",
            json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."
