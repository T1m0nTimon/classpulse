from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    # Required in production. Used for HMAC of anonymous participant tokens and auth session hashing.
    secret_key: str = ""
    database_url: str = "sqlite:///./classpulse.db"
    # Public base URL used for QR codes / join links, e.g. https://classpulse.example.org
    public_url: str = ""
    # Set to true when served over HTTPS (secure cookies).
    secure_cookies: bool = False
    session_hours: int = 12  # how long a class session stays open by default
    data_retention_days: int = 30  # ended sessions and their content are deleted after this
    teacher_login_days: int = 14
    allow_registration: bool = True

    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # Optional AI moderation via any OpenAI-compatible chat endpoint (e.g. a local Ollama).
    ai_filter_url: str = ""  # e.g. http://localhost:11434/v1/chat/completions
    ai_filter_model: str = ""
    ai_filter_api_key: str = ""

    frontend_dist: str = "../frontend/dist"

    @field_validator("database_url")
    @classmethod
    def _db_default(cls, v: str) -> str:
        return v or "sqlite:///./classpulse.db"

    @property
    def spotify_enabled(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.secret_key:
        import secrets
        import warnings

        warnings.warn(
            "SECRET_KEY is not set - using a random key. Logins and votes reset on every restart.",
            stacklevel=1,
        )
        s.secret_key = secrets.token_urlsafe(48)
    return s
