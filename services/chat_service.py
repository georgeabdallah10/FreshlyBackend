"""
Chat service layer for handling business logic related to chat functionality.
This separates business logic from the API endpoints for better maintainability.
"""
import logging
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from core.settings import settings
from models.user import User
from schemas.chat import ChatRequest, ChatResponse, ChatConversation, ChatMessage
import crud.chat as chat_crud
import httpx

logger = logging.getLogger(__name__)


class ChatService:
    """Service class for chat-related business logic"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        self.default_model = "gpt-4o-mini"
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self._response_cache: Dict[str, str] = {}  # Simple in-memory cache

    def _check_api_availability(self) -> None:
        """Check if OpenAI API is configured"""
        if not self.openai_api_key:
            raise HTTPException(
                status_code=503, 
                detail="Chat service is not configured. OpenAI API key is missing."
            )

    def _generate_cache_key(self, messages: List[Dict[str, Any]]) -> str:
        """Generate cache key for AI responses based on message content"""
        content = str(messages)
        return hashlib.md5(content.encode()).hexdigest()

    async def send_legacy_message(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send a message to AI without conversation history (legacy endpoint)
        
        Args:
            prompt: User message
            system_prompt: Optional system prompt
            
        Returns:
            AI response text
        """
        self._check_api_availability()
        
        messages = []
        system_text = system_prompt or "Return ONLY a valid, minified JSON object. No prose."
        messages.append({"role": "system", "content": system_text})
        messages.append({"role": "user", "content": prompt})

        # Check cache first
        cache_key = self._generate_cache_key(messages)
        if cache_key in self._response_cache:
            logger.info("Returning cached AI response")
            return self._response_cache[cache_key]

        try:
            response = await self._call_openai_api(messages, temperature=0.2, max_tokens=750)
            
            # Cache the response
            self._response_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Legacy chat error: {e}")
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    async def send_message_with_history(
        self,
        db: Session,
        user: User,
        request: ChatRequest
    ) -> ChatResponse:
        """
        Send a message to AI with conversation history
        
        Args:
            db: Database session
            user: Current user
            request: Chat request data
            
        Returns:
            Chat response with conversation details
        """
        self._check_api_availability()
        
        try:
            # Get or create conversation
            conversation = await self._get_or_create_conversation(db, user, request.conversation_id)
            
            # Build message history
            messages = await self._build_message_history(db, conversation, request)
            
            # Save user message
            user_message = chat_crud.add_message(
                db, conversation.id, "user", request.prompt
            )
            
            # Get AI response
            ai_response = await self._call_openai_api(messages)
            
            # Save AI response
            ai_message = chat_crud.add_message(
                db, conversation.id, "assistant", ai_response
            )
            
            logger.info(f"Chat completed for user {user.id}, conversation {conversation.id}")
            
            return ChatResponse(
                reply=ai_response,
                conversation_id=conversation.id,
                message_id=ai_message.id
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat with history error: {e}")
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    async def _get_or_create_conversation(
        self, 
        db: Session, 
        user: User, 
        conversation_id: Optional[int]
    ) -> ChatConversation:
        """Get existing conversation or create new one"""
        if conversation_id:
            conversation = chat_crud.get_conversation(db, conversation_id, user.id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation
        else:
            return chat_crud.create_conversation(db, user.id)

    async def _build_message_history(
        self, 
        db: Session, 
        conversation: ChatConversation, 
        request: ChatRequest
    ) -> List[Dict[str, str]]:
        """Build message history for AI context"""
        messages = []
        
        # Add system message
        system_text = request.system or "You are a helpful AI assistant."
        messages.append({"role": "system", "content": system_text})
        
        # Add conversation history (last 10 messages to avoid token limits)
        history = chat_crud.get_conversation_messages(
            db, conversation.id, conversation.user_id, skip=0, limit=10
        )
        
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": request.prompt})
        
        return messages

    async def _call_openai_api(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Make API call to OpenAI"""
        payload = {
            "model": self.default_model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False
        }
        
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}
        
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.openai_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]

    def get_conversation_list(
        self, 
        db: Session, 
        user: User, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Any]:
        """Get user's conversations with message counts"""
        return chat_crud.get_conversation_with_message_count(
            db, user.id, skip, limit
        )

    def get_conversation_details(
        self, 
        db: Session, 
        user: User, 
        conversation_id: int
    ) -> ChatConversation:
        """Get specific conversation with all messages"""
        conversation = chat_crud.get_conversation(db, conversation_id, user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation

    def delete_conversation(
        self, 
        db: Session, 
        user: User, 
        conversation_id: int
    ) -> bool:
        """Delete a conversation and all its messages"""
        success = chat_crud.delete_conversation(db, conversation_id, user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return success

    def update_conversation_title(
        self, 
        db: Session, 
        user: User, 
        conversation_id: int, 
        title: str
    ) -> ChatConversation:
        """Update conversation title"""
        conversation = chat_crud.update_conversation_title(
            db, conversation_id, user.id, title
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation


# Global service instance
chat_service = ChatService()
