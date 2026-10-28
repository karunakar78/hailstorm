from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres@localhost:5432/hailstorm"
    DATABASE_ECHO: bool = False
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAX_REQUEST_RATE: float = 1000.0
    MAX_DURATION_SECONDS: int = 86400


settings = Settings()
