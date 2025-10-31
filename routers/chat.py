# routers/chat.py  
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.deps import get_current_user, get_db
from models.user import User
from schemas.chat import (
    ChatRequest, ChatResponse, ChatConversation, ChatConversationSummary,
    ChatMessage, ChatConversationCreate
)
from services.chat_service import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


# Legacy endpoint - keeping for backward compatibility
class ChatIn(BaseModel):
    prompt: str                    # full prompt from the frontend
    system: str | None = None      # optional system prompt (also from frontend)


@router.post("/legacy") 
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
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    conversations_with_counts = chat_service.get_conversation_list(
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
    chat_service.update_conversation_title(db, current_user, conversation_id, title)
    return {"message": "Title updated successfully"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    chat_service.delete_conversation(db, current_user, conversation_id)
    return {"message": "Conversation deleted successfully"}  