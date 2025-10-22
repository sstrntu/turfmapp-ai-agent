"""
RAG API Endpoints

Endpoints for document upload, management, and RAG queries.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel, Field

from ...core.jwt_auth import get_current_user_from_token
from ...database import get_db_pool
from ...llamaindex.rag import DocumentIngestionService, PgVectorStore, RAGQueryService
from ...llamaindex.services.llm_factory import llm_factory, TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


# Request/Response Models
class DocumentUploadRequest(BaseModel):
    """Document upload request"""
    document_scope: str = Field(default="personal", pattern="^(personal|organization)$")


class RAGQueryRequest(BaseModel):
    """RAG query request"""
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    include_sources: bool = True
    include_organization_docs: bool = Field(default=True, description="Include organization-wide documents in search")


class RAGQueryResponse(BaseModel):
    """RAG query response"""
    answer: str
    sources: list
    chunks_found: int


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    document_id: str
    filename: str
    chunk_count: int
    status: str


# Service Instances
async def get_ingestion_service() -> DocumentIngestionService:
    """Get document ingestion service instance"""
    db_pool = await get_db_pool()
    return DocumentIngestionService(
        chunk_size=1024,  # Increased from 512 for better context
        chunk_overlap=128,  # Increased from 50 for better chunk continuity
        db_pool=db_pool
    )


async def get_vector_store() -> PgVectorStore:
    """Get vector store instance"""
    db_pool = await get_db_pool()
    return PgVectorStore(db_pool=db_pool)


async def get_rag_service() -> RAGQueryService:
    """Get RAG query service instance"""
    vector_store = await get_vector_store()
    llm = llm_factory.create_llm(
        model_id=llm_factory.recommend_model_for_task(TaskType.CHAT),
        temperature=0.3  # Lower temp for factual answers
    )
    return RAGQueryService(
        vector_store=vector_store,
        llm=llm,
        top_k=5,
        similarity_threshold=0.7
    )


# Endpoints
@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_scope: str = "personal",
    current_user: dict = Depends(get_current_user_from_token),
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service),
    vector_store: PgVectorStore = Depends(get_vector_store)
):
    """
    Upload a document for RAG.

    Supported formats: TXT, PDF, MD, DOCX
    Max size: 50MB

    The document will be:
    1. Validated and extracted
    2. Split into chunks
    3. Embedded and stored in vector database

    Example:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/rag/upload" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@document.pdf"
    ```
    """
    try:
        user_id = current_user["id"]

        # Validate document_scope
        if document_scope not in ("personal", "organization"):
            raise HTTPException(
                status_code=400,
                detail="document_scope must be 'personal' or 'organization'"
            )

        # Read file content
        file_content = await file.read()

        # Ingest document
        result = await ingestion_service.ingest_document(
            file_content=file_content,
            filename=file.filename,
            user_id=user_id,
            metadata={"document_scope": document_scope}
        )

        # Generate embeddings
        db_pool = await get_db_pool()
        logger.info(f"📝 Fetching chunks for document_id={result['document_id']}")
        async with db_pool.acquire() as conn:
            # Get all chunks for this document
            rows = await conn.fetch(
                """
                SELECT id, content, metadata
                FROM turfmapp_agent.document_nodes
                WHERE document_id = $1
                ORDER BY chunk_index
                """,
                result['document_id']
            )
            logger.info(f"📝 Found {len(rows)} chunks, IDs: {[str(row['id']) for row in rows[:3]]}...")

            # Create TextNodes
            from llama_index.core.schema import TextNode
            import json

            nodes = []
            for row in rows:
                node = TextNode(
                    id_=str(row['id']),  # Use id_ not node_id!
                    text=row['content'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                nodes.append(node)

            logger.info(f"📝 Created {len(nodes)} TextNodes, first node_id={nodes[0].node_id if nodes else 'none'}")
            # Add embeddings
            await vector_store.add_nodes(nodes)

        logger.info(f"Document uploaded: {file.filename}, user={user_id}")

        return DocumentUploadResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    current_user: dict = Depends(get_current_user_from_token),
    rag_service: RAGQueryService = Depends(get_rag_service)
):
    """
    Ask a question using RAG (Retrieval-Augmented Generation).

    The AI will search your uploaded documents and answer based on their content.

    Example:
    ```python
    {
        "question": "What is the main topic of my documents?",
        "top_k": 5,
        "include_sources": true
    }
    ```
    """
    try:
        user_id = current_user["id"]

        result = await rag_service.query(
            question=request.question,
            user_id=user_id,
            include_sources=request.include_sources,
            include_organization_docs=request.include_organization_docs
        )

        logger.info(f"RAG query: user={user_id}, chunks_found={result['chunks_found']}")

        return RAGQueryResponse(**result)

    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/documents")
async def list_documents(
    current_user: dict = Depends(get_current_user_from_token),
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """
    List all uploaded documents for the current user.

    Returns document metadata including:
    - Filename
    - Upload date
    - Chunk count
    - Processing status
    """
    try:
        user_id = current_user["id"]

        documents = await ingestion_service.get_user_documents(user_id=user_id)

        return {
            "documents": documents,
            "total": len(documents)
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user_from_token),
    ingestion_service: DocumentIngestionService = Depends(get_ingestion_service)
):
    """
    Delete a document and all its chunks.

    This will permanently remove:
    - Document metadata
    - All text chunks
    - All embeddings
    """
    try:
        user_id = current_user["id"]

        success = await ingestion_service.delete_document(
            document_id=document_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user_from_token),
    vector_store: PgVectorStore = Depends(get_vector_store)
):
    """
    Get RAG statistics for the current user.

    Returns:
    - Total documents
    - Total chunks
    - Embedding coverage
    - Average chunk length
    """
    try:
        user_id = current_user["id"]

        stats = await vector_store.get_embedding_stats(user_id=user_id)

        return stats

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
