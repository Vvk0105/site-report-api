from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    PROJECT_NAME: str = "Site Report API"

    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str

    SECRET_KEY: str

    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_EMAIL: str

    ADMIN_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
