"""Define authentication-related API endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRegistration
from app.services.auth import create_access_token, hash_password, verify_password

# Group authentication endpoints under the /auth URL prefix.
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    registration: UserRegistration,
    database: Session = Depends(get_db),
):
    """Create a new SAIL Orbit user account from registration data."""

    # Check whether another account already uses the submitted username or
    # email address before attempting to create the new database record.
    existing_user = (
        database.query(User)
        .filter(
            or_(
                User.username == registration.username,
                User.email == registration.email,
            )
        )
        .first()
    )

    # Reject duplicate account information with a conflict response instead
    # of allowing the database uniqueness constraint to fail during commit.
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered.",
        )

    # Convert the submitted plaintext password into a secure hash before
    # creating the database record. The plaintext password is never stored.
    user = User(
        username=registration.username,
        email=registration.email,
        password_hash=hash_password(registration.password),
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
        "role": user.role,
        "is_active": user.is_active,
    }


# Login endpoint
@router.post("/login", response_model=TokenResponse)
def login_user(
    login: LoginRequest,
    database: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT access token."""

    # Find the account associated with the submitted username.
    user = database.query(User).filter(User.username == login.username).first()

    # Authentication succeeds only for an existing, active account with the
    # correct password. Using the same response for each failure avoids exposing
    # whether a username exists or an account has been deactivated.
    if (
        user is None
        or not user.is_active
        or not verify_password(login.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Create an access token identifying the authenticated user.
    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )