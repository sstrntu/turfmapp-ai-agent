"""
RAG Tools - Document Search and Query Tools

Wraps RAG functionality as LlamaIndex tools for agent use.
Allows the agent to search and query user documents intelligently.
"""

import logging
from typing import List, Optional

from llama_index.core.tools import FunctionTool

logger = logging.getLogger(__name__)


def create_rag_tools(
    user_id: str,
    db_pool,
    vector_store,
    llm,
    top_k: int = 3,
    similarity_threshold: float = 0.3,
) -> List[FunctionTool]:
    """
    Create RAG tools for document search and query.

    Args:
        user_id: User ID for document filtering
        db_pool: Database connection pool
        vector_store: PgVectorStore instance
        llm: LLM instance for answer generation
        top_k: Number of chunks to retrieve
        similarity_threshold: Minimum similarity score

    Returns:
        List of RAG tools
    """
    from ...llamaindex.rag import RAGQueryService

    # Create RAG service
    rag_service = RAGQueryService(
        vector_store=vector_store,
        llm=llm,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )

    async def search_documents(query: str) -> str:
        """
        Search through the user's uploaded documents and files to find relevant information.

        Use this tool when:
        - The user asks about content in their uploaded documents (PDFs, Word docs, etc.)
        - You need detailed information that might be in their files (e.g., resume, reports, notes)
        - The answer requires referencing specific documents they've uploaded
        - User Information doesn't contain enough detail and documents might have more

        Examples:
        - "What does my resume say about my Python experience?"
        - "Find information about project X in my documents"
        - "What are the key points from my uploaded report?"
        - "Do my documents mention anything about Y?"

        Don't use this tool if:
        - The information is already in User Information above (unless more detail is needed)
        - The question is general knowledge that doesn't require their documents
        - You can answer the question from the conversation context alone

        Args:
            query: Search query to find relevant information in uploaded documents

        Returns:
            Relevant information found in documents with sources, or message if nothing found
        """
        try:
            result = await rag_service.query(
                question=query,
                user_id=user_id,
                include_sources=True,
                include_organization_docs=True,
            )

            if result['chunks_found'] == 0:
                return "No relevant information found in the uploaded documents."

            # Format response with sources
            response = f"{result['answer']}\n\n"

            if result.get('sources'):
                sources_list = [f"- {s['filename']}" for s in result['sources']]
                response += f"Sources:\n" + "\n".join(sources_list)

            return response

        except Exception as e:
            logger.error(f"RAG search failed: {e}", exc_info=True)
            return f"Error searching documents: {str(e)}"

    async def list_available_documents() -> str:
        """
        List all documents and files the user has uploaded to their library.

        Use this tool when:
        - User asks what documents they have uploaded
        - User wants to see their document library or file list
        - You need to know what documents are available before searching
        - User asks about specific file types or document names

        Examples:
        - "What documents do I have?"
        - "List my uploaded files"
        - "Show me my PDFs"
        - "Do I have any documents about X?" (first check the list)

        Returns:
            List of available documents with names, types, and upload dates
        """
        try:
            from ...llamaindex.rag import DocumentIngestionService

            ingestion_service = DocumentIngestionService(db_pool=db_pool)
            documents = await ingestion_service.get_user_documents(
                user_id=user_id,
                limit=50,
                include_organization=True,
            )

            if not documents:
                return "No documents have been uploaded yet."

            # Format document list
            doc_list = []
            for doc in documents:
                status = doc.get('status', 'unknown')
                chunks = doc.get('chunk_count', 0)
                filename = doc.get('filename', 'unknown')
                scope = doc.get('document_scope', 'personal')

                doc_list.append(
                    f"- {filename} ({scope}, {chunks} chunks, status: {status})"
                )

            return f"Available documents ({len(documents)}):\n" + "\n".join(doc_list)

        except Exception as e:
            logger.error(f"Failed to list documents: {e}", exc_info=True)
            return f"Error listing documents: {str(e)}"

    # Create tools
    tools = [
        FunctionTool.from_defaults(
            async_fn=search_documents,
            name="search_documents",
            description=(
                "Search through the user's uploaded documents to find relevant information. "
                "Use this when the user asks about content from their files or documents."
            ),
        ),
        FunctionTool.from_defaults(
            async_fn=list_available_documents,
            name="list_documents",
            description=(
                "List all documents the user has uploaded. "
                "Use this when the user wants to know what documents are available."
            ),
        ),
    ]

    return tools
