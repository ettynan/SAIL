"""Define user profile and account-related API endpoints for SAIL Orbit."""

from fastapi import APIRouter, Depends

from app.models.user import User
from app.services.auth import get_current_user


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