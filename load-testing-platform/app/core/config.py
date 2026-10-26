from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres@localhost:5432/hailstorm"
    DATABASE_ECHO: bool = False


settings = Settings()
