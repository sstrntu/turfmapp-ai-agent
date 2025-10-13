"""
Conversation Manager Module

Handles all conversation persistence operations including:
- Conversation CRUD operations
- Message storage and retrieval
- Database fallback patterns for resilience
- User preferences management

Extracted from chat_service.py to improve maintainability and separation of concerns.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from ..database import ConversationService
from ..api.v1.preferences import user_preferences

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation persistence with database fallback."""
    
    def __init__(self):
        """Initialize conversation manager with fallback storage."""
        # Fallback storage for when database fails
        self.fallback_conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.fallback_conversation_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def use_database_fallback(self, func_name: str, *args, **kwargs):
        """
        Try database operation, fall back to in-memory storage if it fails.
        
        Args:
            func_name: Name of ConversationService method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method
            
        Returns:
            Result from database or None if failed
        """
        try:
            method = getattr(ConversationService, func_name)
            if asyncio.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Database {func_name} failed: {e}, using fallback")
            return None
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history with fallback support.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID for ownership verification
            
        Returns:
            List of conversation messages
        """
        # Try database first
        db_result = await self.use_database_fallback(
            "get_conversation_messages", conversation_id
        )
        
        if db_result:
            return db_result
        
        # Use fallback storage
        return self.fallback_conversations.get(conversation_id, [])
    
    async def save_message_to_conversation(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save message with fallback support.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional metadata dict
            
        Returns:
            True if saved successfully
        """
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "add_message",
                conversation_id,
                role,
                content,
                metadata
            )
            
            if db_result:
                return True
        except Exception as e:
            logger.error(f"Database save failed: {e}", exc_info=True)
        
        # Use fallback storage
        if conversation_id not in self.fallback_conversations:
            self.fallback_conversations[conversation_id] = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        self.fallback_conversations[conversation_id].append(message)
        return True
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> str:
        """
        Create new conversation with fallback support.
        
        Args:
            user_id: User ID
            title: Optional conversation title
            
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "create_conversation", user_id, title
            )
            
            if db_result:
                return str(db_result.get("id", conversation_id))
        except Exception as e:
            logger.debug(f"Database create conversation failed: {e}")
        
        # Use fallback storage
        self.fallback_conversation_metadata[conversation_id] = {
            "user_id": user_id,
            "title": title or "New Conversation",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.fallback_conversations[conversation_id] = []
        return conversation_id
    
    async def get_conversation_list(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of conversations for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of conversation metadata dicts
        """
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "get_user_conversations", user_id
            )
            
            if db_result:
                return db_result
        except Exception as e:
            logger.debug(f"Database get conversations failed: {e}")
        
        # Use fallback storage
        conversations = []
        for conv_id, metadata in self.fallback_conversation_metadata.items():
            if metadata.get("user_id") == user_id:
                conversations.append({
                    "conversation_id": conv_id,
                    "title": metadata.get("title", "Untitled"),
                    "created_at": metadata.get("created_at"),
                    "updated_at": metadata.get("updated_at"),
                    "message_count": len(self.fallback_conversations.get(conv_id, []))
                })
        
        return conversations
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID for ownership verification
            
        Returns:
            True if deleted successfully
        """
        try:
            # Try database first
            db_result = await self.use_database_fallback(
                "delete_conversation", conversation_id
            )
            
            if db_result:
                return True
        except Exception as e:
            logger.debug(f"Database delete conversation failed: {e}")
        
        # Use fallback storage
        if conversation_id in self.fallback_conversations:
            # Verify ownership
            metadata = self.fallback_conversation_metadata.get(conversation_id, {})
            if metadata.get("user_id") == user_id:
                del self.fallback_conversations[conversation_id]
                del self.fallback_conversation_metadata[conversation_id]
                return True
        
        return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences for chat configuration.
        
        Args:
            user_id: User ID
            
        Returns:
            User preferences dict with defaults
        """
        return user_preferences.get(user_id, {
            "model": "gpt-4o",
            "include_reasoning": False,
            "text_format": "text",
            "text_verbosity": "medium",
            "reasoning_effort": "medium"
        })
