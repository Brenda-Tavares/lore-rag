import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.models.chunk import Chunk
from app.core.security import SecurityRedactor
from app.core.config import settings
from app.services.qdrant_client import QdrantService

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.qdrant = QdrantService()

    async def process_document(self, file_content: str, filename: str, mime_type: str, tenant_id: uuid.UUID, user_id: uuid.UUID):
        """
        Main pipeline to ingest a document securely.
        """
        print(f"[INGESTION] Iniciando processamento de: {filename}")
        
        # 1. Validation
        if not SecurityRedactor.validate_file_type(mime_type):
            raise ValueError("File type not allowed for security reasons.")

        # 2. Create Document Record (Status: Processing)
        doc = Document(
            tenant_id=tenant_id,
            filename=filename,
            mime_type=mime_type,
            uploaded_by=user_id,
            status=DocumentStatus.PROCESSING
        )
        self.db.add(doc)
        self.db.flush()
        print(f"[INGESTION] Document criado com ID: {doc.id}")

        try:
            # 3. SECURITY STEP: Redact Sensitive Data
            clean_content = SecurityRedactor.redact_text(file_content)
            print(f"[INGESTION] Conteúdo sanitizado: {len(clean_content)} caracteres")

            # 4. Chunking
            chunks_text = self._split_text(clean_content)
            print(f"[INGESTION] Documento dividido em {len(chunks_text)} chunks")

            # 5. BATCH: Generate all embeddings in ONE API call (economiza rate limit!)
            print(f"[INGESTION] Gerando {len(chunks_text)} embeddings em batch...")
            from app.services.llm_client import LLMClient
            llm = LLMClient()
            embedding_vectors = await llm.get_embeddings_batch(chunks_text)
            print(f"[INGESTION] {len(embedding_vectors)} embeddings gerados em 1 request!")

            # 6. Create Chunks and Vectors
            for i, (chunk_text, embedding_vector) in enumerate(zip(chunks_text, embedding_vectors), 1):
                print(f"[INGESTION] Processando chunk {i}/{len(chunks_text)}")
                
                # Save chunk to PostgreSQL
                chunk = Chunk(
                    document_id=doc.id,
                    tenant_id=tenant_id,
                    content=chunk_text,
                    metadata_={}
                )
                self.db.add(chunk)
                self.db.flush()
                print(f"[INGESTION] Chunk salvo no PostgreSQL com ID: {chunk.id}")
                
                # Save vector to Qdrant
                print(f"[INGESTION] Salvando vetor no Qdrant...")
                self.qdrant.add_vectors(
                    chunk_id=chunk.id,
                    tenant_id=tenant_id,
                    document_id=doc.id,
                    embedding=embedding_vector
                )
                print(f"[INGESTION] Vetor salvo no Qdrant!")

            # 7. Finalize
            doc.status = DocumentStatus.READY
            self.db.commit()
            print(f"[INGESTION] Documento processado com sucesso! ID: {doc.id}")
            return doc.id

        except Exception as e:
            print(f"[INGESTION] ERRO durante processamento: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
            doc.status = DocumentStatus.FAILED
            self.db.commit()
            raise

    def _split_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Simple sliding window chunker.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks