import uuid
from sqlalchemy import Column, String, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # CRITICAL SECURITY FIELD: Isolation at the database level
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    
    # Store metadata as JSONB for flexible filtering
    metadata_ = Column("metadata", JSON, nullable=True)

    document = relationship("Document", back_populates="chunks")