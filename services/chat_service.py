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
from services.chat_image_storage import chat_image_storage
import crud.chat as chat_crud
import httpx

logger = logging.getLogger(__name__)


# Strong default system prompt that enforces conversational behavior
DEFAULT_SYSTEM_PROMPT = """You are SAVR AI, a friendly and helpful assistant for the SAVR meal planning app.

CRITICAL BEHAVIORAL RULES:
1. You REMEMBER the entire conversation history. Never act like you're meeting the user for the first time after the initial greeting.
2. NEVER reintroduce yourself after the first message. Do not say "Hello! I'm SAVR AI" on subsequent messages.
3. NEVER restart or reset tasks. If a task is in progress, continue it. Do not ask "Would you like to start?" if already started.
4. Ask follow-up questions to gather more information instead of making assumptions.
5. Reference previous messages when relevant: "As we discussed earlier..." or "Building on what you mentioned..."
6. If the user seems confused about context, summarize what you discussed before continuing.
7. Be concise but helpful. Match the user's energy and communication style.

You can help with:
- Meal planning and recipe suggestions
- Grocery list management
- Pantry organization
- Dietary advice and nutritional information
- Cooking tips and techniques

Always maintain conversation continuity and remember what the user has told you."""

FOOD_IMAGE_SYSTEM_PROMPT = """You may ONLY analyze food-related images. If an image or request is not about meals, groceries, cooking, ingredients, or nutrition, politely refuse and ask for a food-related image instead."""


