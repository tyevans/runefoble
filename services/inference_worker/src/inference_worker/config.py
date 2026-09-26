"""Configuration settings for Runefoble AI Inference Worker."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Runtime configuration for inference worker."""

    model_config = SettingsConfigDict(
        env_prefix="RUNEFOBLE_WORKER_",
        env_file=".env.worker",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8100, description="Listen port")
    log_level: str = Field(default="INFO", description="Log level")

    backend: Literal["auto", "openai_compatible", "ollama", "mock"] = Field(
        default="auto",
        description="Inference backend engine: auto (detects available server), openai_compatible, ollama, or mock",
    )

    # OpenAI-compatible backend (llama-swap, vLLM, llama.cpp, etc.)
    openai_base_url: str = Field(
        default="http://127.0.0.1:8080/v1",
        description="Base URL for OpenAI-compatible endpoint",
    )
    openai_model: str = Field(
        default="granite-4.2-3b",
        description="Target model name on OpenAI-compatible endpoint",
    )
    openai_api_key: SecretStr = Field(
        default=SecretStr("not-required"),
        description="API Key if needed",
    )

    # Ollama backend
    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for Ollama service",
    )
    ollama_model: str = Field(
        default="qwen3.5:9b",
        description="Target Ollama model",
    )

    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    timeout_seconds: float = Field(default=30.0, gt=0.0)

    # Redis Streams integration
    redis_enabled: bool = Field(default=False, description="Enable Redis Streams consumer")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0")
    redis_stream_in: str = Field(default="runefoble.inference.requests")
    redis_stream_out: str = Field(default="runefoble.inference.results")
    redis_consumer_group: str = Field(default="runefoble-inference-workers")
    redis_consumer_name: str = Field(default="worker-01")
