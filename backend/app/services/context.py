"""
Context service for retrieving relevant context for a conversation.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.message import Message
from app.models.chunk import MessageChunk
from app.services.vector_store import vector_store
from app.services.cache import cache
from app.services.tokenizer import tokenizer

logger = logging.getLogger(__name__)

class ContextService:
    """Service for retrieving relevant context from a conversation."""
    
    def __init__(self, top_k=5, max_tokens=4000, cache_ttl=3600):
        """
        Initialize the context service.
        
        Args:
            top_k: Number of chunks to retrieve
            max_tokens: Maximum number of tokens in the context
            cache_ttl: TTL for cached context in seconds
        """
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.cache_ttl = cache_ttl
    
    def get_context(
        self, 
        db: Session, 
        conversation_id: str, 
        query_text: Optional[str] = None,
        use_cache: bool = True
    ) -> str:
        """
        Get conversation context based on a query.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            query_text: Query text to find relevant context, or None for recent
            use_cache: Whether to use cached context
            
        Returns:
            Context string containing relevant conversation chunks
        """
        start_time = time.time()
        
        # Try to get cached context if no specific query is provided
        cache_key = f"conversation:{conversation_id}:context"
        if use_cache and not query_text:
            cached_context = cache.get(cache_key)
            if cached_context:
                logger.info(f"Using cached context for conversation {conversation_id}")
                return cached_context
        
        try:
            # Get chunks for the conversation
            if query_text:
                # Semantic search for relevant chunks
                context = self._get_semantic_context(db, conversation_id, query_text)
            else:
                # Get recent chunks
                context = self._get_chronological_context(db, conversation_id)
                
            # Cache the context if no specific query was provided
            if use_cache and not query_text:
                cache.set(cache_key, context, ttl=self.cache_ttl)
                
            context_time = time.time() - start_time
            logger.info(f"Context retrieval took {context_time:.2f}s")
                
            return context
                
        except Exception as e:
            logger.exception(f"Error getting context: {str(e)}")
            # Fallback to full conversation
            return self._get_chronological_context(db, conversation_id)
    
    def _get_semantic_context(
        self, 
        db: Session, 
        conversation_id: str, 
        query_text: str
    ) -> str:
        """Get context based on semantic similarity to the query."""
        # Search for relevant chunks
        chunk_results = vector_store.search_by_text(
            query_text, 
            conversation_id, 
            self.top_k
        )
        
        if not chunk_results:
            logger.warning(f"No chunks found for query: {query_text}")
            return self._get_chronological_context(db, conversation_id)
            
        # Get chunks from database
        chunk_ids = [chunk_id for chunk_id, _ in chunk_results]
        chunks = db.query(MessageChunk).filter(
            MessageChunk.id.in_(chunk_ids),
            MessageChunk.conversation_id == conversation_id
        ).all()
        
        # Sort chunks by relevance score
        chunks_with_scores = []
        for chunk in chunks:
            score = next((score for cid, score in chunk_results if cid == chunk.id), 0)
            chunks_with_scores.append((chunk, score))
            
        chunks_with_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Build context, respecting token limit
        context_parts = []
        total_tokens = 0
        
        for chunk, score in chunks_with_scores:
            if total_tokens + chunk.token_count > self.max_tokens:
                break
                
            # Add chunk to context
            context_parts.append(f"[Relevance: {score:.2f}] {chunk.content}")
            total_tokens += chunk.token_count
            
        # Join parts with separators
        return "\n\n==========\n\n".join(context_parts)
    
    def _get_chronological_context(
        self, 
        db: Session, 
        conversation_id: str
    ) -> str:
        """Get context based on chronological order (most recent first)."""
        # Get most recent chunks
        chunks = db.query(MessageChunk).filter(
            MessageChunk.conversation_id == conversation_id
        ).order_by(MessageChunk.end_time.desc()).limit(self.top_k).all()
        
        if not chunks:
            logger.warning(f"No chunks found for conversation: {conversation_id}")
            return ""
            
        # Sort chunks chronologically
        chunks.sort(key=lambda x: x.start_time)
        
        # Build context, respecting token limit
        context_parts = []
        total_tokens = 0
        
        for chunk in chunks:
            if total_tokens + chunk.token_count > self.max_tokens:
                break
                
            # Add chunk to context
            context_parts.append(chunk.content)
            total_tokens += chunk.token_count
            
        # Join parts with separators
        return "\n\n==========\n\n".join(context_parts)

# Global context service instance
context_service = ContextService() 