import os
from pydantic import AliasChoices, Field, model_validator
from typing import Optional, List
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url, URL

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/custos"
DEFAULT_TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/custos_test"

SERVICE_NAME = "custos-api"


class Settings(BaseSettings):
    app_name: str = SERVICE_NAME
    otel_enabled: bool = Field(default=False, json_schema_extra={"env": "OTEL_ENABLED"})
    database_url: Optional[str] = None  # Will be set dynamically
    database_pool_size: int = Field(
        default=10, json_schema_extra={"env": "DATABASE_POOL_SIZE"}
    )
    database_max_overflow: int = Field(
        default=20, json_schema_extra={"env": "DATABASE_MAX_OVERFLOW"}
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    disable_auth: bool = Field(default=False, json_schema_extra={"env": "DISABLE_AUTH"})
    rollbar_access_token: Optional[str] = Field(
        default=None, json_schema_extra={"env": "ROLLBAR_ACCESS_TOKEN"}
    )  # Optional field
    super_user_email: Optional[str] = Field(
        default=None, json_schema_extra={"env": "SUPER_USER_EMAIL"}
    )  # Optional field for super user setup (comma-separated list)

    oidc_domain: str = "test.oidc.com"
    oidc_api_audience: str = "https://test-api"
    oidc_issuer: str = "https://test.oidc.com/"
    oidc_algorithms: str = "RS256"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = SERVICE_NAME.lower()
    redis_host: str = Field(
        default="localhost", json_schema_extra={"env": "REDIS_HOST"}
    )
    redis_port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    redis_namespace: str = Field(
        default="llama_index", json_schema_extra={"env": "REDIS_NAMESPACE"}
    )
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    identies_api_url: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "IDENTIES_API_URL"},
    )
    db_app_name: str = Field(
        default="custos-api",
        json_schema_extra={"env": "DB_APP_NAME"},
    )

    @model_validator(mode="before")
    def set_database_url(cls, values):
        """Set the database_url dynamically based on the environment field."""
        environment = values.get("environment", os.getenv("ENV", "development"))
        if environment.lower() == "test":
            values["database_url"] = os.getenv(
                "TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL
            )
        else:
            values["database_url"] = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

        return values

    def get_super_user_emails(self) -> List[str]:
        """Parse the super_user_email setting into a list of emails.

        Returns:
            List of email addresses, stripped of whitespace.
            Returns empty list if super_user_email is None or empty.
        """
        if not self.super_user_email:
            return []

        # Split by comma and strip whitespace from each email
        emails = [email.strip() for email in self.super_user_email.split(",")]
        # Filter out empty strings
        return [email for email in emails if email]

    @property
    def is_production(self) -> bool:
        """Check if the current environment is production."""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if the current environment is test."""
        return self.environment.lower() == "test"

    @property
    def database_url_obj(self) -> URL:
        """Return the database URL as a URL object using sqlalchemy's make_url."""
        if not self.database_url:
            raise ValueError("Database URL is not set.")
        return make_url(self.database_url)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra environment variables


def get_settings() -> Settings:
    """Get application settings with required environment variables."""
    return Settings()
