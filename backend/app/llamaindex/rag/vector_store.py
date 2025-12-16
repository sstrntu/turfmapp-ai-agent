"""
PgVector Store - Vector storage using PostgreSQL + pgvector

Handles embedding generation and similarity search.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio

from llama_index.core.schema import TextNode
from llama_index.embeddings.openai import OpenAIEmbedding

logger = logging.getLogger(__name__)


class PgVectorStore:
    """
    Vector store using PostgreSQL + pgvector extension.

    Features:
    - Automatic embedding generation
    - Cosine similarity search
    - Batch operations for efficiency
    """

    def __init__(
        self,
        db_pool: Any,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536
    ):
        """
        Initialize vector store.

        Args:
            db_pool: Database connection pool
            embedding_model: OpenAI embedding model
            embedding_dim: Embedding dimensions
        """
        self.db_pool = db_pool
        self.embedding_dim = embedding_dim

        # Initialize embedding model
        self.embed_model = OpenAIEmbedding(
            model=embedding_model,
            embed_batch_size=100
        )

        logger.info(f"Initialized PgVectorStore with {embedding_model}")

    async def add_nodes(
        self,
        nodes: List[TextNode],
        show_progress: bool = True
    ) -> int:
        """
        Add nodes with embeddings to the vector store.

        Args:
            nodes: List of text nodes to add
            show_progress: Whether to log progress

        Returns:
            Number of nodes added
        """
        if not nodes:
            return 0

        try:
            # Generate embeddings for all nodes
            texts = [node.text for node in nodes]
            logger.info(f"Generating embeddings for {len(texts)} texts...")
            embeddings = await self.embed_model.aget_text_embedding_batch(texts)
            logger.info(f"Generated {len(embeddings)} embeddings, first embedding dim: {len(embeddings[0]) if embeddings else 0}")

            # Save to database
            async with self.db_pool.acquire() as conn:
                updated_count = 0
                for idx, (node, embedding) in enumerate(zip(nodes, embeddings)):
                    # Convert embedding list to PostgreSQL vector format
                    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                    logger.info(f"Updating node {idx+1}/{len(nodes)}: id={node.node_id} (type={type(node.node_id).__name__}), embedding_dim={len(embedding)}")
                    result = await conn.execute(
                        """
                        UPDATE turfmapp_agent.document_nodes
                        SET embedding = CAST($1 AS vector), updated_at = NOW()
                        WHERE id = $2
                        """,
                        embedding_str,
                        node.node_id
                    )
                    logger.info(f"Update result for node {node.node_id}: {result}")
                    if result == "UPDATE 0":
                        logger.error(f"❌ UPDATE matched 0 rows for node_id={node.node_id}!")
                    updated_count += 1

            logger.info(f"Added {len(nodes)} nodes to vector store (updated {updated_count} rows)")
            return len(nodes)

        except Exception as e:
            logger.error(f"Failed to add nodes: {e}", exc_info=True)
            raise

    async def similarity_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        include_organization_docs: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using cosine similarity.

        Args:
            query: Search query
            user_id: Optional user ID to filter results
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
            include_organization_docs: Include organization-wide documents

        Returns:
            List of matching chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = await self.embed_model.aget_query_embedding(query)

            # Convert embedding to PostgreSQL vector format
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

            # Build SQL query
            sql = """
                SELECT
                    dn.id,
                    dn.document_id,
                    dn.chunk_index,
                    dn.content,
                    dn.metadata,
                    d.filename,
                    d.document_scope,
                    1 - (dn.embedding <=> CAST($1 AS vector)) AS similarity
                FROM turfmapp_agent.document_nodes dn
                JOIN turfmapp_agent.documents d ON dn.document_id = d.id
                WHERE dn.embedding IS NOT NULL
            """

            params = [embedding_str]

            # Add user/organization filter
            if user_id and include_organization_docs:
                # Include both user's documents and organization documents
                sql += " AND (dn.user_id = $2 OR d.document_scope = 'organization')"
                params.append(user_id)
            elif user_id:
                # Only user's personal documents
                sql += " AND dn.user_id = $2"
                params.append(user_id)

            # Order by similarity and get more results than needed (will filter in Python)
            sql += """
                ORDER BY dn.embedding <=> CAST($1 AS vector)
                LIMIT 50
            """

            # Execute search
            logger.info(f"🔍 Executing SQL with threshold={similarity_threshold}, limit={limit}, user_id={user_id}")
            logger.info(f"🔍 SQL: {sql[:200]}...")
            logger.info(f"🔍 Params count: {len(params)}")

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
                logger.info(f"🔍 Main query returned {len(rows)} rows")

                # Also get top results without threshold to see actual scores
                debug_sql = """
                    SELECT dn.id, dn.chunk_index, d.filename, d.document_scope,
                           1 - (dn.embedding <=> CAST($1 AS vector)) AS similarity
                    FROM turfmapp_agent.document_nodes dn
                    JOIN turfmapp_agent.documents d ON dn.document_id = d.id
                    WHERE dn.embedding IS NOT NULL
                """
                if user_id:
                    debug_sql += " AND (dn.user_id = $2 OR d.document_scope = 'organization')"
                    debug_rows = await conn.fetch(debug_sql + " ORDER BY similarity DESC LIMIT 5", embedding_str, user_id)
                else:
                    debug_rows = await conn.fetch(debug_sql + " ORDER BY similarity DESC LIMIT 5", embedding_str)

                logger.info(f"🔍 Top 5 similarity scores (no threshold): {[(r['chunk_index'], float(r['similarity'])) for r in debug_rows]}")

            # Filter by threshold and limit in Python
            results = []
            for row in rows:
                similarity_score = float(row['similarity'])
                if similarity_score >= similarity_threshold:
                    results.append({
                        "id": str(row['id']),
                        "document_id": str(row['document_id']),
                        "filename": row['filename'],
                        "chunk_index": row['chunk_index'],
                        "content": row['content'],
                        "metadata": row['metadata'],
                        "document_scope": row['document_scope'],
                        "similarity": similarity_score
                    })

                    if len(results) >= limit:
                        break

            logger.info(
                f"Similarity search: query_len={len(query)}, "
                f"results={len(results)}/{len(rows)} (after threshold={similarity_threshold}), user={user_id or 'all'}"
            )

            return results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}", exc_info=True)
            raise

    async def get_embedding_stats(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about embeddings in the store.

        Args:
            user_id: Optional user ID to filter stats (includes organization docs)

        Returns:
            Statistics dictionary
        """
        try:
            sql = """
                SELECT
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT dn.document_id) as total_documents,
                    COUNT(dn.embedding) as chunks_with_embeddings,
                    AVG(LENGTH(dn.content)) as avg_chunk_length
                FROM turfmapp_agent.document_nodes dn
                JOIN turfmapp_agent.documents d ON dn.document_id = d.id
            """

            params = []
            if user_id:
                # Include both user's documents and organization documents
                sql += " WHERE (dn.user_id = $1 OR d.document_scope = 'organization')"
                params.append(user_id)

            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(sql, *params)

            return {
                "total_chunks": row['total_chunks'],
                "total_documents": row['total_documents'],
                "chunks_with_embeddings": row['chunks_with_embeddings'],
                "avg_chunk_length": float(row['avg_chunk_length'] or 0),
                "embedding_coverage": (
                    row['chunks_with_embeddings'] / row['total_chunks']
                    if row['total_chunks'] > 0 else 0
                )
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    async def delete_document_embeddings(
        self,
        document_id: str
    ) -> bool:
        """
        Delete all embeddings for a document.

        Args:
            document_id: Document ID

        Returns:
            Success status
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE turfmapp_agent.document_nodes
                    SET embedding = NULL, updated_at = NOW()
                    WHERE document_id = $1
                    """,
                    document_id
                )

            logger.info(f"Deleted embeddings for document: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            return False
