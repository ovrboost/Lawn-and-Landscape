from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lawn:lawn@db:5432/lawn"
    # Used once, to create the login the first time the app starts.
    app_password: str = "change-me"
    # Signs session cookies and encrypts the Gmail app password. Keep it secret and stable.
    secret_key: str = "dev-only-change-me"
    # True when served over HTTPS (Tailscale). Set false only for local http testing.
    cookie_secure: bool = True
    timezone: str = "America/Chicago"
    business_name: str = "My Lawn Care"
    base_address: str = "1213 Arbor Ln, Pacific, MO 63069"
    static_dir: str = "static"


config = Config()
