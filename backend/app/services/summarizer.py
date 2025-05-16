"""
Summarizer service for generating conversation summaries using OpenAI GPT-3.5.
"""
import os
import re
import time
import logging
from collections import Counter
from dotenv import load_dotenv
from typing import Optional
from openai import OpenAIError, OpenAI
from sqlalchemy.orm import Session
from app.models.summary import Summary
from app.models.chunk import MessageChunk
from app.services.context import context_service
from app.services.tokenizer import tokenizer
from app.services.cache import cache

load_dotenv()

logger = logging.getLogger(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

class SummarizerService:
    """Service for generating conversation summaries."""

    def __init__(self, cache_ttl=3600):
        self.cache_ttl = cache_ttl


    def summarize_conversation(
        self,
        conversation_text: str,
        query: Optional[str] = None
    ) -> str:
        start_time = time.time()

        # Speaker stats
        speakers = re.findall(r"^(.+?):", conversation_text, re.MULTILINE)
        speaker_counts = Counter(speakers)
        num_users = len(speaker_counts)
        top_users = ", ".join([f"{user} ({count} msgs)" for user, count in speaker_counts.most_common(5)])

        # System prompt
        system_prompt = (
            f"You are a professional conversation summarizer.\n"
            f"There are {num_users} participants, mainly {top_users}.\n"
        )
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

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation_text[:6000]}
            ]

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"OpenAI call took {time.time() - start_time:.2f}s")
            return summary

        except OpenAIError as e:
            logger.exception("OpenAI API error")
            raise RuntimeError(f"Summarization failed due to OpenAI error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during summarization")
            raise RuntimeError(f"Summarization failed due to exception: {str(e)}")

    def get_or_create_summary(
        self,
        db: Session,
        conversation_id: str,
        query: Optional[str] = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> str:
        start_time = time.time()

        # Auto-generate a "query" from recent messages if not explicitly provided
        if not query:
            recent_messages = message_repository.get_messages(db, conversation_id, skip=0, limit=3)
            joined_recent = "\n".join([f"{m.author}: {m.content}" for m in recent_messages])
            query = joined_recent[-300:]  # use last ~300 chars of message context as implicit query

        cache_key = f"conversation:{conversation_id}:summary:{query}"

        # Use cached summary if available and not forcing refresh
        if use_cache and not force_refresh:
            cached_summary = cache.get(cache_key)
            if cached_summary:
                logger.info(f"Using cached summary for conversation {conversation_id} (query-based)")
                return cached_summary

        # Try to get context using RAG with query
        context = context_service.get_context(db, conversation_id, query_text=query)
        if not context:
            logger.warning(f"No semantic context available for conversation {conversation_id}, falling back")
            context = context_service.get_context(db, conversation_id)

        if not context:
            logger.warning(f"No context available for conversation {conversation_id}")
            return "No conversation data available to summarize."

        # Generate summary using OpenAI
        summary_text = self.summarize_conversation(context, query)
        token_count = tokenizer.count_tokens(summary_text)

        # Persist to database only for full (non-query-based) summaries
        if not force_refresh and not query:
            chunks = (
                db.query(MessageChunk)
                .filter(MessageChunk.conversation_id == conversation_id)
                .order_by(MessageChunk.end_time.desc())
                .limit(context_service.top_k)
                .all()
            )
            chunk_ids = [chunk.id for chunk in chunks]
            new_summary = Summary(
                conversation_id=conversation_id,
                content=summary_text,
                chunk_ids=chunk_ids,
                is_full_summary=True,
                token_count=token_count
            )
            db.add(new_summary)
            db.commit()

        if use_cache:
            cache.set(cache_key, summary_text, ttl=self.cache_ttl)

        logger.info(f"Summary generation took {time.time() - start_time:.2f}s total")
        return summary_text


# Global summarizer instance
summarizer_service = SummarizerService()