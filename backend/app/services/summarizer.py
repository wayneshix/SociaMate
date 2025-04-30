"""
Summarizer service for generating conversation summaries.
"""
import requests
import os
import re
import time
import logging
from collections import Counter
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.summary import Summary
from app.models.chunk import MessageChunk
from app.services.context import context_service
from app.services.tokenizer import tokenizer
from app.services.cache import cache

load_dotenv()

logger = logging.getLogger(__name__)

API_URL = "https://api-inference.huggingface.co/models/philschmid/bart-large-cnn-samsum"
HF_TOKEN = os.getenv("HF_TOKEN")

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

class SummarizerService:
    """Service for generating conversation summaries."""
    
    def __init__(self, cache_ttl=3600):
        """
        Initialize the summarizer service.
        
        Args:
            cache_ttl: TTL for cached summaries in seconds
        """
        self.cache_ttl = cache_ttl
        
    def summarize_conversation(
        self, 
        conversation_text: str,
        query: Optional[str] = None
    ) -> str:
        """
        Summarize a conversation.
        
        Args:
            conversation_text: The conversation text to summarize
            query: Optional query to focus the summary on
            
        Returns:
            Summary text
        """
        start_time = time.time()
        
        speakers = re.findall(r"^(.+?):", conversation_text, re.MULTILINE)
        speaker_counts = Counter(speakers)
        num_users = len(speaker_counts)
        top_users = ", ".join([f"{user} ({count} msgs)" for user, count in speaker_counts.most_common(5)])

        # Create a system prompt based on conversation statistics
        system_prompt = (
            f"You are a professional conversation summarizer.\n"
            f"There are {num_users} participants, mainly {top_users}.\n"
        )
        
        # Add query-specific instructions if a query is provided
        if query:
            system_prompt += (
                f"Focus your summary on content related to: '{query}'.\n"
                f"Summarize the conversation:\n"
                f"- Mention key points made related to the focus topic.\n"
                f"- Highlight important statements relevant to the query.\n"
                f"Be detailed and faithful to the tone.\n\n"
            )
        else:
            system_prompt += (
                f"Summarize the conversation:\n"
                f"- Mention key points made.\n"
                f"- Highlight important statements.\n"
                f"Be detailed and faithful to the tone.\n\n"
            )

        payload = system_prompt + conversation_text

        try:
            # Make the API call
            response = requests.post(API_URL, headers=headers, json={"inputs": payload})
            api_time = time.time() - start_time
            logger.info(f"API call took {api_time:.2f}s")

            if response.status_code == 200:
                summary = response.json()
                summary_text = summary[0]['summary_text'] if isinstance(summary, list) else summary
                return summary_text
            else:
                logger.error(f"API error: {response.text}")
                return "Summarization failed. API error."
        except Exception as e:
            logger.exception(f"Error summarizing conversation: {str(e)}")
            return "Summarization failed. An error occurred."
            
    def get_or_create_summary(
        self, 
        db: Session, 
        conversation_id: str,
        query: Optional[str] = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> str:
        """
        Get an existing summary or create a new one.
        
        Args:
            db: Database session
            conversation_id: ID of the conversation
            query: Optional query to focus the summary on
            use_cache: Whether to use cached summaries
            force_refresh: Whether to force a refresh of the summary
            
        Returns:
            Summary text
        """
        start_time = time.time()
        
        # Cache key for this summary
        cache_key = f"conversation:{conversation_id}:summary"
        if query:
            cache_key += f":{query}"
            
        # Try to get from cache first
        if use_cache and not force_refresh:
            cached_summary = cache.get(cache_key)
            if cached_summary:
                logger.info(f"Using cached summary for conversation {conversation_id}")
                return cached_summary
                
        # If no query is provided and not forcing refresh, check for existing summary in DB
        if not query and not force_refresh:
            existing_summary = (
                db.query(Summary)
                .filter(Summary.conversation_id == conversation_id)
                .order_by(Summary.timestamp.desc())
                .first()
            )
            
            if existing_summary:
                logger.info(f"Using existing summary for conversation {conversation_id}")
                
                # Cache the summary
                if use_cache:
                    cache.set(cache_key, existing_summary.content, ttl=self.cache_ttl)
                    
                return existing_summary.content
                
        # Get conversation context
        context = context_service.get_context(db, conversation_id, query)
        
        if not context:
            logger.warning(f"No context available for conversation {conversation_id}")
            return "No conversation data available to summarize."
            
        # Generate summary
        summary_text = self.summarize_conversation(context, query)
        token_count = tokenizer.count_tokens(summary_text)
        
        # Store summary in database if no query was provided
        if not query:
            # Get chunk IDs that were used
            chunks = (
                db.query(MessageChunk)
                .filter(MessageChunk.conversation_id == conversation_id)
                .order_by(MessageChunk.end_time.desc())
                .limit(context_service.top_k)
                .all()
            )
            
            chunk_ids = [chunk.id for chunk in chunks]
            
            # Create new summary
            new_summary = Summary(
                conversation_id=conversation_id,
                content=summary_text,
                chunk_ids=chunk_ids,
                is_full_summary=True,
                token_count=token_count
            )
            
            db.add(new_summary)
            db.commit()
            
        # Cache the summary
        if use_cache:
            cache.set(cache_key, summary_text, ttl=self.cache_ttl)
            
        total_time = time.time() - start_time
        logger.info(f"Summary generation took {total_time:.2f}s total")
            
        return summary_text

# Global summarizer instance
summarizer_service = SummarizerService() 