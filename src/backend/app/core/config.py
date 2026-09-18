"""Application Configuration and Environment Settings."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/safety_ctd_db"
    )
    WATSONX_API_KEY: str = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: str = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str = os.getenv(
        "WATSONX_URL",
        "https://us-south.ml.cloud.ibm.com"
    )
    WATSONX_MODEL_ID: str = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct")
    IBM_BOB_CONFIG: str = os.getenv("IBM_BOB_CONFIG", "{}")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
