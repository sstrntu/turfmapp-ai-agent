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
        llm: Any,
        auto_save: bool = True,
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

        # Format recent messages (only use what was provided, typically 2-3 messages)
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        )

        prompt = f"""Extract NEWLY SHARED information about the USER from this conversation.

You should extract TWO types of information:

1. PERSONAL FACTS (name, profession, location, etc.)
2. EXPLICIT INSTRUCTIONS/PREFERENCES (when user says "remember:", "keep in mind:", etc.)

CRITICAL RULES:
- ONLY extract information from USER messages (not assistant responses)
- Focus on NEW information just shared
- For explicit instructions, preserve the full context
- Extract a MAXIMUM of 3 most important items

PERSONAL FACTS (use these key formats):
- "name": user's name
- "profession": job title or role
- "location": city or country
- "company": company name
- "interests": hobbies or interests

EXPLICIT INSTRUCTIONS/PREFERENCES (use descriptive keys):
- "data_analysis_approach": for data analysis instructions
- "communication_style": for how they want you to communicate
- "work_preferences": for workflow or process preferences
- "[topic]_instructions": for any specific domain instructions

DETECTION PATTERNS for explicit instructions:
- "Remember: [instruction]"
- "Here are the points I want you to remember: [instruction]"
- "Keep in mind that [instruction]"
- "When [doing X], [instruction]"
- "Please remember [instruction]"

Return ONLY a JSON object. If NO NEW information is found, return {{}}.

Examples:
Input: "My name is Alex"
Output: {{"name": "Alex"}}

Input: "Remember: When analyzing data, you need to look at previous trends and take out outliers"
Output: {{"data_analysis_approach": "When analyzing data, look at previous trends and take out outliers"}}

Input: "I'm a software engineer at Google, and when reviewing code, always check for security issues first"
Output: {{"profession": "Software Engineer", "company": "Google", "code_review_approach": "Always check for security issues first"}}

Conversation:
{conversation_text}

Extracted information (JSON only, max 3 items, no explanation):"""

        try:
            response = await llm.acomplete(prompt)

            # Parse JSON response
            facts_text = response.text.strip()
            logger.info(f"LLM response for fact extraction: {facts_text}")

            # Try to extract JSON from response
            if "```json" in facts_text:
                facts_text = facts_text.split("```json")[1].split("```")[0].strip()
            elif "```" in facts_text:
                facts_text = facts_text.split("```")[1].split("```")[0].strip()

            facts = json.loads(facts_text)

            if auto_save:
                # Save each fact immediately (skip if already exists with same value)
                saved_count = 0
                for key, value in facts.items():
                    if not value or not isinstance(value, str):
                        continue

                    normalized_key = key.lower().replace(" ", "_")

                    # Check if fact already exists with same value
                    if normalized_key in self.facts and self.facts[normalized_key] == value:
                        logger.info(f"⏭️  Skipping duplicate fact: {normalized_key}={value}")
                        continue

                    # Save new or updated fact
                    await self.save_fact(
                        key=normalized_key,
                        value=value,
                        confidence=0.9,  # High confidence from direct extraction
                        source_conversation_id=conversation_id
                    )
                    saved_count += 1
                    logger.info(f"💾 Saved fact: {normalized_key}={value}")

                if saved_count > 0:
                    logger.info(
                        f"✅ Saved {saved_count} new user facts: user={self.user_id}, "
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

        Separates personal facts from instructions/preferences for clarity.

        Returns:
            Formatted context string
        """
        if not self.facts:
            return ""

        # Categorize facts
        personal_facts = {}
        instructions = {}

        # Keys that indicate instructions/preferences (not personal facts)
        instruction_keywords = ['approach', 'instruction', 'preference', 'style', 'guideline', 'rule', 'method']

        for key, value in self.facts.items():
            # Check if this is an instruction/preference
            is_instruction = any(keyword in key.lower() for keyword in instruction_keywords)

            if is_instruction:
                instructions[key] = value
            else:
                personal_facts[key] = value

        lines = []

        # Add personal facts section
        if personal_facts:
            lines.append("**User Profile:**")
            for key, value in personal_facts.items():
                formatted_key = key.replace("_", " ").title()
                lines.append(f"- {formatted_key}: {value}")

        # Add instructions/preferences section
        if instructions:
            if personal_facts:  # Add spacing if we had personal facts
                lines.append("")
            lines.append("**User's Instructions & Preferences:**")
            for key, value in instructions.items():
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