# Internal state message template for assistant intent persistence
INTERNAL_STATE_TEMPLATE = """[ASSISTANT STATE - DO NOT REFERENCE DIRECTLY]
Mode: {mode}
Context: {context}
Instructions: Continue the conversation naturally. Do not restart completed tasks. Reference prior messages when relevant."""


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
        Send a message to AI without conversation history (legacy endpoint).
        This endpoint is STATELESS and does NOT write to database.

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
            response = await self._call_openai_api_uncached(messages, temperature=0.2, max_tokens=750)
            return response

        except Exception as e:
            logger.error(f"Legacy chat error: {e}")
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    async def send_message_with_history(
        self,
        db: Session,
        user: User,
        request: ChatRequest,
        image_data: Optional[str] = None,
        image_mime: Optional[str] = None,
    ) -> ChatResponse:
        """
        Send a message to AI with conversation history.

        BEHAVIORAL RULES:
        1. System prompt is LOCKED per conversation - only accepted on new conversations
        2. Existing conversations always use their stored system prompt
        3. Context includes system prompt + last 6 user + last 6 assistant messages
        4. Internal state message persists assistant intent

        Args:
            db: Database session
            user: Current user
            request: Chat request data

            Returns:
                Chat response with conversation details
        """
        self._check_api_availability()

        try:
            text_prompt = request.prompt  # normalized upstream

            # Determine if this is a new or existing conversation
            is_new_conversation = request.conversation_id is None

            if is_new_conversation:
                # Create new conversation
                conversation = chat_crud.create_conversation(db, user.id)

                # Determine system prompt: user-provided or default
                system_prompt = request.system if request.system else DEFAULT_SYSTEM_PROMPT

                # Store the system prompt as the FIRST message (locked)
                chat_crud.add_message(db, conversation.id, "system", system_prompt, is_internal=0)

                # Create initial internal state message
                initial_state = INTERNAL_STATE_TEMPLATE.format(
                    mode="conversation",
                    context="New conversation started. User is exploring the chat."
                )
                chat_crud.add_message(db, conversation.id, "system", initial_state, is_internal=1)

                logger.info(f"Created new conversation {conversation.id} for user {user.id}")

            else:
                # Get existing conversation - enforce ownership
                conversation = chat_crud.get_conversation(db, request.conversation_id, user.id)
                if not conversation:
                    raise HTTPException(
                        status_code=404,
                        detail="Conversation not found or does not belong to you"
                    )

                # IGNORE any system prompt sent with existing conversation
                if request.system:
                    logger.debug(
                        f"Ignoring system prompt for existing conversation {conversation.id} - "
                        "system prompts are locked after creation"
                    )

            # Build message context for OpenAI
            messages = await self._build_message_context(db, conversation.id, text_prompt)

            # Upload image to Supabase Storage if present (must succeed before saving message)
            uploaded_image_url = None
            if image_data:
                uploaded_image_url, storage_path = chat_image_storage.upload_image(
                    image_base64=image_data,
                    mime_type=image_mime or "image/jpeg",
                    user_id=user.id,
                    conversation_id=conversation.id
                )
                if not uploaded_image_url:
                    logger.error(
                        f"CHAT_IMAGE_UPLOAD_FAILED | user_id={user.id} | "
                        f"conversation_id={conversation.id}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to upload image. Please try again."
                    )
                logger.info(
                    f"CHAT_IMAGE_UPLOADED | user_id={user.id} | "
                    f"conversation_id={conversation.id} | url={uploaded_image_url}"
                )

            # Save user message (with image_url if uploaded)
            user_message = chat_crud.add_message(
                db, conversation.id, "user", text_prompt, image_url=uploaded_image_url
            )

            # Get AI response (NO CACHING for chat - responses must be fresh)
            if image_data:
                ai_response = await self._call_openai_api_multimodal(
                    messages, image_data, image_mime or "image/jpeg"
                )
            else:
                ai_response = await self._call_openai_api_uncached(messages)

            # Save AI response
            ai_message = chat_crud.add_message(
                db, conversation.id, "assistant", ai_response
            )

            # Update internal state based on conversation context
            await self._update_internal_state(db, conversation.id, text_prompt, ai_response)

            # Invalidate conversation list cache (new message updates timestamps)
            await invalidate_cache_pattern(f"chat_conversations:*:{user.id}:*")

            logger.info(f"Chat completed for user {user.id}, conversation {conversation.id}")

            return ChatResponse(
                reply=ai_response,
                conversation_id=conversation.id,
                message_id=ai_message.id,
                image_url=uploaded_image_url
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat with history error: {e}")
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    async def _build_message_context(
        self,
        db: Session,
        conversation_id: int,
        current_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Build message context for OpenAI API call.

        Structure:
        1. System message (locked, stored in DB)
        2. Internal state message (hidden from frontend)
        3. Last 6 user messages + last 6 assistant messages (ordered by time)
        4. Current user prompt

        This ensures the AI has proper context without feeling like a reset.
        """
        messages = []

        # Get messages from CRUD (handles fetching system, internal state, and history)
        context_messages = chat_crud.get_messages_for_context(
            db, conversation_id, user_limit=6, assistant_limit=6
        )

        # Convert to OpenAI message format
        for msg in context_messages:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user prompt (not yet saved to DB)
        messages.append({"role": "user", "content": current_prompt})

        return messages

    async def _update_internal_state(
        self,
        db: Session,
        conversation_id: int,
        user_prompt: str,
        ai_response: str
    ) -> None:
        """
        Update the internal assistant state message based on conversation context.

        This helps maintain continuity by persisting the assistant's understanding
        of the conversation's current state.
        """
        # Determine mode based on conversation content
        mode = "conversation"
        context = "General chat in progress."

        # Simple heuristics for mode detection (can be enhanced)
        prompt_lower = user_prompt.lower()
        if any(word in prompt_lower for word in ["recipe", "cook", "meal", "food", "eat"]):
            mode = "meal_planning"
            context = "User is discussing meals or recipes."
        elif any(word in prompt_lower for word in ["grocery", "shop", "buy", "list"]):
            mode = "grocery_planning"
            context = "User is working on grocery lists."
        elif any(word in prompt_lower for word in ["pantry", "stock", "inventory"]):
            mode = "pantry_management"
            context = "User is managing their pantry."

        state_content = INTERNAL_STATE_TEMPLATE.format(mode=mode, context=context)
        chat_crud.update_internal_state_message(db, conversation_id, state_content)

    async def _call_openai_api_uncached(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Make API call to OpenAI WITHOUT caching.

        IMPORTANT: Chat responses must always be generated fresh.
        Caching chat responses breaks conversational flow.
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

    async def _call_openai_api_multimodal(
        self,
        messages: List[Dict[str, Any]],
        image_data: str,
        image_mime: str,
    ) -> str:
        """
        Send a multimodal request (text + image) to OpenAI Vision.
        Inserts a guardrail system prompt to keep analysis food-only.
        """
        headers = {"Authorization": f"Bearer {self.openai_api_key}"}

        history = messages[:-1] if messages else []
        user_text = messages[-1]["content"] if messages else ""

        payload = {
            "model": self.vision_model,
            "messages": history
            + [
                {"role": "system", "content": FOOD_IMAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime};base64,{image_data}"
                            },
                        },
                    ],
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.openai_chat_url, headers=headers, json=payload
            )
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
        """Get specific conversation with all messages (excluding internal messages)"""
        conversation = chat_crud.get_conversation(db, conversation_id, user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Filter out internal messages before returning to frontend
        # This ensures hidden system messages (assistant state) are not exposed
        conversation.messages = [msg for msg in conversation.messages if msg.is_internal == 0]

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

            return ImageScanResponse(
                items=items,
                total_items=len(items),
                analysis_notes=analysis_notes
            )

        except httpx.RequestError as e:
            logger.error(f"Request error during image scanning: {e}")
            raise HTTPException(status_code=503, detail="Image scanning service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error during image scanning: {e}")
            raise HTTPException(status_code=500, detail="Image scanning failed")


# Global service instance
chat_service = ChatService()
