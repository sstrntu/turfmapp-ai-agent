from __future__ import annotations

import os
from typing import List, Optional, Dict, Any
from datetime import datetime

import openai
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.conversation import (
    Conversation, Message, MessageRole,
    ConversationCreate, ConversationResponse, MessageCreate, MessageResponse,
    ConversationListResponse
)
from ..models.user import User, UserPreferences
from ..services.user_service import UserService
from ..core.exceptions import NotFoundError, AuthorizationError


class ChatService:
    """Service for chat operations with pure OpenAI integration"""

    def __init__(self):
        # Initialize OpenAI client lazily so backend can start without a key
        api_key = os.getenv("OPENAI_API_KEY")
        self.is_configured = bool(api_key)
        if self.is_configured:
            openai.api_key = api_key

    @staticmethod
    def create_conversation(db: Session, user_id: str, conversation_data: ConversationCreate) -> Conversation:
        """Create a new conversation"""
        # Get user's current system prompt to snapshot it
        user_prefs = UserService.get_user_preferences(db, user_id)
        system_prompt = user_prefs.system_prompt if user_prefs and user_prefs.system_prompt else None
        
        conversation = Conversation(
            user_id=user_id,
            title=conversation_data.title,
            model=conversation_data.model,
            system_prompt=system_prompt  # Snapshot the system prompt
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def get_conversation(db: Session, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Get conversation by ID (user must own it)"""
        return (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
            .first()
        )

    @staticmethod
    def get_user_conversations(
        db: Session, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[ConversationListResponse]:
        """Get user's conversations with message count and last message time"""
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        result = []
        for conv in conversations:
            # Get message count and last message time
            message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
            last_message = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(desc(Message.created_at))
                .first()
            )
            
            result.append(ConversationListResponse(
                id=conv.id,
                title=conv.title,
                model=conv.model,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count,
                last_message_at=last_message.created_at if last_message else None
            ))
        
        return result

    @staticmethod
    def get_conversation_messages(db: Session, conversation_id: str, user_id: str) -> List[Message]:
        """Get messages for a conversation"""
        # Verify user owns the conversation
        conversation = ChatService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

    @staticmethod
    def add_message(db: Session, conversation_id: str, message_data: MessageCreate, user_id: str) -> Message:
        """Add message to conversation"""
        # Verify user owns the conversation
        conversation = ChatService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        message = Message(
            conversation_id=conversation_id,
            role=message_data.role,
            content=message_data.content,
            message_metadata=message_data.message_metadata or {}
        )
        
        db.add(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def build_openai_messages(
        conversation_messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build OpenAI messages array with optional system prompt (ChatGPT-style)"""
        messages = []
        
        # Add system prompt ONLY if user has set one (like ChatGPT Custom Instructions)
        if system_prompt and system_prompt.strip():
            messages.append({
                "role": "system",
                "content": system_prompt.strip()
            })
        
        # Add conversation history
        for msg in conversation_messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        return messages

    async def send_message(
        self,
        db: Session,
        user_id: str,
        conversation_id: str,
        message_content: str,
        attachments: Optional[List[Dict]] = None
    ) -> tuple[Message, Message]:
        """Send message and get AI response"""
        # If OpenAI is not configured, return a graceful error response
        # Add user message
        user_message = ChatService.add_message(
            db, conversation_id,
            MessageCreate(
                role=MessageRole.USER,
                content=message_content,
                message_metadata={"attachments": attachments} if attachments else {}
            ),
            user_id
        )
        if not self.is_configured:
            error_message = ChatService.add_message(
                db, conversation_id,
                MessageCreate(
                    role=MessageRole.ASSISTANT,
                    content=(
                        "Chat is not configured on the server. Please set OPENAI_API_KEY "
                        "for AI responses, or contact an administrator."
                    ),
                    message_metadata={"error": True, "reason": "missing_openai_api_key"}
                ),
                user_id
            )
            return user_message, error_message
        
        # Get conversation and its messages
        conversation = ChatService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        # Get all messages including the one we just added
        all_messages = ChatService.get_conversation_messages(db, conversation_id, user_id)
        
        # Build OpenAI messages with the conversation's system prompt snapshot
        openai_messages = ChatService.build_openai_messages(
            all_messages, 
            conversation.system_prompt
        )
        
        try:
            # Call OpenAI API (pure Chat Completions - like ChatGPT)
            response = await openai.ChatCompletion.acreate(
                model=conversation.model,
                messages=openai_messages,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Extract response
            assistant_content = response.choices[0].message.content
            
            # Add assistant response
            assistant_message = ChatService.add_message(
                db, conversation_id,
                MessageCreate(
                    role=MessageRole.ASSISTANT,
                    content=assistant_content,
                    message_metadata={
                        "model": conversation.model,
                        "usage": response.get("usage", {}),
                        "finish_reason": response.choices[0].get("finish_reason")
                    }
                ),
                user_id
            )
            
            return user_message, assistant_message
            
        except Exception as e:
            # Add error message
            error_message = ChatService.add_message(
                db, conversation_id,
                MessageCreate(
                    role=MessageRole.ASSISTANT,
                    content=f"I encountered an error processing your request: {str(e)}",
                    message_metadata={"error": True, "error_message": str(e)}
                ),
                user_id
            )
            return user_message, error_message

    @staticmethod
    def update_message_rating(
        db: Session, 
        message_id: str, 
        user_id: str, 
        rating: int, 
        feedback: Optional[str] = None
    ) -> Message:
        """Update message rating and feedback"""
        # Get message and verify user owns the conversation
        message = db.query(Message).join(Conversation).filter(
            Message.id == message_id,
            Conversation.user_id == user_id
        ).first()
        
        if not message:
            raise NotFoundError(f"Message {message_id} not found")
        
        message.rating = rating
        if feedback:
            message.feedback = feedback
            
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def delete_conversation(db: Session, conversation_id: str, user_id: str) -> bool:
        """Delete conversation (user must own it)"""
        conversation = ChatService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        db.delete(conversation)
        db.commit()
        return True

    @staticmethod
    def update_conversation_title(
        db: Session, 
        conversation_id: str, 
        user_id: str, 
        title: str
    ) -> Conversation:
        """Update conversation title"""
        conversation = ChatService.get_conversation(db, conversation_id, user_id)
        if not conversation:
            raise NotFoundError(f"Conversation {conversation_id} not found")
        
        conversation.title = title
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def generate_conversation_title(messages: List[Message]) -> str:
        """Generate a title based on the first user message"""
        for message in messages:
            if message.role == MessageRole.USER:
                content = message.content.strip()
                if len(content) > 50:
                    return content[:47] + "..."
                return content
        return "New Conversation"