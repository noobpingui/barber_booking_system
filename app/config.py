from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./barber.db"
    debug: bool = False
    cancellation_window_hours: int = 2  # minimum hours before appointment to allow cancellation

    # pydantic-settings will automatically read from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Single instance imported directly wherever settings are needed.
settings = Settings()
