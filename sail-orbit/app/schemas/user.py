"""Define request and response data structures for SAIL Orbit users."""

from pydantic import BaseModel, EmailStr, field_validator


class UserRegistration(BaseModel):
    """Define and validate the data required to register a user."""

    # Each declaration defines a request field and its required data type.
    # Pydantic validates incoming request data against these types.
    username: str
    email: EmailStr
    password: str

    # This value becomes the name shown to other users.
    display_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        """Require passwords to meet Orbit's basic security rules."""

        # Require enough length to discourage short, easily guessed passwords.
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long.")

        # Require a mixture of character types instead of accepting passwords
        # made entirely from one type of character.
        if not any(character.isupper() for character in password):
            raise ValueError("Password must contain an uppercase letter.")

        if not any(character.islower() for character in password):
            raise ValueError("Password must contain a lowercase letter.")

        if not any(character.isdigit() for character in password):
            raise ValueError("Password must contain a number.")

        if not any(not character.isalnum() for character in password):
            raise ValueError("Password must contain a special character.")

        return password
