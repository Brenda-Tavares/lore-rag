from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.base import Base
from app.db.session import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Cria as tabelas no banco de dados automaticamente
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: (Lógica de encerramento, se necessário)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Secure RAG for SRE Knowledge",
    docs_url="/docs",  # Força o Swagger UI a ficar ativo para testes
    redoc_url=None,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default
        "http://127.0.0.1:5173",  # Vite default (alternativo)
        "http://localhost:3000",   # Manter (caso use outra ferramenta depois)
        "http://localhost:8080",   # Manter
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Lore is running. Access /docs for documentation.",
        "security_warning": "Do not input sensitive credentials into prompts."
    }