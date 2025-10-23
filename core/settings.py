from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    APP_NAME: str = "Freshly API"
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Freshly Team"
    MAIL_STARTTLS: bool =True
    MAIL_SSL_TLS: bool =False

    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE: str | None = None
    AVATARS_BUCKET: str | None = "users"

    DATABASE_URL: str

    # Accept CSV string or JSON array. Use default_factory to avoid mutable default
    CORS_ORIGINS: List[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: str):
        if isinstance(v, str):
            v = v.strip().strip('"').strip("'")  # handle quoted values in .env
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

settings = Settings()