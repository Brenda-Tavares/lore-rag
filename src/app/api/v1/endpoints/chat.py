from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.deps import get_db
from app.services.rag import RAGService
import uuid

router = APIRouter()

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="The question to ask the knowledge base")

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Query the operational knowledge base.
    """
    # MVP MOCK: In production, extract tenant_id from JWT Token
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    
    rag_service = RAGService(db)
    try:
        result = await rag_service.query_knowledge(request.query, tenant_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request. Please try again in a few minutes.")