"""
Document Ingestion Service

Handles uploading, processing, and chunking documents for RAG.
Supports: PDF, TXT, DOCX, MD
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Service for ingesting and processing documents.

    Features:
    - File validation and type detection
    - Text extraction from various formats
    - Intelligent chunking with overlap
    - Metadata preservation
    """

    SUPPORTED_EXTENSIONS = {'.txt', '.pdf', '.md', '.docx'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        db_pool: Optional[Any] = None
    ):
        """
        Initialize document ingestion service.

        Args:
            chunk_size: Size of text chunks (in characters)
            chunk_overlap: Overlap between chunks
            db_pool: Database connection pool
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.db_pool = db_pool

        # Initialize text splitter
        self.text_splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    async def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest a document: validate, extract text, chunk, and save.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            user_id: User ID
            metadata: Optional additional metadata

        Returns:
            Document ingestion result with document_id and chunk count
        """
        try:
            # Validate file
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(
                    f"Unsupported file type: {file_ext}. "
                    f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
                )

            if len(file_content) > self.MAX_FILE_SIZE:
                raise ValueError(
                    f"File too large: {len(file_content)} bytes. "
                    f"Max size: {self.MAX_FILE_SIZE} bytes"
                )

            # Extract text from file
            text = await self._extract_text(file_content, file_ext)

            if not text or len(text.strip()) < 10:
                raise ValueError("Document contains no extractable text")

            # Create document record in database
            document_id = str(uuid.uuid4())
            await self._save_document_metadata(
                document_id=document_id,
                user_id=user_id,
                filename=filename,
                file_type=file_ext,
                file_size=len(file_content),
                metadata=metadata or {}
            )

            # Create LlamaIndex document
            doc = Document(
                text=text,
                metadata={
                    "filename": filename,
                    "file_type": file_ext,
                    "user_id": user_id,
                    "document_id": document_id,
                    **(metadata or {})
                }
            )

            # Split into chunks
            nodes = self.text_splitter.get_nodes_from_documents([doc])

            # Save chunks to database
            await self._save_document_chunks(
                document_id=document_id,
                user_id=user_id,
                nodes=nodes
            )

            # Update document status
            await self._update_document_status(
                document_id=document_id,
                status='ready',
                chunk_count=len(nodes)
            )

            logger.info(
                f"Document ingested: {filename}, "
                f"chunks={len(nodes)}, user={user_id}"
            )

            return {
                "document_id": document_id,
                "filename": filename,
                "chunk_count": len(nodes),
                "status": "ready"
            }

        except Exception as e:
            logger.error(f"Failed to ingest document: {e}", exc_info=True)
            if 'document_id' in locals():
                await self._update_document_status(
                    document_id=document_id,
                    status='failed',
                    error=str(e)
                )
            raise

    async def _extract_text(self, file_content: bytes, file_ext: str) -> str:
        """Extract text from different file formats."""

        if file_ext == '.txt' or file_ext == '.md':
            # Plain text files
            return file_content.decode('utf-8')

        elif file_ext == '.pdf':
            # PDF extraction
            try:
                import pypdf
                pdf_file = io.BytesIO(file_content)
                reader = pypdf.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
                return text
            except ImportError:
                raise ImportError(
                    "pypdf is required for PDF support. "
                    "Install with: pip install pypdf"
                )

        elif file_ext == '.docx':
            # Word document extraction
            try:
                import docx
                doc_file = io.BytesIO(file_content)
                doc = docx.Document(doc_file)
                text = "\n\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                raise ImportError(
                    "python-docx is required for DOCX support. "
                    "Install with: pip install python-docx"
                )

        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")

    async def _save_document_metadata(
        self,
        document_id: str,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        metadata: Dict[str, Any]
    ) -> None:
        """Save document metadata to database."""
        if not self.db_pool:
            return

        import json

        # Extract document_scope from metadata
        document_scope = metadata.pop("document_scope", "personal")

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO turfmapp_agent.documents
                (id, user_id, filename, file_type, file_size, status, document_scope, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                """,
                document_id,
                user_id,
                filename,
                file_type,
                file_size,
                'processing',
                document_scope,
                json.dumps(metadata)
            )

    async def _save_document_chunks(
        self,
        document_id: str,
        user_id: str,
        nodes: List[TextNode]
    ) -> None:
        """Save document chunks to database."""
        if not self.db_pool:
            return

        import json
        import logging
        logger = logging.getLogger(__name__)

        async with self.db_pool.acquire() as conn:
            for idx, node in enumerate(nodes):
                logger.info(f"💾 Saving chunk {idx}: node_id={node.node_id} (type={type(node.node_id).__name__}), document_id={document_id}")
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.document_nodes
                    (id, user_id, document_id, chunk_index, content, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    """,
                    node.node_id,
                    user_id,
                    document_id,
                    idx,
                    node.text,
                    json.dumps(node.metadata or {})
                )
                # Verify what was actually inserted
                result = await conn.fetchrow(
                    "SELECT id FROM turfmapp_agent.document_nodes WHERE document_id = $1 AND chunk_index = $2",
                    document_id, idx
                )
                logger.info(f"💾 Verified chunk {idx}: saved_id={result['id']}, expected_id={node.node_id}, match={str(result['id']) == node.node_id}")

    async def _update_document_status(
        self,
        document_id: str,
        status: str,
        chunk_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Update document processing status."""
        if not self.db_pool:
            return

        import json

        async with self.db_pool.acquire() as conn:
            if error:
                await conn.execute(
                    """
                    UPDATE turfmapp_agent.documents
                    SET status = $1, metadata = metadata || $2, updated_at = NOW()
                    WHERE id = $3
                    """,
                    status,
                    json.dumps({"error": error}),
                    document_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE turfmapp_agent.documents
                    SET status = $1, chunk_count = $2, updated_at = NOW()
                    WHERE id = $3
                    """,
                    status,
                    chunk_count,
                    document_id
                )

    async def get_user_documents(
        self,
        user_id: str,
        limit: int = 50,
        include_organization: bool = True
    ) -> List[Dict[str, Any]]:
        """Get list of user's documents (personal + organization if enabled)."""
        if not self.db_pool:
            return []

        async with self.db_pool.acquire() as conn:
            if include_organization:
                # Get both personal and organization documents
                rows = await conn.fetch(
                    """
                    SELECT id, filename, file_type, file_size, chunk_count,
                           status, document_scope, created_at, updated_at
                    FROM turfmapp_agent.documents
                    WHERE user_id = $1 OR document_scope = 'organization'
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit
                )
            else:
                # Get only personal documents
                rows = await conn.fetch(
                    """
                    SELECT id, filename, file_type, file_size, chunk_count,
                           status, document_scope, created_at, updated_at
                    FROM turfmapp_agent.documents
                    WHERE user_id = $1 AND document_scope = 'personal'
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit
                )

            return [dict(row) for row in rows]

    async def delete_document(
        self,
        document_id: str,
        user_id: str
    ) -> bool:
        """Delete a document and all its chunks."""
        if not self.db_pool:
            return False

        try:
            async with self.db_pool.acquire() as conn:
                # Delete document (chunks deleted automatically via CASCADE)
                result = await conn.execute(
                    """
                    DELETE FROM turfmapp_agent.documents
                    WHERE id = $1 AND user_id = $2
                    """,
                    document_id,
                    user_id
                )

                logger.info(f"Deleted document: {document_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
