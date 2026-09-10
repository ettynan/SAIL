"""Run the SAIL Orbit FastAPI application."""

from fastapi import FastAPI
from app.api.auth import router as auth_router

app = FastAPI(title="SAIL Orbit")

# Register authentication endpoints such as POST /auth/register.
app.include_router(auth_router)