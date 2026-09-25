"""Define request and response data structures for user authentication."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Validate data submitted when a user logs in."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Define the response returned after successful authentication."""

    access_token: str
    token_type: str
