"""Runefoble Platform Configuration.

Centralizes configuration settings across bounded contexts.
"""

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Environments where a missing dependency must stop a service at start-up (ADR-0015 4).
DEPLOYED_ENVIRONMENTS = frozenset({"staging", "production"})


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

    # Database (PostgreSQL) & Event Store
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/runefoble",
        validation_alias=AliasChoices("RUNEFOBLE_DATABASE_URL", "DATABASE_URL"),
        description="Postgres async connection string",
    )
    event_store_backend: Literal["postgresql", "memory"] = Field(
        default="postgresql",
        description=(
            "Event store backend. postgresql is the default. memory is for tests and explicit "
            "injection only, and deployed environments refuse it (ADR-0015 4)."
        ),
    )
    postgres_pool_size: int = Field(
        default=5,
        validation_alias=AliasChoices("RUNEFOBLE_POSTGRES_POOL_SIZE", "POSTGRES_POOL_SIZE"),
        description="PostgreSQL connection pool size",
    )
    postgres_max_overflow: int = Field(
        default=10,
        validation_alias=AliasChoices("RUNEFOBLE_POSTGRES_MAX_OVERFLOW", "POSTGRES_MAX_OVERFLOW"),
        description="PostgreSQL connection pool max overflow",
    )
    event_store_table_name: str = Field(
        default="runefoble_events",
        validation_alias=AliasChoices("RUNEFOBLE_EVENT_STORE_TABLE_NAME", "EVENT_STORE_TABLE_NAME"),
        description="Table name for event store events",
    )

    @model_validator(mode="after")
    def _default_audience_to_client_id(self) -> "PlatformSettings":
        if not self.zitadel_audience:
            self.zitadel_audience = self.zitadel_client_id
        return self

    @property
    def is_deployed(self) -> bool:
        """True when the environment is a deployed one (staging or production)."""
        return self.environment in DEPLOYED_ENVIRONMENTS

    @property
    def postgres_dsn(self) -> str:
        """Alias for database_url for backward compatibility."""
        return self.database_url

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

    # Gateway CORS: comma-separated browser origins that may call the API with credentials.
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated allowed CORS origins. Never '*' with credentials.",
    )

    # Identity & AuthN (Zitadel)
    zitadel_issuer: str = Field(
        default="http://localhost:8080",
        description="Zitadel self-hosted issuer URL",
    )
    zitadel_client_id: str = Field(
        default="runefoble-api",
        description="Zitadel OAuth client ID",
    )
    zitadel_audience: str = Field(
        default="",
        validation_alias=AliasChoices("RUNEFOBLE_ZITADEL_AUDIENCE", "ZITADEL_AUDIENCE"),
        description="Expected 'aud' claim. Empty means use zitadel_client_id.",
    )
    zitadel_internal_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RUNEFOBLE_ZITADEL_INTERNAL_URL"),
        description=(
            "Origin that serves Zitadel inside the cluster, for example http://zitadel:8080. "
            "Discovery and JWKS requests go here with Host set to the issuer host. Empty means "
            "the issuer serves them directly."
        ),
    )

    # Service-to-service credential (ADR-0015 e). No default value. The caller presents it in
    # the X-Runefoble-Service-Credential header. The receiver refuses to start without it.
    service_credential: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("RUNEFOBLE_SERVICE_CREDENTIAL"),
        description="Service credential shared by services and the MCP gateway (Kubernetes Secret)",
    )

    # Authorization & Zanzibar (SpiceDB)
    spicedb_endpoint: str = Field(
        default="localhost:50051",
        validation_alias=AliasChoices("RUNEFOBLE_SPICEDB_ENDPOINT", "SPICEDB_ENDPOINT"),
        description="SpiceDB gRPC endpoint",
    )
    spicedb_preshared_key: str = Field(
        validation_alias=AliasChoices("RUNEFOBLE_SPICEDB_PRESHARED_KEY"),
        description="SpiceDB preshared key (operator secret). No default; required at startup",
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
    otel_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("RUNEFOBLE_OTEL_ENABLED", "OTEL_ENABLED"),
        description="Enable OpenTelemetry tracing and metrics export",
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        validation_alias=AliasChoices(
            "RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT"
        ),
        description="OTel collector / Loki gRPC endpoint",
    )
    loki_endpoint: str = Field(
        default="http://localhost:3100",
        validation_alias=AliasChoices("RUNEFOBLE_LOKI_ENDPOINT", "LOKI_ENDPOINT"),
        description="Grafana Loki endpoint",
    )

    # Email & SMTP Testing (Mailpit)
    mailpit_smtp_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("RUNEFOBLE_MAILPIT_SMTP_HOST", "MAILPIT_SMTP_HOST"),
        description="Mailpit SMTP host for email testing",
    )
    mailpit_smtp_port: int = Field(
        default=1025,
        validation_alias=AliasChoices("RUNEFOBLE_MAILPIT_SMTP_PORT", "MAILPIT_SMTP_PORT"),
        description="Mailpit SMTP port",
    )
    mailpit_http_url: str = Field(
        default="http://localhost:8025",
        validation_alias=AliasChoices("RUNEFOBLE_MAILPIT_HTTP_URL", "MAILPIT_HTTP_URL"),
        description="Mailpit HTTP Web UI and API base URL",
    )
    mailpit_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("RUNEFOBLE_MAILPIT_ENABLED", "MAILPIT_ENABLED"),
        description="Whether Mailpit email testing is enabled",
    )

    # Gateway upstream base URLs. A None value means the gateway has no route to that
    # service, and a proxy call to it returns 503. game_session reads the character sheet
    # URL from this same field, so both processes share one variable name. The other names
    # follow the RUNEFOBLE_<SERVICE>_URL pattern or the names that Helm renders for gateway-api.
    game_session_url: str | None = Field(
        default=None, description="Base URL of the game_session service"
    )
    board_state_url: str | None = Field(
        default=None, description="Base URL of the board_state service"
    )
    the_watcher_url: str | None = Field(
        default=None, description="Base URL of the the_watcher service"
    )
    character_sheet_url: str | None = Field(
        default=None,
        description="Base URL of the character_sheet service (RUNEFOBLE_CHARACTER_SHEET_URL)",
    )
    campaign_lore_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CAMPAIGN_LORE_URL"),
        description="Base URL of the campaign_lore service",
    )
    campaign_analytics_url: str | None = Field(
        default="http://campaign-analytics:8011",
        validation_alias=AliasChoices("CAMPAIGN_ANALYTICS_URL"),
        description="Base URL of the campaign_analytics service",
    )
    soundscape_url: str | None = Field(
        default="http://soundscape:8009",
        validation_alias=AliasChoices("SOUNDSCAPE_SERVICE_URL"),
        description="Base URL of the soundscape service",
    )
    rules_compendium_url: str | None = Field(
        default=None, description="Base URL of the rules_compendium service"
    )
    asset_forge_url: str | None = Field(
        default=None, description="Base URL of the asset_forge service"
    )
    voice_agent_url: str | None = Field(
        default=None, description="Base URL of the voice_agent service"
    )
    audience_studio_url: str | None = Field(
        default=None, description="Base URL of the audience_studio service"
    )


