from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from app.core.config import settings
import uuid
from typing import List, Dict, Any

class QdrantService:
    def __init__(self):
        # Local Qdrant - stores data in a folder
        self.client = QdrantClient(path=settings.QDRANT_PATH)
        self.collection_name = "lore_chunks"
        
        # Create collection if it doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Create the collection if it doesn't exist."""
        collections = [c.name for c in self.client.get_collections().collections]
        
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1024,  # liquid/lfm-2.5-embedding-350m:free
                    distance=Distance.COSINE
                )
            )

    def add_vectors(self, chunk_id: uuid.UUID, tenant_id: uuid.UUID, document_id: uuid.UUID, embedding: List[float]):
        """
        Add a vector to Qdrant with tenant isolation metadata.
        """
        print(f"[QDRANT] add_vectors chamado:")
        print(f"  - chunk_id: {chunk_id}")
        print(f"  - tenant_id: {tenant_id}")
        print(f"  - document_id: {document_id}")
        print(f"  - embedding: {len(embedding)} dimensões")
        
        point = PointStruct(
            id=str(chunk_id),
            vector=embedding,
            payload={
                "chunk_id": str(chunk_id),
                "tenant_id": str(tenant_id),
                "document_id": str(document_id)
            }
        )
        
        print(f"[QDRANT] Chamando client.upsert...")
        result = self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        print(f"[QDRANT] Upsert result: {result}")
        
        # Verificar se foi adicionado
        collection_info = self.client.get_collection(self.collection_name)
        print(f"[QDRANT] Total de pontos na collection: {collection_info.points_count}")

    def search_vectors(self, query_embedding: List[float], tenant_id: uuid.UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar vectors, filtered by tenant_id (CRITICAL SECURITY).
        Uses the new query_points API from qdrant-client 1.16+
        """
        # Security: Filter by tenant_id to prevent cross-tenant data leakage
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=str(tenant_id))
                )
            ]
        )
        
        # Nova API: query_points em vez de search
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=search_filter,
            limit=limit
        )
        
        # Extrair pontos do response
        results = response.points if hasattr(response, 'points') else []
        
        return [
            {
                "chunk_id": result.payload["chunk_id"],
                "score": result.score if hasattr(result, 'score') else 0.0
            }
            for result in results
        ]

    def delete_vectors(self, chunk_ids: List[uuid.UUID]):
        """
        Delete vectors from Qdrant (for data privacy when documents are deleted).
        Updated for qdrant-client 1.16+ API
        """
        if not chunk_ids:
            return
        
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="chunk_id",
                    match=MatchAny(any=[str(cid) for cid in chunk_ids])
                )
            ]
        )
        
        # Nova API: delete_points em vez de delete
        self.client.delete_points(
            collection_name=self.collection_name,
            points_selector=delete_filter
        )