"""
RAG Query Service - Retrieval-Augmented Generation

Combines document retrieval with LLM generation to answer questions
using your uploaded documents as context.
"""

import logging
from typing import List, Dict, Any, Optional

from llama_index.core.llms import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class RAGQueryService:
    """
    RAG query service for document-based question answering.

    Features:
    - Semantic search over documents
    - Context-aware answer generation
    - Source citation
    - Multi-document retrieval
    """

    def __init__(
        self,
        vector_store: Any,
        llm: Any,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize RAG query service.

        Args:
            vector_store: PgVectorStore instance
            llm: LLM instance for generation
            top_k: Number of chunks to retrieve
            similarity_threshold: Minimum similarity score
        """
        self.vector_store = vector_store
        self.llm = llm
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def query(
        self,
        question: str,
        user_id: Optional[str] = None,
        include_sources: bool = True,
        include_organization_docs: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG.

        Args:
            question: User's question
            user_id: Optional user ID to filter documents
            include_sources: Whether to include source citations
            include_organization_docs: Include organization-wide documents

        Returns:
            Answer with optional source citations
        """
        try:
            # Step 1: Retrieve relevant chunks
            chunks = await self.vector_store.similarity_search(
                query=question,
                user_id=user_id,
                limit=self.top_k,
                similarity_threshold=self.similarity_threshold,
                include_organization_docs=include_organization_docs
            )

            if not chunks:
                return {
                    "answer": "I couldn't find any relevant information in your documents to answer this question.",
                    "sources": [],
                    "chunks_found": 0
                }

            # Step 2: Build context from retrieved chunks
            context = self._build_context(chunks)

            # Step 3: Generate answer using LLM
            answer = await self._generate_answer(
                question=question,
                context=context
            )

            # Step 4: Format sources
            sources = self._format_sources(chunks) if include_sources else []

            logger.info(
                f"RAG query completed: question_len={len(question)}, "
                f"chunks={len(chunks)}, user={user_id or 'all'}"
            )

            return {
                "answer": answer,
                "sources": sources,
                "chunks_found": len(chunks)
            }

        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            raise

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []

        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {idx}: {chunk['filename']}, "
                f"Section {chunk['chunk_index'] + 1}]\n"
                f"{chunk['content']}\n"
            )

        return "\n".join(context_parts)

    async def _generate_answer(
        self,
        question: str,
        context: str
    ) -> str:
        """Generate answer using LLM with retrieved context."""

        system_prompt = """You are a helpful assistant that answers questions based on the provided context.

IMPORTANT RULES:
1. ONLY use information from the provided context to answer questions
2. If the context doesn't contain the answer, say "I don't have enough information to answer that question"
3. Cite the source number (e.g., "According to Source 1...") when referencing information
4. Be concise but thorough
5. If the question is unclear, ask for clarification

DO NOT make up information or use knowledge outside the provided context."""

        user_prompt = f"""Context from documents:
{context}

Question: {question}

Please answer the question using ONLY the information from the context above."""

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=MessageRole.USER, content=user_prompt)
        ]

        response = await self.llm.achat(messages)
        return response.message.content

    def _format_sources(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format source citations for the response."""
        sources = []
        seen_docs = set()

        for idx, chunk in enumerate(chunks, 1):
            doc_id = chunk['document_id']

            # Group chunks by document
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                sources.append({
                    "source_number": idx,
                    "document_id": doc_id,
                    "filename": chunk['filename'],
                    "chunk_index": chunk['chunk_index'],
                    "similarity": chunk['similarity'],
                    "preview": chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content']
                })

        return sources

    async def query_with_chat_history(
        self,
        question: str,
        chat_history: List[ChatMessage],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG with chat history context.

        Useful for follow-up questions that reference previous messages.

        Args:
            question: Current question
            chat_history: Previous chat messages
            user_id: Optional user ID

        Returns:
            Answer with sources
        """
        # For now, just use the current question
        # In the future, we could use chat history to reformulate the query
        return await self.query(question, user_id)
