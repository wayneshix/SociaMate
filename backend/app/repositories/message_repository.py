"""
Repository for message operations.
"""
import uuid
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.message import Message
from app.models.chunk import MessageChunk
from app.services.chunker import chunker
from app.services.embedding import embedding_service
from app.services.vector_store import vector_store
from app.services.cache import cache

logger = logging.getLogger(__name__)

class MessageRepository:
    """Repository for message operations."""
    
    def __init__(self):
        """Initialize the repository."""
        pass
        
    def get_message(self, db: Session, message_id: int) -> Optional[Message]:
        """Get a message by ID."""
        return db.query(Message).filter(Message.id == message_id).first()
        
    def get_messages(
        self, 
        db: Session, 
        conversation_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get messages for a conversation."""
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
            .offset(skip)
            .limit(limit)
            .all()
        )
        
    def create_message(
        self, 
        db: Session, 
        conversation_id: str,
        author: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Create a new message."""
        timestamp = timestamp or datetime.utcnow()
        
        message = Message(
            conversation_id=conversation_id,
            author=author,
            content=content,
            timestamp=timestamp,
            meta_data=metadata
        )
        
        start_time = time.time()
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        # Invalidate conversation cache
        cache.invalidate_conversation(conversation_id)
        
        logger.info(f"Created message in {time.time() - start_time:.4f}s")
        
        return message
        
    def create_messages(
        self, 
        db: Session, 
        conversation_id: str,
        messages_data: List[Dict[str, Any]]
    ) -> List[Message]:
        """
        Create multiple messages at once.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            messages_data: List of message data dictionaries, each containing:
                - author: Author of the message
                - content: Message content
                - timestamp: Optional timestamp (defaults to now)
                - metadata: Optional metadata dictionary
                
        Returns:
            List of created Message objects
        """
        start_time = time.time()
        
        messages = []
        for message_data in messages_data:
            timestamp = message_data.get("timestamp") or datetime.utcnow()
            
            message = Message(
                conversation_id=conversation_id,
                author=message_data["author"],
                content=message_data["content"],
                timestamp=timestamp,
                meta_data=message_data.get("metadata")
            )
            
            messages.append(message)
            
        # Bulk insert
        db.add_all(messages)
        db.commit()
        
        for message in messages:
            db.refresh(message)
            
        # Process chunks and invalidate cache
        self._process_conversation_chunks(db, conversation_id)
        cache.invalidate_conversation(conversation_id)
        
        logger.info(f"Created {len(messages)} messages in {time.time() - start_time:.4f}s")
        
        return messages
        
    def _process_conversation_chunks(self, db: Session, conversation_id: str):
        """
        Process conversation messages into chunks and update embeddings.
        
        This is called after adding messages to a conversation.
        """
        # Get all messages for the conversation
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
            .all()
        )
        
        if not messages:
            logger.warning(f"No messages found for conversation {conversation_id}")
            return
            
        # Delete existing chunks for the conversation
        db.query(MessageChunk).filter(
            MessageChunk.conversation_id == conversation_id
        ).delete()
        
        # Create new chunks
        chunks = chunker.chunk_conversation(messages, conversation_id)
        
        if not chunks:
            logger.warning(f"No chunks created for conversation {conversation_id}")
            return
            
        # Add chunks to database
        for chunk in chunks:
            db.add(chunk)
            
        db.commit()
        
        # Generate embeddings for chunks
        for chunk in chunks:
            db.refresh(chunk)
            embedding = embedding_service.generate_embedding(chunk.content)
            
            if embedding:
                # Add to vector store
                embedding_id = vector_store.add_embedding(
                    embedding, 
                    conversation_id, 
                    chunk.id
                )
                
                # Update chunk with embedding ID
                chunk.embedding_id = embedding_id
                db.add(chunk)
                
        db.commit()
        
        logger.info(f"Processed {len(chunks)} chunks for conversation {conversation_id}")

# Global repository instance
message_repository = MessageRepository() 