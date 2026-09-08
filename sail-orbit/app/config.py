"""Application configuration for Triage."""

import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    """Store configuration values loaded from environment variables."""

    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_URL = os.getenv("DATABASE_URL")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")