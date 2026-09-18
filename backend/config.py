"""Application settings loaded from environment variables / .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    GROQ_API_KEY: str = "placeholder-for-tests"
    FALLBACK_API_KEY: str = ""
    FALLBACK_API_URL: str = ""

    # Auth
    AUTH_TOKEN: str = "dev-secret-token"

    # Persistence
    DATABASE_URL: str = "sqlite:///./airline_agent.db"
    CHROMA_PATH: str = str(Path(__file__).parent / "chroma_db")

    # Policy YAML (resolved relative to this file so it works regardless of cwd)
    POLICY_YAML_PATH: str = str(Path(__file__).parent / "policy_rules.yaml")


settings = Settings()
