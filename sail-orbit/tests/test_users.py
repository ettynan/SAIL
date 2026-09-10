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
        user = database.scalar(
            select(User).where(User.username == TEST_USERNAME)
        )

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
            user = database.scalar(
                select(User).where(User.username == TEST_USERNAME)
            )

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