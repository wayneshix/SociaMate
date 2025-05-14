from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import uuid
import logging
import time
from datetime import datetime
from pydantic import BaseModel, Field
from app.services.infoextractor import InfoExtractorService
from app.database import get_db
from app.services.summarizer import summarizer_service
from app.repositories.message_repository import message_repository
from app.services.context import context_service
from app.services.response_drafter import response_drafter_service

router = APIRouter()
extractor = InfoExtractorService()
logger = logging.getLogger(__name__)

class TextRequest(BaseModel):
    text: str
    as_user: Optional[str] = None

class MessageRequest(BaseModel):
    author: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class MessagesUploadRequest(BaseModel):
    messages: List[MessageRequest]
    conversation_id: Optional[str] = None

class ContextResponse(BaseModel):
    context: str
    context_size: int
    processing_time: float

class SummaryResponse(BaseModel):
    summary: str
    processing_time: float

class DraftResponse(BaseModel):
    draft: str
    processing_time: float

@router.post("/summarize")
async def summarize(request: Request):
    """Legacy endpoint for summarizing text directly."""
    data = await request.json()
    text = data.get("text", "")

    if not text:
        return {"error": "No text provided."}

    start_time = time.time()
    summary = summarizer_service.summarize_conversation(text)
    processing_time = time.time() - start_time
    
    return {
        "summary": summary,
        "processing_time": processing_time
    }

@router.post("/conversations", status_code=201)
async def create_conversation(
    request: MessagesUploadRequest,
    db: Session = Depends(get_db)
):
    """Create a new conversation from messages."""
    # Generate conversation ID if not provided
    conversation_id = request.conversation_id or str(uuid.uuid4())
    
    # Convert Pydantic models to dictionaries
    messages_data = []
    for msg in request.messages:
        messages_data.append(msg.dict(exclude_none=True))
    
    # Create messages
    start_time = time.time()
    messages = message_repository.create_messages(db, conversation_id, messages_data)
    processing_time = time.time() - start_time
    
    return {
        "conversation_id": conversation_id,
        "message_count": len(messages),
        "processing_time": processing_time
    }

@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(
    conversation_id: str,
    request: MessageRequest,
    db: Session = Depends(get_db)
):
    """Add a message to an existing conversation."""
    # Create message
    start_time = time.time()
    message = message_repository.create_message(
        db,
        conversation_id,
        request.author,
        request.content,
        request.timestamp,
        request.metadata
    )
    processing_time = time.time() - start_time
    
    # Process chunks (async in a real implementation)
    message_repository._process_conversation_chunks(db, conversation_id)
    
    return {
        "message_id": message.id,
        "conversation_id": conversation_id,
        "processing_time": processing_time
    }

@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get messages from a conversation."""
    start_time = time.time()
    messages = message_repository.get_messages(db, conversation_id, skip, limit)
    processing_time = time.time() - start_time
    
    return {
        "conversation_id": conversation_id,
        "messages": [message.to_dict() for message in messages],
        "count": len(messages),
        "processing_time": processing_time
    }

@router.get("/conversations/{conversation_id}/context", response_model=ContextResponse)
async def get_conversation_context(
    conversation_id: str,
    query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get context for a conversation, optionally filtered by query."""
    start_time = time.time()
    context = context_service.get_context(db, conversation_id, query)
    processing_time = time.time() - start_time
    
    return {
        "context": context,
        "context_size": len(context),
        "processing_time": processing_time
    }

@router.get("/conversations/{conversation_id}/summary", response_model=SummaryResponse)
async def get_conversation_summary(
    conversation_id: str,
    query: Optional[str] = None,
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """Get a summary for a conversation, optionally focused on a query."""
    start_time = time.time()
    summary = summarizer_service.get_or_create_summary(
        db, 
        conversation_id,
        query,
        use_cache=True,
        force_refresh=force_refresh
    )
    processing_time = time.time() - start_time
    
    return {
        "summary": summary,
        "processing_time": processing_time
    }

@router.post("/draft_response")
async def draft_response(request: Request):
    """Legacy endpoint for drafting responses directly."""
    data = await request.json()
    text = data.get("text", "")
    as_user = data.get("as_user", None)

    if not text:
        return {"error": "No text provided."}

    start_time = time.time()
    draft = response_drafter_service.draft_response(text, as_user)
    processing_time = time.time() - start_time
    
    return {
        "draft": draft,
        "processing_time": processing_time
    }
@router.post("/conversations/{conversation_id}/keyinfo")
async def get_key_info(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    context = context_service.get_context(db, conversation_id, query=None)
    if not context:
        raise HTTPException(404, "Conversation not found")
    raw = extractor.extract_key_info(context)
    if not raw:
        return {"key_info": "", "ics_file": ""}
    refined = extractor.refine_key_info(context, raw)
    ics = extractor.generate_ics(refined)

    return {"key_info": refined, "ics_file": ics}