"""Application Configuration and Environment Settings."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/safety_ctd_db"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Comma-separated list of allowed frontend origins for CORS, e.g.
    # "https://pharmsignals.vercel.app,http://localhost:3000". No wildcard
    # in production — the frontend never sends cookies/credentials, so this
    # is the sole gate on which origins may call the API.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    # Optional regex to additionally allow (e.g. Vercel's per-deploy preview
    # URLs, which change on every push): r"https://.*\.vercel\.app"
    CORS_ORIGIN_REGEX: Optional[str] = os.getenv("CORS_ORIGIN_REGEX") or None

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