class EmbeddingEndpointSettings(BaseSettings):
    """Connection settings for an OpenAI-compatible embeddings endpoint.

    Read by the embedding provider factory in `libs/runefoble_embeddings`. Any
    service that selects a provider reads these values. Fields that a provider
    needs are checked when the provider is built, so a missing value stops start-up.
    """

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_EMBEDDING_",
        env_file=".env",
        extra="ignore",
    )

    base_url: str | None = Field(
        default=None,
        description="Base URL of the embeddings API, including the /v1 path",
    )
    model: str | None = Field(
        default=None,
        description="Model name sent to the endpoint and recorded as provenance",
    )
    dimension: int | None = Field(
        default=None,
        description="Vector width the model produces; checked on the first embedding",
    )
    api_key: str = Field(
        default="not-needed",
        description="Bearer key for the endpoint. Local servers usually ignore it",
    )
    document_prefix: str = Field(
        default="",
        description="Text prepended to every indexed document (asymmetric models)",
    )
    query_prefix: str = Field(
        default="",
        description="Text prepended to every search query (asymmetric models)",
    )


class RulesCompendiumSettings(BaseSettings):
    """Rules Compendium retrieval mode.

    `lexical` ranks rules with BM25 only, and search responses say so. Any other
    value names a configured embedding provider, and search becomes hybrid.
    """

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_RULES_",
        env_file=".env",
        extra="ignore",
    )

    embedding: Literal["lexical", "openai_compatible"] = Field(
        default="lexical",
        description="Retrieval mode: lexical (BM25 only) or a configured embedding provider",
    )


class LoreBackendSettings(BaseSettings):
    """Campaign Lore retrieval backends, selected per port.

    The entity vector index lives in PostgreSQL (pgvector) and the embeddings come
    from a configured OpenAI-compatible endpoint (`EmbeddingEndpointSettings`). There
    is no in-process vector index and no fake embedder in production settings
    (ADR-0015). Start-up fails when either backend is unreachable.
    """

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_LORE_",
        env_file=".env",
        extra="ignore",
    )

    graph: Literal["projection"] = Field(
        default="projection",
        description="Entity graph, rebuilt from LoreDocument events at start-up",
    )
    vector: Literal["pgvector"] = Field(
        default="pgvector",
        description="Entity vectors in PostgreSQL (pgvector) on the platform database",
    )
    chunk: Literal["memory"] = Field(
        default="memory",
        description="Passage corpus for BM25 and dense search, rebuilt at start-up (in process)",
    )
    embedding: Literal["openai_compatible"] = Field(
        default="openai_compatible",
        description="Embedding provider: an OpenAI-compatible /v1/embeddings endpoint",
    )


class WardrobeGeneratorSettings(BaseSettings):
    """Wardrobe image generator for Asset Forge, selected at start-up.

    Only the deterministic placeholder exists today. It draws a flat colour portrait
    and preserves no face. Other choices arrive with their adapters.
    """

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_WARDROBE_",
        env_file=".env",
        extra="ignore",
    )

    generator: Literal["placeholder"] = Field(
        default="placeholder",
        description="Wardrobe generator behind the WardrobeGenerator port",
    )
