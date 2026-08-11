from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT / ".env"), str(_BACKEND / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://abac:abac_secret@localhost:5432/abac_auth"
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cookie_name: str = "access_token"
    cors_origins: str = "http://localhost:5173"
    ollama_model: str = "gemma4:e2b"
    ollama_host: str = "http://localhost:11434"
    moodle_url: str = ""
    moodle_token: str = ""
    max_agent_steps: int = 5


settings = Settings()
