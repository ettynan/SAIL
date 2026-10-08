"""Integration tests for SAIL Orbit administrator user-management APIs.

These tests verify administrative account-management operations through
Orbit's real API boundary. Requests therefore exercise routing,
authentication, authorization, database access, and response handling
together.

Administrator accounts are created directly in PostgreSQL because normal
Orbit registration intentionally creates accounts with the standard "user"
role. The administrator then authenticates through the normal login endpoint
so protected requests use the same JWT authentication path as the application.
"""

import httpx2
import pytest
from sqlalchemy import select

from app.extensions import SessionLocal
from app.models.user import User
from app.services.auth import hash_password
from run import app

# Separate administrator and managed-user accounts allow tests to verify that
# authorization belongs to the requester while account changes apply only to
# the intended target user.
ADMIN_USERNAME = "orbit_test_admin"
ADMIN_EMAIL = "orbit_test_admin@example.com"
ADMIN_PASSWORD = "OrbitAdmin123!"

USER_USERNAME = "orbit_managed_user"
USER_EMAIL = "orbit_managed_user@example.com"
USER_PASSWORD = "OrbitUser123!"


def delete_test_users():
    """Remove accounts created by administrator user-management tests."""

    with SessionLocal() as database:
        # Both accounts are removed together because administrator tests can
        # create an admin requester and a separate account being managed.
        users = database.scalars(
            select(User).where(User.username.in_([ADMIN_USERNAME, USER_USERNAME]))
        ).all()

        for user in users:
            database.delete(user)

        database.commit()


@pytest.fixture(autouse=True)
def clean_test_users():
    """Give each administrator test an isolated database state."""

    # Cleanup before the test prevents data left by an interrupted earlier run
    # from affecting the result. Cleanup afterward prevents this test from
    # affecting later tests.
    delete_test_users()
    yield
    delete_test_users()


@pytest.fixture
async def client():
    """Provide an HTTP client connected directly to the FastAPI application."""

    # ASGITransport sends requests through the actual FastAPI application
    # without requiring a separately running web server.
    transport = httpx2.ASGITransport(app=app)

    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


def create_admin_user():
    """Create an administrator directly for authorization testing."""

    # Public registration always creates a normal user. Creating this account
    # directly allows the test to establish the admin role without introducing
    # an artificial API for granting administrative privileges.
    with SessionLocal() as database:
        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )

        database.add(admin)
        database.commit()


async def register_managed_user(client):
    """Create the account that will be managed by the administrator."""

    # The target account goes through normal registration so it begins with
    # the same defaults and persisted state as a real Orbit user.
    response = await client.post(
        "/auth/register",
        json={
            "username": USER_USERNAME,
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
        },
    )

    # Setup must succeed before an administrator-management test can provide
    # meaningful results.
    assert response.status_code == 201


async def login_admin(client):
    """Authenticate the test administrator and return its JWT access token."""

    # Although the administrator was created directly in PostgreSQL, login
    # deliberately uses the real endpoint. This verifies subsequent admin
    # requests with a JWT produced through Orbit's normal authentication path.
    response = await client.post(
        "/auth/login",
        json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
    )

    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.anyio
async def test_admin_can_deactivate_user(client):
    """Verify that an administrator can deactivate another user account."""

    create_admin_user()
    await register_managed_user(client)
    access_token = await login_admin(client)

    # The username identifies the account being managed, while the JWT
    # identifies and authorizes the administrator requesting the change.
    response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["username"] == USER_USERNAME
    assert data["role"] == "user"
    assert data["is_active"] is False

    # Check PostgreSQL separately so the response alone does not count as
    # proof that the account-status change was actually persisted.
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == USER_USERNAME))

        assert user is not None
        assert user.is_active is False


@pytest.mark.anyio
async def test_admin_can_reactivate_user(client):
    """Verify that an administrator can reactivate a deactivated user account."""

    create_admin_user()
    await register_managed_user(client)
    access_token = await login_admin(client)

    # Establish the deactivated state through the same administrator endpoint
    # used by the application rather than modifying the target directly.
    deactivate_response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    # Send a second administrative request to restore access to the account.
    response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Verify that the restored status is also persisted in PostgreSQL.
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == USER_USERNAME))

        assert user is not None
        assert user.is_active is True


@pytest.mark.anyio
async def test_regular_user_cannot_change_user_status(client):
    """Verify that a regular user cannot manage another account's status."""

    await register_managed_user(client)

    # Authenticate the standard user through the real login endpoint so the
    # request is authenticated but lacks the administrator role.
    login_response = await client.post(
        "/auth/login",
        json={
            "username": USER_USERNAME,
            "password": USER_PASSWORD,
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    # Authentication succeeded, so authorization should specifically reject
    # the request as forbidden rather than treating it as unauthenticated.
    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."

    # A rejected administrative request must leave the target account active.
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == USER_USERNAME))

        assert user is not None
        assert user.is_active is True


@pytest.mark.anyio
async def test_user_status_update_requires_authentication(client):
    """Verify that anonymous requests cannot change account status."""

    await register_managed_user(client)

    # No Authorization header is supplied. Authentication should stop the
    # request before the administrator authorization check or update occurs.
    response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        json={"is_active": False},
    )

    assert response.status_code == 401

    # Verify that the rejected request did not alter the stored account.
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == USER_USERNAME))

        assert user is not None
        assert user.is_active is True


@pytest.mark.anyio
async def test_admin_status_update_rejects_unknown_user(client):
    """Verify that an administrator receives 404 for an unknown account."""

    create_admin_user()
    access_token = await login_admin(client)

    # Use a username that the cleanup fixture guarantees is not one of the
    # administrator-test accounts created for this test.
    response = await client.patch(
        "/users/user_that_does_not_exist/status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_active": False},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


@pytest.mark.anyio
async def test_deactivated_user_cannot_login(client):
    """Verify that a deactivated account cannot authenticate."""

    create_admin_user()
    await register_managed_user(client)
    admin_token = await login_admin(client)

    # Deactivate the account through the administrator API so the test covers
    # the same account-management path used by the application.
    response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Attempt authentication with the correct credentials after deactivation.
    # A deactivated account must be rejected even when its password is valid.
    login_response = await client.post(
        "/auth/login",
        json={
            "username": USER_USERNAME,
            "password": USER_PASSWORD,
        },
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid username or password."


@pytest.mark.anyio
async def test_deactivated_user_cannot_use_existing_token(client):
    """Verify that deactivation invalidates access from an existing user token."""

    create_admin_user()
    await register_managed_user(client)

    # Authenticate the user before deactivation so the test has a valid JWT
    # that was issued while the account was still active.
    login_response = await client.post(
        "/auth/login",
        json={
            "username": USER_USERNAME,
            "password": USER_PASSWORD,
        },
    )
    assert login_response.status_code == 200
    user_token = login_response.json()["access_token"]

    # Confirm that the token initially provides access to an authenticated
    # endpoint before changing the account's status.
    profile_response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert profile_response.status_code == 200

    # Deactivate the account through the administrator API.
    admin_token = await login_admin(client)
    deactivate_response = await client.patch(
        f"/users/{USER_USERNAME}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200

    # Reuse the JWT that was issued before deactivation. get_current_user()
    # checks the current database state, so an otherwise valid token must no
    # longer authorize access once its account has been deactivated.
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials."
