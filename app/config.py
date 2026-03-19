from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./barber.db"
    debug: bool = False
    cancellation_window_hours: int = 1  # minimum hours before appointment to allow cancellation

    # Auth — MUST be overridden via .env in production.
    secret_key: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # Email notifications — set EMAIL_PROVIDER to "resend" (default) or "ses".
    # Leave email_from empty to disable all email notifications.
    email_provider: str = "resend"
    email_from: str = ""        # e.g. "noreply@booking.betofallas.dev"
    resend_api_key: str = ""    # required when email_provider=resend

    # Amazon SES — only needed when email_provider=ses.
    # Leave aws_access_key_id empty to use the EC2 instance's IAM role instead.
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # pydantic-settings will automatically read from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single instance imported directly wherever settings are needed.
settings = Settings()
