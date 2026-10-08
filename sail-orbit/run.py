"""Run the SAIL Orbit FastAPI application."""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="SAIL Orbit")

# Allow the local React/Vite frontend to make cross-origin requests
# to the FastAPI backend during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register authentication endpoints such as POST /auth/register and
# POST /auth/login.
app.include_router(auth_router)

# Register authenticated user account and profile endpoints such as
# GET /users/me.
app.include_router(users_router)
