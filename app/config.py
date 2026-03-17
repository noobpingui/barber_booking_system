from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./barber.db"
    debug: bool = False
    cancellation_window_hours: int = 2  # minimum hours before appointment to allow cancellation

    # Auth — MUST be overridden via .env in production.
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # pydantic-settings will automatically read from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single instance imported directly wherever settings are needed.
settings = Settings()
