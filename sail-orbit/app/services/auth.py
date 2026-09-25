"""Authentication and password security services for Orbit."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import Config
from app.extensions import get_db
from app.models.user import User

PASSWORD_HASH = PasswordHash.recommended()

# Extract bearer tokens from the Authorization header of protected requests.
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a plaintext password for secure storage."""
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored password hash."""
    return PASSWORD_HASH.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    """Create a JWT access token for an authenticated user."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=Config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expires_at}

    return jwt.encode(
        payload,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(
        token,
        Config.JWT_SECRET_KEY,
        algorithms=[Config.JWT_ALGORITHM],
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    database: Session = Depends(get_db),
) -> User:
    """Return the authenticated user identified by a valid JWT access token."""

    # Decode and validate the JWT from the Authorization header. The token
    # subject contains the database ID of the authenticated user.
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        # Reject tokens that are invalid, expired, missing a user ID, or
        # contain a user ID that cannot be converted to an integer.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
        )

    # Retrieve the user account identified by the token.
    user = database.get(User, user_id)

    # Authentication succeeds only when the account still exists and is active.
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
        )

    return user
