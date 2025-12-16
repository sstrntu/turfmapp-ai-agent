"""
Conversation Memory Manager using LlamaIndex

Provides advanced memory management for conversations including:
- Chat buffer memory (store recent messages)
- Auto-summarization (when buffer exceeds limit)
- Entity extraction (track important entities)
- Memory persistence to PostgreSQL

This replaces the simple message storage in ConversationManager with
intelligent memory management powered by LlamaIndex.
"""

from __future__ import annotations

import asyncio
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

from ..services.llm_factory import llm_factory, TaskType

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memory that can be stored."""
    BUFFER = "buffer"  # Raw message buffer
    SUMMARY = "summary"  # Conversation summary
    ENTITIES = "entities"  # Extracted entities


class ConversationMemory:
    """
    Manages conversation memory with LlamaIndex.

    Features:
    - Stores recent messages in buffer
    - Auto-summarizes when buffer gets too large
    - Extracts and tracks entities across conversation
    - Persists memory to database
    """

    def __init__(
        self,
        user_id: str,
        conversation_id: str,
        max_messages: int = 20,
        summarize_threshold: int = 30,
        db_pool: Optional[Any] = None,
    ):
        """
        Initialize conversation memory.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            max_messages: Maximum messages to keep in buffer
            summarize_threshold: Number of messages before auto-summarization
            db_pool: Database connection pool (optional)
        """
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.max_messages = max_messages
        self.summarize_threshold = summarize_threshold
        self.db_pool = db_pool

        # Initialize LlamaIndex chat memory
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=8000)

        # Track conversation state
        self.message_count = 0
        self.summary: Optional[str] = None
        self.entities: Dict[str, Any] = {}

    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to the conversation memory.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata
        """
        # Convert role string to MessageRole enum
        if role == "user":
            message_role = MessageRole.USER
        elif role == "assistant":
            message_role = MessageRole.ASSISTANT
        elif role == "system":
            message_role = MessageRole.SYSTEM
        else:
            message_role = MessageRole.USER  # Default

        # Create ChatMessage
        message = ChatMessage(
            role=message_role,
            content=content,
            additional_kwargs=metadata or {},
        )

        # Add to memory buffer
        self.memory.put(message)
        self.message_count += 1

        logger.debug(
            f"Added message to memory: conversation={self.conversation_id}, "
            f"role={role}, count={self.message_count}"
        )

        # Check if we need to summarize
        if self.message_count >= self.summarize_threshold:
            await self._auto_summarize()

        # Persist to database if available
        if self.db_pool:
            await self._persist_message(role, content, metadata)

    async def get_messages(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages from memory.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        messages = self.memory.get()

        # Convert to dict format
        result = []
        for msg in messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content,
                "metadata": msg.additional_kwargs,
            })

        # Apply limit if specified
        if limit and len(result) > limit:
            result = result[-limit:]

        return result

    async def get_context(
        self,
        include_summary: bool = True,
        include_entities: bool = True
    ) -> str:
        """
        Get conversation context as a formatted string.

        Args:
            include_summary: Whether to include conversation summary
            include_entities: Whether to include extracted entities

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add summary if available
        if include_summary and self.summary:
            context_parts.append(f"Conversation Summary:\n{self.summary}")

        # Add entities if available
        if include_entities and self.entities:
            entities_str = json.dumps(self.entities, indent=2)
            context_parts.append(f"Key Entities:\n{entities_str}")

        # Add recent messages
        messages = await self.get_messages(limit=self.max_messages)
        if messages:
            messages_str = "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in messages
            )
            context_parts.append(f"Recent Messages:\n{messages_str}")

        return "\n\n".join(context_parts)

    async def summarize_conversation(self) -> str:
        """
        Create a summary of the conversation using LLM.

        Returns:
            Conversation summary
        """
        messages = await self.get_messages()

        if not messages:
            return "No conversation history."

        # Format messages for summarization
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in messages
        )

        # Use LLM to summarize
        llm = llm_factory.create_llm(
            model_id=llm_factory.recommend_model_for_task(TaskType.SUMMARIZATION),
            temperature=0.3,  # Lower temperature for consistency
        )

        prompt = f"""Summarize the following conversation concisely, focusing on:
1. Main topics discussed
2. Key decisions or conclusions
3. Important context to remember

Conversation:
{conversation_text}

Summary:"""

        response = await llm.acomplete(prompt)
        summary = response.text.strip()

        logger.info(
            f"Generated conversation summary: conversation={self.conversation_id}, "
            f"length={len(summary)}"
        )

        return summary

    async def extract_entities(self) -> Dict[str, Any]:
        """
        Extract important entities from the conversation.

        Returns:
            Dictionary of extracted entities
        """
        messages = await self.get_messages()

        if not messages:
            return {}

        # Format messages for entity extraction
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in messages[-10:]  # Last 10 messages
        )

        # Use LLM to extract entities
        llm = llm_factory.create_llm(
            model_id=llm_factory.recommend_model_for_task(TaskType.ANALYSIS),
            temperature=0.2,  # Lower temperature for accuracy
        )

        prompt = f"""Extract important entities from this conversation. Focus on:
- People (names, roles)
- Places (locations, addresses)
- Organizations (companies, institutions)
- Dates and times
- Key topics or subjects

Return the entities as a JSON object with categories.

Conversation:
{conversation_text}

