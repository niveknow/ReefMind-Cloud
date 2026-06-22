from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://reefmind:reefmind@postgres:5432/reefmind"

    # InfluxDB
    influx_url: str = "http://influxdb:8086"
    influx_token: str = "reefmind-admin-token"
    influx_org: str = "reefmind"
    influx_bucket: str = "reefmind_dev"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    jwt_secret: str = "reefmind-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # App
    api_url: str = "http://localhost:8000"
    web_url: str = "http://localhost:5173"
    app_name: str = "ReefMind"
    debug: bool = True

    # Email (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@reefmind.io"

    # Nemo AI
    nemo_api_key: str = ""
    nemo_model: str = "gemini-3.1-flash-lite"
    nemo_provider: str = "gemini"

    model_config = {"env_prefix": "REEFMIND_", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
