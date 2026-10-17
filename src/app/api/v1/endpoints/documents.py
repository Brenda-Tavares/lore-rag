from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ingestion import IngestionService
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a runbook or postmortem for ingestion.
    """
    # MVP MOCK: In production, extract user/tenant from JWT
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    
    # Basic validation
    if file.content_type not in ["text/plain", "text/markdown"]:
        raise HTTPException(status_code=400, detail="Only .txt or .md files allowed for this MVP")

    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding")

    service = IngestionService(db)
    try:
        doc_id = await service.process_document(
            file_content=text_content,
            filename=file.filename,
            mime_type=file.content_type,
            tenant_id=tenant_id,
            user_id=user_id
        )
        return {"document_id": str(doc_id), "status": "ingested"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))