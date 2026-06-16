from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "RAGForge"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_MODE: bool = False  # set to true when Supabase is configured

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant Cloud
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "documents"
    QDRANT_CLOUD_INFERENCE: bool = False  # set true when using Qdrant Cloud inference API

    # Auth / JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # LLM (OpenAI-compatible)
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1

    # Embedding
    EMBEDDING_DIM: int = 384
    EMBEDDING_MODEL: str = "sentence-transformers/all-minilm-l6-v2"
    SPARSE_MODEL: str = "bm25"

    # RAG Pipeline
    CHUNK_DEFAULT_STRATEGY: str = "recursive"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 50
    TOP_K_RERANK: int = 5
    HYBRID_ALPHA: float = 0.5
    RERANKER_ENABLED: bool = True

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt,md,html"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Langfuse
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"
    LANGFUSE_ENABLED: bool = False

    # RAGAS
    RAGAS_ENABLED: bool = False


settings = Settings()
