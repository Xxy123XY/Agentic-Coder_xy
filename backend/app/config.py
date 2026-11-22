from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "multi-agent-orchestrator"
    debug: bool = False

    # Groq LLM (free tier)
    groq_api_key: str
    groq_reason_model: str = "openai/gpt-oss-120b"
    groq_code_model: str = "openai/gpt-oss-120b"

    # Ollama (optional local fallback)
    ollama_base_url: str = "http://localhost:11434"
    ollama_enabled: bool = False

    # RAG embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist_dir: str = "./data/chroma"

    # GitHub
    github_token: str
    github_webhook_secret: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/orchestrator.db"

    # Docker sandbox limits
    sandbox_image: str = "python:3.12-slim"
    sandbox_timeout: int = 120
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: float = 0.5

    # LangGraph
    checkpointer_db: str = "./data/checkpoints.db"
    max_retries: int = 3

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Cached so .env is read only once, not on every import."""
    return Settings()