from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./barber.db"
    debug: bool = False
    cancellation_window_hours: int = 2  # minimum hours before appointment to allow cancellation

    # Auth — MUST be overridden via .env in production.
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # Amazon SES — leave empty to disable email notifications.
    # If aws_access_key_id is empty, boto3 falls back to the IAM role attached to the EC2 instance.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    ses_from_email: str = "noreply@booking.betofallas.dev"

    # pydantic-settings will automatically read from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single instance imported directly wherever settings are needed.
settings = Settings()
