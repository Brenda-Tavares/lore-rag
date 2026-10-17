import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import Base

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    QUARANTINE = "quarantine"

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    
    # Security: Track who uploaded to prevent spoofing
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to chunks (Cascade delete ensures data privacy when doc is deleted)
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")