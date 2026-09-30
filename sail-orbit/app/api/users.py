"""Define user profile and account-related API endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UserStatusUpdate
from app.services.auth import get_current_user, require_admin

# Keep user and profile operations under a common /users URL prefix.
# Authentication operations such as registration and login remain under
# /auth, while account and profile operations belong here.
router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_own_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the profile belonging to the authenticated user."""

    # get_current_user validates the bearer token, reads the user ID from
    # the token, retrieves that user from the database, and verifies that
    # the account is active before this endpoint is allowed to run.
    #
    # The endpoint therefore does not accept a user ID from the client.
    # The authenticated token determines which account can be returned.
    #
    # Fields are selected explicitly instead of returning the SQLAlchemy
    # User object directly. This controls the API response and ensures that
    # internal authentication data such as password_hash is never exposed.
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.patch("/me")
def update_own_profile(
    profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    database: Session = Depends(get_db),
):
    """Update profile information belonging to the authenticated user."""

    # Only fields explicitly supplied by the client should be changed.
    # This lets a PATCH request modify one profile field while preserving
    # the current value of every field the user did not submit.
    updates = profile.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(current_user, field, value)

    # Persist the changes to PostgreSQL and refresh the model so the response
    # reflects the values actually stored by the database.
    database.commit()
    database.refresh(current_user)

    # Return the same profile representation used by GET /users/me.
    # Explicit field selection also prevents password_hash from being exposed.
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.get("/{username}")
def get_public_profile(
    username: str,
    database: Session = Depends(get_db),
):
    """Return the public profile for an active Orbit user."""

    # Look up the account by username because usernames provide a stable,
    # human-readable way to address public profiles.
    user = database.query(User).filter(User.username == username).first()

    # Inactive accounts are treated the same as accounts that do not exist so
    # their profiles are not exposed through the public endpoint.
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Public profiles expose only information intended for other Orbit users.
    # Private account and authentication fields remain internal.
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "created_at": user.created_at,
    }


@router.patch("/{username}/status")
def update_user_status(
    username: str,
    status_update: UserStatusUpdate,
    database: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Allow an administrator to activate or deactivate a user account."""

    # The require_admin dependency authenticates the requester and verifies
    # administrator authorization before account management can occur.
    user = database.query(User).filter(User.username == username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Persist only the account-status value accepted by UserStatusUpdate.
    user.is_active = status_update.is_active
    database.commit()
    database.refresh(user)

    # Return enough account information to confirm the administrative change
    # without exposing authentication data such as password_hash.
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
    }
