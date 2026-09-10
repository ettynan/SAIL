"""Define request and response data structures for SAIL Orbit users."""

from pydantic import BaseModel, EmailStr


class UserRegistration(BaseModel):
    """Define and validate the data required to register a user."""

    # Each declaration defines a request field and its required data type.
    # Pydantic validates incoming request data against these types.
    username: str
    email: EmailStr
    password: str

    # This value becomes the name shown to other users.
    display_name: str