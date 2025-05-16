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
        """Generate a draft response based on the conversation context and user input."""
        if not user_input:
            return ""

        # Get speaker stats for context
        speakers = re.findall(r"^(.+?):", conversation_text, re.MULTILINE)
        speaker_counts = Counter(speakers)
        num_users = len(speaker_counts)
        top_users = ", ".join([f"{user} ({count} msgs)" for user, count in speaker_counts.most_common(5)])

        system_prompt = (
            f"You are an expert at paraphrasing messages while maintaining a specific user's writing style.\n"
            f"There are {num_users} participants in the conversation, mainly {top_users}.\n"
        )

        if as_user:
            system_prompt += (
                f"Your task is to rephrase the user's input message AS IF IT WAS WRITTEN BY {as_user}.\n"
                f"Carefully analyze {as_user}'s writing style from the conversation history and mimic it exactly.\n"
                f"While maintaining {as_user}'s style, ensure you:\n"
                "1. Keep the same meaning and intent as the original message\n"
                "2. Use {as_user}'s typical phrases, emojis, and writing patterns\n"
                "3. Match {as_user}'s level of formality and tone\n"
                "4. Preserve any specific details or requests from the original message\n"
                "5. Not add any new information or responses\n"
                "\n"
                "The message to rephrase in {as_user}'s style is:\n"
                f"{user_input}"
            )
        else:
            system_prompt += (
                "Your task is to rephrase the user's input message in a natural, conversational tone.\n"
                "While maintaining the original meaning, ensure you:\n"
                "1. Keep the same meaning and intent\n"
                "2. Make it sound natural and conversational\n"
                "3. Preserve any specific details or requests\n"
                "4. Not add any new information or responses\n"
                "\n"
                "The message to rephrase is:\n"
                f"{user_input}"
            )

        try:
            start_time = time.time()
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text[:6000]}
                ],
                temperature=0.7
            )
            logger.info(f"OpenAI call took {time.time() - start_time:.2f}s")
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            logger.exception("OpenAI error drafting response")
            raise RuntimeError(f"Response drafting failed: {e}")


# Global response drafter instance
response_drafter_service = ResponseDrafterService() 