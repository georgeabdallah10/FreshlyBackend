from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from models.chat import ChatConversation, ChatMessage
from schemas.chat import ChatConversationCreate, ChatMessageCreate


def create_conversation(db: Session, user_id: int, title: Optional[str] = None) -> ChatConversation:
    """Create a new chat conversation"""
    db_conversation = ChatConversation(
        user_id=user_id,
        title=title
    )
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def get_conversation(db: Session, conversation_id: int, user_id: int) -> Optional[ChatConversation]:
    """Get a specific conversation for a user"""
    return db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == user_id
    ).first()


def get_user_conversations(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 20
) -> List[ChatConversation]:
    """Get all conversations for a user, ordered by most recent"""
    return db.query(ChatConversation).filter(
        ChatConversation.user_id == user_id
    ).order_by(desc(ChatConversation.updated_at)).offset(skip).limit(limit).all()


def get_conversation_with_message_count(db: Session, user_id: int, skip: int = 0, limit: int = 20):
    """Get conversations with message count for summary view"""
    return db.query(
        ChatConversation,
        func.count(ChatMessage.id).label('message_count')
    ).outerjoin(ChatMessage).filter(
        ChatConversation.user_id == user_id
    ).group_by(ChatConversation.id).order_by(
        desc(ChatConversation.updated_at)
    ).offset(skip).limit(limit).all()


def add_message(
    db: Session, 
    conversation_id: int, 
    role: str, 
    content: str
) -> ChatMessage:
    """Add a message to a conversation"""
    db_message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content
    )
    db.add(db_message)
    
    # Update conversation's updated_at timestamp
    db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id
    ).update({"updated_at": func.now()})
    
    db.commit()
    db.refresh(db_message)
    return db_message


def get_conversation_messages(
    db: Session, 
    conversation_id: int, 
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[ChatMessage]:
    """Get messages for a specific conversation"""
    # First verify the conversation belongs to the user
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return []
    
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.created_at).offset(skip).limit(limit).all()


def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    """Delete a conversation and all its messages"""
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return False
    
    db.delete(conversation)
    db.commit()
    return True


def update_conversation_title(
    db: Session, 
    conversation_id: int, 
    user_id: int, 
    title: str
) -> Optional[ChatConversation]:
    """Update conversation title"""
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return None
    
    conversation.title = title
    db.commit()
    db.refresh(conversation)
    return conversation
