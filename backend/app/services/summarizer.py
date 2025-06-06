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
from app.repositories.message_repository import message_repository
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
        cache_key = f"conversation:{conversation_id}:summary"
        if query:
            cache_key += f":{query}"

        if use_cache and not force_refresh:
            cached_summary = cache.get(cache_key)
            if cached_summary:
                logger.info(f"Using cached summary for conversation {conversation_id}")
                return cached_summary

        if not query and not force_refresh:
            existing_summary = (
                db.query(Summary)
                .filter(Summary.conversation_id == conversation_id)
                .order_by(Summary.timestamp.desc())
                .first()
            )
            if existing_summary:
                logger.info(f"Using existing summary for conversation {conversation_id}")
                if use_cache:
                    cache.set(cache_key, existing_summary.content, ttl=self.cache_ttl)
                return existing_summary.content

        # 💡 Add: auto semantic query based on recent messages
        if not query:
            recent_messages = message_repository.get_messages(db, conversation_id, skip=0, limit=3)
            query = " ".join([msg.content for msg in recent_messages]).strip()
            logger.info(f"Auto-generated semantic query for RAG: '{query}'")

        context = context_service.get_context(db, conversation_id, query)
        if not context:
            logger.warning(f"No semantic context available for conversation {conversation_id}, falling back")
            context = context_service.get_context(db, conversation_id, query_text=None)
            if not context:
                logger.warning(f"No context available for conversation {conversation_id}")
                return "No conversation data available to summarize."

        summary_text = self.summarize_conversation(context, query)
        token_count = tokenizer.count_tokens(summary_text)

        if not query:
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