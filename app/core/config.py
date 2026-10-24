from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    PROJECT_NAME: str = "Site Report API"

    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str

    SECRET_KEY: str

    ALGORITHM: str = "HS256"

    # Short-lived access tokens: there is no server-side revocation for them,
    # so a stolen access token is only useful until it expires.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_EMAIL: str

    ADMIN_PASSWORD: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SMTP_SSL: bool

    STRIPE_SECRET_KEY: str

    STRIPE_PUBLISHABLE_KEY: str

    STRIPE_WEBHOOK_SECRET: str

    # Comma separated list of browser origins allowed to call the API
    # (the admin panel and the public web pages).
    CORS_ORIGINS: str = "https://admin.sitesreports.com,https://sitesreports.com,https://www.sitesreports.com"

    # Public URLs used for Stripe redirects and the customer portal.
    ADMIN_PUBLIC_URL: str = "https://admin.sitesreports.com"

    WEB_PUBLIC_URL: str = "https://sitesreports.com"

    # PEM encoded Apple Root CA (AppleRootCA-G3). Required to verify StoreKit
    # JWS tokens. Apple purchases are rejected while this is not configured.
    APPLE_ROOT_CA_PATH: str = ""

    APPLE_BUNDLE_ID: str = ""

    # Optional demo account for App Store / Google Play review. Leave both empty to disable it.
    # When set, this one email logs in with the fixed 6-digit code below instead of an emailed OTP.
    # Use a throwaway non-admin account that holds no real data.
    REVIEW_ACCOUNT_EMAIL: str = ""

    REVIEW_ACCOUNT_OTP: str = ""

    # Maximum size of an uploaded report PDF, in bytes.
    MAX_REPORT_PDF_BYTES: int = 15 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @field_validator("REVIEW_ACCOUNT_OTP")
    @classmethod
    def _review_otp_is_six_digits(cls, value: str) -> str:
        if value and not (len(value) == 6 and value.isdigit()):
            raise ValueError("REVIEW_ACCOUNT_OTP must be exactly 6 digits")
        return value

    @property
    def review_account_enabled(self) -> bool:
        return bool(self.REVIEW_ACCOUNT_EMAIL.strip() and self.REVIEW_ACCOUNT_OTP)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
