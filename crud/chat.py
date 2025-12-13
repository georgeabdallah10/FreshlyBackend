from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
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
    content: str,
    is_internal: int = 0
) -> ChatMessage:
    """Add a message to a conversation

    Args:
        db: Database session
        conversation_id: ID of the conversation
        role: Message role ('user', 'assistant', 'system')
        content: Message content
        is_internal: 0 for visible messages, 1 for internal/hidden messages
    """
    db_message = ChatMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        is_internal=is_internal
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
    limit: int = 100,
    include_internal: bool = False
) -> List[ChatMessage]:
    """Get messages for a specific conversation

    Args:
        db: Database session
        conversation_id: ID of the conversation
        user_id: ID of the user (for ownership verification)
        skip: Number of messages to skip
        limit: Maximum number of messages to return
        include_internal: If False, excludes internal/hidden messages (default for frontend)
    """
    # First verify the conversation belongs to the user
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return []

    query = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    )

    # Filter out internal messages unless explicitly requested
    if not include_internal:
        query = query.filter(ChatMessage.is_internal == 0)

    return query.order_by(ChatMessage.created_at).offset(skip).limit(limit).all()


def get_system_message(db: Session, conversation_id: int) -> Optional[ChatMessage]:
    """Get the first system message for a conversation (the locked system prompt)"""
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.role == "system",
        ChatMessage.is_internal == 0  # The main system prompt is not internal
    ).order_by(asc(ChatMessage.created_at)).first()


def get_internal_state_message(db: Session, conversation_id: int) -> Optional[ChatMessage]:
    """Get the internal assistant state message for a conversation"""
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.role == "system",
        ChatMessage.is_internal == 1
    ).order_by(desc(ChatMessage.created_at)).first()


def update_internal_state_message(
    db: Session,
    conversation_id: int,
    content: str
) -> ChatMessage:
    """Update or create the internal assistant state message"""
    existing = get_internal_state_message(db, conversation_id)
    if existing:
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing
    else:
        return add_message(db, conversation_id, "system", content, is_internal=1)


def get_messages_for_context(
    db: Session,
    conversation_id: int,
    user_limit: int = 6,
    assistant_limit: int = 6
) -> List[ChatMessage]:
    """Get messages for AI context building.

    Returns:
        - The first system message (the locked system prompt)
        - The internal state message if exists
        - Last N user messages
        - Last N assistant messages
        All ordered by created_at for proper context flow.
    """
    messages = []

    # Get the first system message (locked system prompt)
    system_msg = get_system_message(db, conversation_id)
    if system_msg:
        messages.append(system_msg)

    # Get internal state message (if exists)
    internal_state = get_internal_state_message(db, conversation_id)
    if internal_state:
        messages.append(internal_state)

    # Get last N user messages
    user_messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.role == "user"
    ).order_by(desc(ChatMessage.created_at)).limit(user_limit).all()

    # Get last N assistant messages
    assistant_messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.role == "assistant"
    ).order_by(desc(ChatMessage.created_at)).limit(assistant_limit).all()

    # Combine user and assistant messages
    conversation_messages = user_messages + assistant_messages

    # Sort by created_at to maintain conversation order
    conversation_messages.sort(key=lambda x: x.created_at)

    messages.extend(conversation_messages)

    return messages


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