Entities (JSON):"""

        response = await llm.acomplete(prompt)

        try:
            # Parse JSON response
            entities = json.loads(response.text.strip())
            logger.info(
                f"Extracted entities: conversation={self.conversation_id}, "
                f"count={len(entities)}"
            )
            return entities
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse entities JSON: {e}")
            return {}

    async def _auto_summarize(self) -> None:
        """Automatically summarize conversation when threshold is reached."""
        logger.info(
            f"Auto-summarizing conversation: conversation={self.conversation_id}, "
            f"message_count={self.message_count}"
        )

        try:
            # Generate summary
            self.summary = await self.summarize_conversation()

            # Extract entities
            self.entities = await self.extract_entities()

            # Persist summary to database
            if self.db_pool:
                await self._persist_memory_state(
                    MemoryType.SUMMARY,
                    {"summary": self.summary, "message_count": self.message_count}
                )
                await self._persist_memory_state(
                    MemoryType.ENTITIES,
                    self.entities
                )

            # Clear old messages from buffer (keep recent ones)
            messages = await self.get_messages()
            if len(messages) > self.max_messages:
                # Keep only recent messages
                recent_messages = messages[-self.max_messages:]
                self.memory = ChatMemoryBuffer.from_defaults(token_limit=8000)
                for msg in recent_messages:
                    role = MessageRole(msg["role"])
                    message = ChatMessage(
                        role=role,
                        content=msg["content"],
                        additional_kwargs=msg.get("metadata", {}),
                    )
                    self.memory.put(message)

            logger.info(f"Auto-summarization complete: conversation={self.conversation_id}")

        except Exception as e:
            logger.error(f"Auto-summarization failed: {e}", exc_info=True)

    async def _persist_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Persist message to database."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.messages
                    (conversation_id, role, content, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    self.conversation_id,
                    role,
                    content,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.error(f"Failed to persist message: {e}")

    async def _persist_memory_state(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any]
    ) -> None:
        """Persist memory state to database."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.memory_states
                    (user_id, conversation_id, memory_type, content, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $5)
                    ON CONFLICT (user_id, conversation_id, memory_type)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = EXCLUDED.updated_at
                    """,
                    self.user_id,
                    self.conversation_id,
                    memory_type.value,
                    json.dumps(content),
                    datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.error(f"Failed to persist memory state: {e}")

    async def load_from_database(self) -> None:
        """Load conversation memory from database."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                # Load messages
                messages = await conn.fetch(
                    """
                    SELECT role, content, metadata, created_at
                    FROM turfmapp_agent.messages
                    WHERE conversation_id = $1
                    ORDER BY created_at ASC
                    LIMIT $2
                    """,
                    self.conversation_id,
                    self.max_messages,
                )

                for msg in messages:
                    role = MessageRole(msg["role"])
                    metadata = json.loads(msg["metadata"]) if msg["metadata"] else {}

                    message = ChatMessage(
                        role=role,
                        content=msg["content"],
                        additional_kwargs=metadata,
                    )
                    self.memory.put(message)
                    self.message_count += 1

                # Load memory states
                memory_states = await conn.fetch(
                    """
                    SELECT memory_type, content
                    FROM turfmapp_agent.memory_states
                    WHERE user_id = $1 AND conversation_id = $2
                    """,
                    self.user_id,
                    self.conversation_id,
                )

                for state in memory_states:
                    memory_type = state["memory_type"]
                    content = json.loads(state["content"])

                    if memory_type == MemoryType.SUMMARY.value:
                        self.summary = content.get("summary")
                    elif memory_type == MemoryType.ENTITIES.value:
                        self.entities = content

                logger.info(
                    f"Loaded conversation memory: conversation={self.conversation_id}, "
                    f"messages={self.message_count}, has_summary={bool(self.summary)}"
                )

        except Exception as e:
            logger.error(f"Failed to load memory from database: {e}")

    def clear(self) -> None:
        """Clear all memory."""
        self.memory = ChatMemoryBuffer.from_defaults(token_limit=8000)
        self.message_count = 0
        self.summary = None
        self.entities = {}
        logger.info(f"Cleared conversation memory: conversation={self.conversation_id}")


class MemoryManager:
    """
    Factory for creating and managing conversation memory instances.
    """

    def __init__(self, db_pool: Optional[Any] = None):
        """
        Initialize memory manager.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._memories: Dict[str, ConversationMemory] = {}

    def get_memory(
        self,
        user_id: str,
        conversation_id: str,
        max_messages: int = 20,
        summarize_threshold: int = 30,
    ) -> ConversationMemory:
        """
        Get or create conversation memory.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            max_messages: Maximum messages in buffer
            summarize_threshold: When to auto-summarize

        Returns:
            ConversationMemory instance
        """
        key = f"{user_id}:{conversation_id}"

        if key not in self._memories:
            self._memories[key] = ConversationMemory(
                user_id=user_id,
                conversation_id=conversation_id,
                max_messages=max_messages,
                summarize_threshold=summarize_threshold,
                db_pool=self.db_pool,
            )

        return self._memories[key]

    def remove_memory(self, user_id: str, conversation_id: str) -> None:
        """
        Remove conversation memory from cache.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
        """
        key = f"{user_id}:{conversation_id}"
        if key in self._memories:
            del self._memories[key]
            logger.info(f"Removed memory from cache: {key}")
