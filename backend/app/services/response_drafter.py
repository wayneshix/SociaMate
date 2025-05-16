"""
Response drafter service for generating draft responses to conversations using OpenAI.
"""
import os
import re
import time
import logging
from collections import Counter
from dotenv import load_dotenv
from typing import Optional
from openai import OpenAIError, OpenAI

load_dotenv()

logger = logging.getLogger(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

class ResponseDrafterService:
    """Service for generating draft responses to conversations."""

    def __init__(self, cache_ttl=3600):
        self.cache_ttl = cache_ttl

    def draft_response(
        self,
        conversation_text: str,
        as_user: Optional[str] = None,
        user_input: Optional[str] = None,
        prefer_something: bool = False
    ) -> str:
        start_time = time.time()

        # Speaker stats for context
        speakers = re.findall(r"^(.+?):", conversation_text, re.MULTILINE)
        speaker_counts = Counter(speakers)
        num_users = len(speaker_counts)
        top_users = ", ".join([f"{user} ({count} msgs)" for user, count in speaker_counts.most_common(5)])

        # System prompt
        system_prompt = (
            f"You are a professional assistant that drafts helpful responses.\n"
            f"There are {num_users} participants, mainly {top_users}.\n"
        )
        
        if as_user:
            system_prompt += (
                f"The user wants you to draft a response AS IF YOU WERE {as_user}.\n"
                f"Mimic {as_user}'s writing style and write concisely while creating a response.\n"
                f"Make sure your response sounds natural and consistent with how {as_user} would respond in the chat history.\n"
                f"Please try your best to not sound like AI and response should normally be very short, and do not directly mention users name and sound casual like how you would normally talk in a discord server\n"
            )
        else:
            system_prompt += (
                f"The user needs you to draft a response to this conversation.\n"
            )

        if user_input:
            system_prompt += (
                f"\nThe user has suggested this input: '{user_input}'\n"
                f"Use this as a starting point or inspiration for your response, but feel free to modify it to better fit the conversation context.\n"
                f"Your response should be a natural continuation of the conversation, incorporating the user's suggestion if appropriate.\n"
            )

        if prefer_something:
            system_prompt += (
                f"\nThe user wants an alternative response. Please provide a different perspective or approach while maintaining the same tone and style.\n"
            )
        
        system_prompt += (
            f"Focus on the key points from the conversation and create a thoughtful, concise response that directly addresses the main topics discussed.\n"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation_text[:6000]}
            ]

            response = openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                temperature=0.3
            )

            draft = response.choices[0].message.content.strip()
            logger.info(f"OpenAI call took {time.time() - start_time:.2f}s")
            return draft

        except OpenAIError as e:
            logger.exception("OpenAI API error")
            raise RuntimeError(f"Response drafting failed due to OpenAI error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during response drafting")
            raise RuntimeError(f"Response drafting failed due to exception: {str(e)}")


# Global response drafter instance
response_drafter_service = ResponseDrafterService() 