from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "Autonomous AI Customer Support & Resolution Agent"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Supabase Infrastructure (Configured in Level 3)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    DATABASE_URL: str = ""

    # Free Local RAG & Embedding Settings (Level 4 - 100% Free & Open Source)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384
    RAG_SIMILARITY_THRESHOLD: float = 0.65
    RAG_TOP_K: int = 3

    # Demo Customer Session & Authentication
    SESSION_SECRET_KEY: str = "demo-insecure-secret-key-change-in-env"
    SESSION_EXPIRE_MINUTES: int = 1440

    # Free Hosted LLM & Agent Provider Settings (Level 5 - 100% Free Developer Tier)
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TEMPERATURE: float = 0.1
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"




settings = Settings()
