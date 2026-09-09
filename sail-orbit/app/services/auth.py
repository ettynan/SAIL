"""Authentication and password security services for Orbit."""

import jwt
from pwdlib import PasswordHash
from app.config import Config
from datetime import datetime, timedelta, timezone

PASSWORD_HASH = PasswordHash.recommended()

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