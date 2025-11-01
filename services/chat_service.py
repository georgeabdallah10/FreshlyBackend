"""
Chat service layer for handling business logic related to chat functionality.
This separates business logic from the API endpoints for better maintainability.
"""
import logging
import hashlib
import base64
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from core.settings import settings
from models.user import User
from schemas.chat import (
    ChatRequest, ChatResponse, ChatConversation, ChatMessage,
    ImageGenerationRequest, ImageGenerationResponse,
    ImageScanRequest, ImageScanResponse, GroceryItem
)
import crud.chat as chat_crud
import httpx

logger = logging.getLogger(__name__)


class ChatService:
    """Service class for chat-related business logic"""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.openai_chat_url = "https://api.openai.com/v1/chat/completions"
        self.openai_image_url = "https://api.openai.com/v1/images/generations"
        self.default_model = "gpt-4o-mini"
        self.vision_model = "gpt-4o"  # Better for image analysis
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE
        self._response_cache: Dict[str, str] = {}  # Simple in-memory cache

    def _check_api_availability(self) -> None:
        """Check if OpenAI API is configured"""
        if not settings.openai_enabled:
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

    async def generate_image(
        self, 
        db: Session, 
        user: User, 
        request: ImageGenerationRequest
    ) -> ImageGenerationResponse:
        """Generate an image using OpenAI's DALL-E"""
        self._check_api_availability()
        
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = chat_crud.create_conversation(
                db, user.id, f"Image: {request.prompt[:50]}..."
            )
            conversation_id = conversation.id
        
        # Save user's request as a message
        user_message = chat_crud.create_message(
            db, conversation_id, "user", f"Generate image: {request.prompt}"
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "dall-e-3",  # Use DALL-E 3 for best quality
                "prompt": request.prompt,
                "size": request.size,
                "quality": request.quality,
                "style": request.style,
                "n": 1  # Generate 1 image
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.openai_image_url,
                    headers=headers,
                    json=payload
                )
                
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"OpenAI Image API error: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Image generation failed: {error_text}"
                )
                
            result = response.json()
            image_url = result["data"][0]["url"]
            
            # Save AI response as a message
            ai_message = chat_crud.create_message(
                db, conversation_id, "assistant", 
                f"Generated image for: {request.prompt}\nImage URL: {image_url}"
            )
            
            return ImageGenerationResponse(
                image_url=image_url,
                prompt=request.prompt,
                conversation_id=conversation_id,
                message_id=ai_message.id
            )
            
        except httpx.RequestError as e:
            logger.error(f"Request error during image generation: {e}")
            raise HTTPException(status_code=503, detail="Image generation service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error during image generation: {e}")
            raise HTTPException(status_code=500, detail="Image generation failed")

    async def scan_grocery_image(
        self, 
        db: Session, 
        user: User, 
        request: ImageScanRequest
    ) -> ImageScanResponse:
        """Analyze grocery image using OpenAI's Vision API"""
        self._check_api_availability()
        
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation = chat_crud.create_conversation(
                db, user.id, "Grocery Scan"
            )
            conversation_id = conversation.id
        
        # Save user's request as a message
        user_message = chat_crud.create_message(
            db, conversation_id, "user", "Uploaded grocery image for scanning"
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # System prompt for grocery scanning
            system_prompt = """You are a grocery item recognition expert. Analyze the uploaded image and identify all grocery items visible. For each item, provide:
1. Name of the item (be specific, e.g., "Red Delicious Apples" not just "Apples")
2. Estimated quantity (e.g., "3 pieces", "2 lbs", "1 bottle")
3. Category (fruits, vegetables, dairy, meat, snacks, beverages, pantry, frozen, etc.)
4. Confidence score (0.0 to 1.0)

Return the response as a JSON object with this exact structure:
{
  "items": [
    {
      "name": "item name",
      "quantity": "estimated quantity",
      "category": "category",
      "confidence": 0.95
    }
  ],
  "analysis_notes": "Any additional observations about the image quality, lighting, or items that were hard to identify"
}

Be thorough but only include items you can clearly identify. If the image quality is poor or items are unclear, mention this in analysis_notes."""

            payload = {
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this grocery image and identify all items with their quantities and categories."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{request.image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1  # Low temperature for consistent parsing
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.openai_chat_url,
                    headers=headers,
                    json=payload
                )
                
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"OpenAI Vision API error: {response.status_code} - {error_text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Image analysis failed: {error_text}"
                )
                
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # Parse the JSON response
            try:
                parsed_data = json.loads(ai_response)
                items = [
                    GroceryItem(**item) for item in parsed_data.get("items", [])
                ]
                analysis_notes = parsed_data.get("analysis_notes")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse AI response: {e}")
                # Fallback: treat as plain text
                items = []
                analysis_notes = f"AI response could not be parsed as JSON: {ai_response}"
            
            # Save AI response as a message
            response_text = f"Grocery scan completed. Found {len(items)} items."
            if analysis_notes:
                response_text += f"\n\nNotes: {analysis_notes}"
            
            ai_message = chat_crud.create_message(
                db, conversation_id, "assistant", response_text
            )
            
            return ImageScanResponse(
                items=items,
                total_items=len(items),
                analysis_notes=analysis_notes,
                conversation_id=conversation_id,
                message_id=ai_message.id
            )
            
        except httpx.RequestError as e:
            logger.error(f"Request error during image scanning: {e}")
            raise HTTPException(status_code=503, detail="Image scanning service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error during image scanning: {e}")
            raise HTTPException(status_code=500, detail="Image scanning failed")


# Global service instance
chat_service = ChatService()
