# routers/chat.py
import logging
import base64
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.deps import get_current_user, get_db
from core.rate_limit import rate_limiter_with_user, rate_limiter
from models.user import User
from schemas.chat import (
    ChatRequest, ChatResponse, ChatConversation, ChatConversationSummary,
    ChatMessage, ChatConversationCreate, ImageGenerationRequest, 
    ImageGenerationResponse, ImageScanRequest, ImageScanResponse
)
from services.chat_service import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# Legacy endpoint - keeping for backward compatibility
class ChatIn(BaseModel):
    prompt: str                    # full prompt from the frontend
    system: str | None = None      # optional system prompt (also from frontend)


@router.post("/legacy", dependencies=[Depends(rate_limiter("chat", require_auth=False))])
async def chat_legacy(inp: ChatIn):
    """Legacy chat endpoint without conversation history"""
    logger.info(f"Legacy chat request: {len(inp.prompt)} characters")
    
    try:
        response = await chat_service.send_legacy_message(
            prompt=inp.prompt,
            system_prompt=inp.system
        )
        return JSONResponse({"reply": response})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Legacy chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat service error")


# New chat endpoint with conversation history
@router.post("", response_model=ChatResponse)
async def chat(
    req: Request,
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit = Depends(rate_limiter_with_user("chat"))
):
    """Send a chat message and get AI response with conversation history"""
    logger.info(f"Chat request from user {current_user.id}: {len(request.prompt)} characters")
    
    return await chat_service.send_message_with_history(db, current_user, request)


@router.get("/conversations", response_model=List[ChatConversationSummary])
async def get_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's chat conversations with message counts"""
    conversations_with_counts = await chat_service.get_conversation_list(
        db, current_user, skip, limit
    )

    return [
        ChatConversationSummary(
            id=conv.id,
            user_id=conv.user_id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count
        )
        for conv, count in conversations_with_counts
    ]


@router.get("/conversations/{conversation_id}", response_model=ChatConversation)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with all messages"""
    return chat_service.get_conversation_details(db, current_user, conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessage])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific conversation"""
    # Import here to avoid circular imports
    import crud.chat as chat_crud
    
    messages = chat_crud.get_conversation_messages(
        db, conversation_id, current_user.id, skip, limit
    )
    return messages


@router.post("/conversations", response_model=ChatConversation)
async def create_conversation(
    conversation: ChatConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat conversation"""
    # Import here to avoid circular imports
    import crud.chat as chat_crud
    
    return chat_crud.create_conversation(db, current_user.id, conversation.title)


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int,
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation title"""
    await chat_service.update_conversation_title(db, current_user, conversation_id, title)
    return {"message": "Title updated successfully"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    await chat_service.delete_conversation(db, current_user, conversation_id)
    return {"message": "Conversation deleted successfully"}


@router.post("/generate-image", response_model=ImageGenerationResponse)
async def generate_image(
    req: Request,
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit = Depends(rate_limiter_with_user("chat-image"))
):
    """Generate an image using OpenAI's DALL-E"""
    logger.info(f"Image generation request from user {current_user.id}: {request.prompt[:100]}...")
    
    return await chat_service.generate_image(db, current_user, request)


@router.post("/scan-grocery", response_model=ImageScanResponse)
async def scan_grocery_image(
    req: Request,
    request: ImageScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit = Depends(rate_limiter_with_user("chat"))
):
    """Scan a grocery image to identify items, quantities, and categories"""
    logger.info(f"Grocery scan request from user {current_user.id}")
    
    return await chat_service.scan_grocery_image(db, current_user, request)


@router.post("/scan-grocery-proxy", response_model=ImageScanResponse)
async def scan_grocery_proxy(
    req: Request,
    file: UploadFile = File(..., description="Image file (JPEG/PNG, max 2MB)"),
    scan_type: str = Form(..., description="Type of scan: 'groceries' or 'receipt'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit = Depends(rate_limiter_with_user("chat"))
):
    """
    iOS Safari-compatible endpoint for scanning grocery/receipt images.

    Accepts multipart/form-data instead of JSON with base64. This endpoint:
    - Accepts image file uploads (JPEG/PNG, max 2MB)
    - Validates scan type (groceries or receipt)
    - Converts to base64 and uses existing AI processing
    - Returns same response format as /scan-grocery

    Args:
        file: Image file (JPEG or PNG, max 2MB)
        scan_type: Either "groceries" or "receipt"

    Returns:
        ImageScanResponse with items array and total_items count
    """
    # Validate scan type
    if scan_type not in ["groceries", "receipt"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid scan_type. Must be 'groceries' or 'receipt'"
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Must be an image (image/jpeg or image/png)"
        )
    
    logger.info(
        f"Grocery proxy scan request from user {current_user.id}: "
        f"type={scan_type}, file={file.filename}, content_type={file.content_type}"
    )
    
    try:
        # Read file contents
        contents = await file.read()
        
        # Validate file size (2MB limit)
        if len(contents) > 2 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 2MB"
            )
        
        # Convert to base64
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        logger.debug(f"Converted image to base64: {len(base64_image)} characters")
        
        # Create ImageScanRequest to reuse existing service
        scan_request = ImageScanRequest(
            image_data=base64_image
        )
        
        # Call existing AI processing service - same as /scan-grocery endpoint
        result = await chat_service.scan_grocery_image(db, current_user, scan_request)
        
        logger.info(f"Scan completed: {result.total_items} items found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing grocery proxy scan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )