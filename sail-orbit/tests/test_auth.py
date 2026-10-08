"""Tests for Orbit authentication and password security services."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import Config
from app.extensions import SessionLocal
from app.models.user import User
from app.services.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)


def test_hash_password_does_not_return_plaintext():
    """Verify that plaintext passwords are not returned as stored hashes."""
    password = "OrbitTest123!"
    hashed_password = hash_password(password)

    assert hashed_password != password


def test_verify_password_accepts_correct_password():
    """Verify that the correct password matches its stored hash."""
    password = "OrbitTest123!"
    hashed_password = hash_password(password)

    assert verify_password(password, hashed_password) is True


def test_verify_password_rejects_incorrect_password():
    """Verify that an incorrect password does not match the stored hash."""
    hashed_password = hash_password("OrbitTest123!")

    assert verify_password("wrong", hashed_password) is False


def test_create_and_decode_access_token():
    """Verify that a valid JWT contains the correct user ID."""
    token = create_access_token(user_id=1)
    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert "exp" in payload


def test_decode_invalid_access_token():
    """Verify that an invalid JWT is rejected."""
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("invalid.token.value")


def test_decode_expired_access_token():
    """Verify that an expired JWT is rejected."""
    payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_get_current_user_accepts_valid_token():
    """Verify that a valid JWT identifies the correct active user."""
    # Create a temporary user directly in PostgreSQL so the dependency has
    # a known account to retrieve from the user ID stored in the JWT.
    with SessionLocal() as database:
        user = User(
            username="current_user_test",
            email="current_user_test@example.com",
            password_hash=hash_password("OrbitTest123!"),
        )
        database.add(user)
        database.commit()
        database.refresh(user)

        user_id = user.id

    try:
        # Create a JWT whose subject contains the temporary user's database ID.
        token = create_access_token(user_id)

        # Package the JWT the same way FastAPI's bearer authentication
        # dependency provides credentials to get_current_user().
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        # Call the dependency with a database session and verify that the
        # token resolves to the expected user account.
        with SessionLocal() as database:
            current_user = get_current_user(
                credentials=credentials,
                database=database,
            )

            assert current_user.id == user_id
            assert current_user.username == "current_user_test"
            assert current_user.is_active is True

    finally:
        # Remove the temporary account even if an assertion fails.
        with SessionLocal() as database:
            user = database.get(User, user_id)
            if user is not None:
                database.delete(user)
                database.commit()


def test_get_current_user_rejects_invalid_token():
    """Verify that an invalid JWT cannot authenticate a user."""
    # Package an invalid JWT the same way FastAPI supplies bearer
    # credentials to the authentication dependency.
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.token.value",
    )

    # An invalid token should cause the authentication dependency to reject
    # the request with HTTP 401 rather than returning a user.
    with SessionLocal() as database, pytest.raises(HTTPException) as exception:
        get_current_user(
            credentials=credentials,
            database=database,
        )

    assert exception.value.status_code == 401


def test_get_current_user_rejects_expired_token():
    """Verify that an expired JWT cannot authenticate a user."""
    payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    # An expired token should be rejected with HTTP 401.
    with SessionLocal() as database, pytest.raises(HTTPException) as exception:
        get_current_user(
            credentials=credentials,
            database=database,
        )

    assert exception.value.status_code == 401


def test_get_current_user_rejects_unknown_user():
    """Verify that a valid JWT cannot authenticate a nonexistent user."""
    # Use a valid token containing a user ID that does not exist.
    token = create_access_token(user_id=999999999)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with SessionLocal() as database, pytest.raises(HTTPException) as exception:
        get_current_user(
            credentials=credentials,
            database=database,
        )

    assert exception.value.status_code == 401


def test_require_admin_accepts_admin_user():
    """Verify that an authenticated administrator passes authorization."""

    user = User(
        username="admin_test",
        email="admin_test@example.com",
        password_hash="unused",
        role="admin",
        is_active=True,
    )

    assert require_admin(user) is user


def test_require_admin_rejects_regular_user():
    """Verify that an authenticated regular user is denied admin access."""

    user = User(
        username="user_test",
        email="user_test@example.com",
        password_hash="unused",
        role="user",
        is_active=True,
    )

    with pytest.raises(HTTPException) as error:
        require_admin(user)

    assert error.value.status_code == 403
    assert error.value.detail == "Administrator access required."
