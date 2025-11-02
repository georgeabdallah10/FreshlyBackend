from typing import List, Optional
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, validator


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Freshly API"
    APP_ENV: str = "local"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    # Security settings
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    # Email configuration
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_FROM_NAME: str = "Freshly Team"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # JWT settings
    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # External services
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE: Optional[str] = None
    AVATARS_BUCKET: Optional[str] = "users"
    
    # AI/OpenAI settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7
    
    # Database configuration
    DATABASE_URL: str
    # Note: Pool settings below are not used with NullPool (default for Supabase)
    # NullPool is used to avoid "MaxClientsInSessionMode" errors
    DATABASE_POOL_SIZE: int = 20  # Kept for backward compatibility
    DATABASE_MAX_OVERFLOW: int = 30  # Kept for backward compatibility
    DATABASE_POOL_TIMEOUT: int = 30  # Kept for backward compatibility

    # API rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    AUTH_RATE_LIMIT: int = 10    # for auth endpoints
    
    # Cache settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default
    
    # CORS configuration
    CORS_ORIGINS: List[str] = Field(default_factory=list)
    ALLOWED_HOSTS: List[str] = Field(default_factory=lambda: ["*"])
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = Field(default_factory=lambda: ["image/jpeg", "image/png", "image/webp"])

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=False,
        env_file_encoding="utf-8"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_csv_origins(cls, v):
        """Parse CORS origins from CSV or list"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or []

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def split_csv_hosts(cls, v):
        """Parse allowed hosts from CSV or list"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or ["*"]

    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def split_csv_file_types(cls, v):
        """Parse allowed file types from CSV or list"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or ["image/jpeg", "image/png", "image/webp"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: str):
        """Validate and clean database URL"""
        if isinstance(v, str):
            v = v.strip().strip('"').strip("'")  # handle quoted values in .env
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v

    @field_validator("APP_ENV")
    @classmethod
    def validate_environment(cls, v: str):
        """Validate application environment"""
        allowed_envs = ["local", "development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"APP_ENV must be one of: {allowed_envs}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {allowed_levels}")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.APP_ENV in ["local", "development"]

    @property
    def openai_enabled(self) -> bool:
        """Check if OpenAI features are available"""
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())


# Global settings instance
settings = Settings()