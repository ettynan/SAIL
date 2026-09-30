"""Run the SAIL Orbit FastAPI application."""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.users import router as users_router

app = FastAPI(title="SAIL Orbit")

# Register authentication endpoints such as POST /auth/register and
# POST /auth/login.
app.include_router(auth_router)

# Register authenticated user account and profile endpoints such as
# GET /users/me.
app.include_router(users_router)
