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
from utils.cache import cached, invalidate_cache_pattern
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

    def _check_api_availability(self) -> None:
        """Check if OpenAI API is configured"""
        if not settings.openai_enabled:
            raise HTTPException(
                status_code=503, 
                detail="Chat service is not configured. OpenAI API key is missing."
            )

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

        try:
            # Cache is now handled by decorator in _call_openai_api
            response = await self._call_openai_api(messages, temperature=0.2, max_tokens=750)
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

            # Invalidate conversation list cache (new message updates timestamps)
            await invalidate_cache_pattern(f"chat_conversations:*:{user.id}:*")

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

    @cached(ttl=3600, key_prefix="chat_response")
    async def _call_openai_api(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Make API call to OpenAI with automatic caching

        Cache TTL: 1 hour (3600s) - saves on expensive API calls for similar prompts
        Cache automatically invalidates after TTL or can be manually cleared
        """
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False
        }

        headers = {"Authorization": f"Bearer {self.openai_api_key}"}

        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.openai_chat_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

    @cached(ttl=60, key_prefix="chat_conversations")
    async def get_conversation_list(
        self,
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 20
    ) -> List[Any]:
        """Get user's conversations with message counts - cached for 60 seconds"""
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

    async def delete_conversation(
        self,
        db: Session,
        user: User,
        conversation_id: int
    ) -> bool:
        """Delete a conversation and all its messages"""
        success = chat_crud.delete_conversation(db, conversation_id, user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Invalidate conversation list cache
        await invalidate_cache_pattern(f"chat_conversations:*:{user.id}:*")

        return success

    async def update_conversation_title(
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

        # Invalidate conversation list cache
        await invalidate_cache_pattern(f"chat_conversations:*:{user.id}:*")

        return conversation

    async def generate_image(
        self,
        db: Session,
        user: User,
        request: ImageGenerationRequest
    ) -> ImageGenerationResponse:
        """Generate an image using OpenAI's DALL-E - pure utility endpoint with no conversation tracking"""
        self._check_api_availability()

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

            return ImageGenerationResponse(
                image_url=image_url,
                prompt=request.prompt
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
        user_message = chat_crud.add_message(
            db, conversation_id, "user", "Uploaded grocery image for scanning"
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # System prompt for grocery scanning with strict JSON schema
            system_prompt = """You are a grocery item recognition expert. Analyze images and identify all visible grocery items.
            
Return a JSON object with this EXACT structure:
{
  "items": [
    {
      "name": "specific item name",
      "quantity": "amount with unit (e.g., '3 pieces', '2 lbs', '1 bottle')",
      "category": "category (fruits/vegetables/dairy/meat/snacks/beverages/pantry/frozen/bakery/other)",
      "confidence": 0.95
    }
  ],
  "analysis_notes": "observations about image quality or identification challenges"
}

Guidelines:
- Be specific with names (e.g., "Red Delicious Apples" not "Apples")
- Estimate quantities realistically with proper units
- Use standard categories: fruits, vegetables, dairy, meat, snacks, beverages, pantry, frozen, bakery, other
- Confidence: 0.9-1.0 (certain), 0.7-0.9 (likely), 0.5-0.7 (possible), <0.5 (uncertain)
- Only include items you can identify with reasonable confidence
- Mention image quality issues in analysis_notes"""

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
                                "text": "Analyze this grocery image and identify all items with their quantities, categories, and confidence scores."
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
                "temperature": 0.1,  # Low temperature for consistent results
                "response_format": {"type": "json_object"}  # Force JSON output
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
                
                # Validate the response structure
                if not isinstance(parsed_data, dict) or "items" not in parsed_data:
                    logger.error(f"Invalid response structure: {ai_response}")
                    raise ValueError("Response missing 'items' array")
                
                # Parse each item with validation
                items = []
                for item_data in parsed_data.get("items", []):
                    try:
                        # Validate required fields
                        if not all(key in item_data for key in ["name", "quantity", "category", "confidence"]):
                            logger.warning(f"Skipping item with missing fields: {item_data}")
                            continue
                        
                        # Create GroceryItem with validated data
                        item = GroceryItem(
                            name=str(item_data["name"]).strip(),
                            quantity=str(item_data["quantity"]).strip(),
                            category=str(item_data["category"]).strip().lower(),
                            confidence=float(item_data["confidence"])
                        )
                        items.append(item)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid item: {item_data}, error: {e}")
                        continue
                
                analysis_notes = parsed_data.get("analysis_notes", "")
                
                # Log success metrics
                logger.info(f"Successfully parsed {len(items)} items from grocery scan")
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"Failed to parse AI response: {e}, response: {ai_response[:500]}")
                # Fallback: return empty result with error note
                items = []
                analysis_notes = f"Error parsing AI response: {str(e)}. The image may not contain recognizable grocery items or the quality may be too poor."
            
            # Save AI response as a message
            response_text = f"Grocery scan completed. Found {len(items)} items."
            if analysis_notes:
                response_text += f"\n\nNotes: {analysis_notes}"
            
            ai_message = chat_crud.add_message(
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
