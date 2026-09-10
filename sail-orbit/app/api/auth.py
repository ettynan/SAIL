"""Define authentication-related API endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.user import User
from app.schemas.user import UserRegistration
from app.services.auth import hash_password


# Group authentication endpoints under the /auth URL prefix.
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    registration: UserRegistration,
    database: Session = Depends(get_db),
):
    """Create a new SAIL Orbit user account from registration data."""

    # Convert the submitted plaintext password into a secure hash before
    # creating the database record. The plaintext password is never stored.
    user = User(
        username=registration.username,
        email=registration.email,
        password_hash=hash_password(registration.password),
        display_name=registration.display_name,
    )

    # Stage the new user, save the transaction, and reload database-generated
    # values such as the user ID and timestamps.
    database.add(user)
    database.commit()
    database.refresh(user)

    # Return account information without exposing the stored password hash.
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
    }