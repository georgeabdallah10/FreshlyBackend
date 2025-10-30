# routers/chat.py  
import os, httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from core.deps import get_current_user, get_db
from core.settings import settings
from models.user import User
from schemas.chat import (
    ChatRequest, ChatResponse, ChatConversation, ChatConversationSummary,
    ChatMessage, ChatConversationCreate
)
import crud.chat as chat_crud

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"  # Current available model - gpt-5-nano may not be publicly available yet

router = APIRouter(prefix="/chat", tags=["chat"])


# Legacy endpoint - keeping for backward compatibility
class ChatIn(BaseModel):
    prompt: str                    # full prompt from the frontend
    system: str | None = None      # optional system prompt (also from frontend)


@router.post("/legacy") 
async def chat_legacy(inp: ChatIn):
    """Legacy chat endpoint without conversation history"""
    messages = []

    # Use explicit system message if provided; otherwise set a minimal hard rule
    system_text = inp.system or "Return ONLY a valid, minified JSON object. No prose."
    messages.append({"role": "system", "content": system_text})

    # User content is the actual inputs + JSON directive
    messages.append({"role": "user", "content": inp.prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 750,
        "stream": False
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OPENAI_URL, headers=headers, json=payload)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return JSONResponse({"reply": text})


# New chat endpoint with conversation history
@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message and get AI response with conversation history"""
    
    # Get or create conversation
    if request.conversation_id:
        conversation = chat_crud.get_conversation(db, request.conversation_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = chat_crud.create_conversation(db, current_user.id)
    
    # Get conversation history
    messages = []
    
    # Add system message
    system_text = request.system or "You are a helpful AI assistant."
    messages.append({"role": "system", "content": system_text})
    
    # Add conversation history (last 10 messages to avoid token limits)
    history = chat_crud.get_conversation_messages(
        db, conversation.id, current_user.id, skip=0, limit=10
    )
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current user message
    messages.append({"role": "user", "content": request.prompt})
    
    # Save user message to database
    user_message = chat_crud.add_message(
        db, conversation.id, "user", request.prompt
    )
    
    # Call OpenAI API
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "stream": False
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(OPENAI_URL, headers=headers, json=payload)
        r.raise_for_status()
        ai_response = r.json()["choices"][0]["message"]["content"]
        
        # Save AI response to database
        ai_message = chat_crud.add_message(
            db, conversation.id, "assistant", ai_response
        )
        
        return ChatResponse(
            reply=ai_response,
            conversation_id=conversation.id,
            message_id=ai_message.id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.get("/conversations", response_model=List[ChatConversationSummary])
async def get_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's chat conversations with message counts"""
    conversations_with_counts = chat_crud.get_conversation_with_message_count(
        db, current_user.id, skip, limit
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
    conversation = chat_crud.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessage])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific conversation"""
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
    return chat_crud.create_conversation(db, current_user.id, conversation.title)


@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int,
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation title"""
    conversation = chat_crud.update_conversation_title(
        db, conversation_id, current_user.id, title
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Title updated successfully"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    success = chat_crud.delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}  