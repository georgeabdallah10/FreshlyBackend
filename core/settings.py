from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Freshly API"
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    # add fields if missing
    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str

    # Accept CSV string or JSON array
    CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

settings = Settings()