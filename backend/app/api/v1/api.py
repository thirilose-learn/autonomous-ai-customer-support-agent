from fastapi import APIRouter
from app.api.v1.endpoints import health, rag, auth, chat

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Demo Session"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG & Knowledge Base"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Support Agent & Chat"])


