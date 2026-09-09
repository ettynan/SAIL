"""Tests for Orbit authentication and password security services."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import Config
from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
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