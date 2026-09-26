"""Runefoble Platform Configuration.

Centralizes configuration settings across bounded contexts.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """Platform-wide environment configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_",
        env_file=".env",
        extra="ignore",
    )

    # Core
    environment: str = Field(
        default="development", description="Environment: development, staging, production"
    )
    service_name: str = Field(default="runefoble", description="Service identifier")
    debug: bool = Field(default=True, description="Enable debug logging")

    # Database (PostgreSQL)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/runefoble",
        description="Postgres async connection string",
    )

    # Cache & Event Streaming (Redis)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("RUNEFOBLE_REDIS_URL", "REDIS_URL"),
        description="Redis connection string",
    )

    # Object Storage (Silo / MinIO fork)
    silo_endpoint: str = Field(default="localhost:9000", description="Silo S3 endpoint")
    silo_access_key: str = Field(default="silo_admin", description="Silo access key")
    silo_secret_key: str = Field(default="silo_secret_pass", description="Silo secret key")
    silo_bucket_assets: str = Field(default="runefoble-assets", description="Silo assets bucket")
    silo_secure: bool = Field(default=False, description="Use TLS for Silo")

    # Identity & AuthN (Zitadel)
    zitadel_issuer: str = Field(
        default="http://localhost:8080",
        description="Zitadel self-hosted issuer URL",
    )
    zitadel_client_id: str = Field(
        default="runefoble-api",
        description="Zitadel OAuth client ID",
    )
    auth_dev_mode: bool = Field(
        default=True,
        validation_alias=AliasChoices("RUNEFOBLE_AUTH_DEV_MODE", "AUTH_DEV_MODE"),
        description="Enable offline development auth bypass",
    )
    zitadel_jwks_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RUNEFOBLE_ZITADEL_JWKS_URL", "ZITADEL_JWKS_URL"),
        description="Zitadel JWKS keys endpoint URL",
    )

    # Authorization & Zanzibar (SpiceDB)
    spicedb_endpoint: str = Field(
        default="localhost:50051",
        description="SpiceDB gRPC endpoint",
    )
    spicedb_preshared_key: str = Field(
        default="runefoble_secret_key",
        description="SpiceDB preshared authentication token",
    )

    # Analytics (OpenPanel)
    openpanel_endpoint: str = Field(
        default="http://localhost:3000/api",
        description="OpenPanel analytics endpoint",
    )
    openpanel_client_id: str | None = Field(
        default=None,
        description="OpenPanel project client ID",
    )

    # Observability (OpenTelemetry / Grafana / Loki)
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTel collector / Loki gRPC endpoint",
    )
    loki_endpoint: str = Field(
        default="http://localhost:3100",
        description="Grafana Loki endpoint",
    )
