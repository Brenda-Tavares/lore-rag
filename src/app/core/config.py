from pydantic_settings import BaseSettings
from pathlib import Path

# Caminho absoluto para a raiz do projeto
# __file__ = src/app/core/config.py
# 4x parent = C:\projetos\lore-rag\
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Lore"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str
    
    # Qdrant
    QDRANT_PATH: str = "./qdrant_storage"
    
    # AI & OpenRouter (para embeddings)
    OPENROUTER_API_KEY: str
    DEFAULT_LLM_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Groq (para chat)
    GROQ_API_KEY: str = ""
    
    # Security Limits
    MAX_CHUNKS_PER_QUERY: int = 5
    RATE_LIMIT_PER_MINUTE: int = 10
    SECRET_KEY: str = "change-this-in-production"
    
    class Config:
        # Aponta explicitamente para o .env na raiz do projeto
        env_file = _PROJECT_ROOT / ".env"
        case_sensitive = True

settings = Settings()