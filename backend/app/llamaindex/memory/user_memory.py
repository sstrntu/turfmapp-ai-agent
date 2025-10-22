"""
User Memory Manager - Account-Level Memory

Manages persistent user facts that carry across all conversations:
- Name, preferences, background
- Extracts facts from conversations using LLM
- Injects user context into new conversations
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class UserMemory:
    """
    Manages account-level memory for a user.

    This persists facts about the user across ALL conversations,
    unlike conversation memory which is per-conversation.
    """

    def __init__(self, user_id: str, db_pool: Optional[Any] = None):
        """
        Initialize user memory.

        Args:
            user_id: User ID
            db_pool: Database connection pool
        """
        self.user_id = user_id
        self.db_pool = db_pool
        self.facts: Dict[str, str] = {}

    async def load_from_database(self) -> None:
        """Load user memory from database."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT memory_key, memory_value, confidence
                    FROM turfmapp_agent.user_memory
                    WHERE user_id = $1
                    ORDER BY updated_at DESC
                    """,
                    self.user_id
                )

                self.facts = {
                    row['memory_key']: row['memory_value']
                    for row in rows
                }

                logger.info(
                    f"Loaded user memory: user={self.user_id}, "
                    f"facts={len(self.facts)}"
                )

        except Exception as e:
            logger.error(f"Failed to load user memory: {e}")

    async def save_fact(
        self,
        key: str,
        value: str,
        confidence: float = 1.0,
        source_conversation_id: Optional[str] = None
    ) -> None:
        """
        Save a fact about the user.

        Args:
            key: Memory key (e.g., 'name', 'profession')
            value: Memory value (e.g., 'Sira', 'Software Engineer')
            confidence: Confidence score (0-1)
            source_conversation_id: Where this fact came from
        """
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO turfmapp_agent.user_memory
                    (user_id, memory_key, memory_value, confidence, source_conversation_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                    ON CONFLICT (user_id, memory_key)
                    DO UPDATE SET
                        memory_value = EXCLUDED.memory_value,
                        confidence = EXCLUDED.confidence,
                        source_conversation_id = EXCLUDED.source_conversation_id,
                        updated_at = NOW()
                    """,
                    self.user_id,
                    key,
                    value,
                    confidence,
                    source_conversation_id
                )

            # Update in-memory cache
            self.facts[key] = value

            logger.info(f"Saved user fact: user={self.user_id}, {key}={value}")

        except Exception as e:
            logger.error(f"Failed to save user fact: {e}")

    async def extract_facts_from_conversation(
        self,
        messages: List[Dict[str, str]],
        conversation_id: str,
        llm: Any
    ) -> Dict[str, str]:
        """
        Extract user facts from conversation using LLM.

        Args:
            messages: Recent conversation messages
            conversation_id: Conversation ID
            llm: LLM instance for extraction

        Returns:
            Dictionary of extracted facts
        """
        if not messages:
            return {}

        # Format recent messages
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in messages[-10:]  # Last 10 messages
        )

        prompt = f"""Extract factual information about the USER from this conversation.
Focus on:
- Name
- Profession/occupation
- Location
- Preferences
- Interests
- Background information

Return ONLY a JSON object with keys and values. If no facts are found, return {{}}.

Conversation:
{conversation_text}

Extracted facts (JSON only, no explanation):"""

        try:
            response = await llm.acomplete(prompt)

            # Parse JSON response
            facts_text = response.text.strip()

            # Try to extract JSON from response
            if "```json" in facts_text:
                facts_text = facts_text.split("```json")[1].split("```")[0].strip()
            elif "```" in facts_text:
                facts_text = facts_text.split("```")[1].split("```")[0].strip()

            facts = json.loads(facts_text)

            # Save each fact
            for key, value in facts.items():
                if value and isinstance(value, str):
                    await self.save_fact(
                        key=key.lower().replace(" ", "_"),
                        value=value,
                        confidence=0.9,  # High confidence from direct extraction
                        source_conversation_id=conversation_id
                    )

            logger.info(
                f"Extracted {len(facts)} user facts: user={self.user_id}, "
                f"conversation={conversation_id}"
            )

            return facts

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse facts JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to extract user facts: {e}")
            return {}

    def get_context_string(self) -> str:
        """
        Get user memory as a formatted string for injection into prompts.

        Returns:
            Formatted context string
        """
        if not self.facts:
            return ""

        lines = ["**User Information (from previous conversations):**"]
        for key, value in self.facts.items():
            formatted_key = key.replace("_", " ").title()
            lines.append(f"- {formatted_key}: {value}")

        return "\n".join(lines)

    def get_facts(self) -> Dict[str, str]:
        """Get all user facts."""
        return self.facts.copy()

    async def clear(self) -> None:
        """Clear all user memory."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM turfmapp_agent.user_memory WHERE user_id = $1",
                    self.user_id
                )

            self.facts = {}
            logger.info(f"Cleared user memory: user={self.user_id}")

        except Exception as e:
            logger.error(f"Failed to clear user memory: {e}")
