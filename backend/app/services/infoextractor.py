# app/services/infoextractor.py
import os
import re
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAIError, OpenAI

load_dotenv()

logger = logging.getLogger(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

class InfoExtractorService:
    """Service for extracting key notification information from conversations."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl

    def extract_key_info(self, conversation_text: str) -> str:
        key_info = []
        # Step 1: simple regex extraction for meetings, deadlines, appointments
        meeting_info = re.findall(
            r"(meeting|call|appointment|class) on (\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2})",
            conversation_text, flags=re.IGNORECASE
        )
        for match in meeting_info:
            key_info.append(f"Meeting scheduled on {match[1]} at {match[2]}")

        deadline_info = re.findall(
            r"deadline\s+by\s+(\d{4}-\d{2}-\d{2})",
            conversation_text, flags=re.IGNORECASE
        )
        for dl in deadline_info:
            key_info.append(f"Deadline by {dl}")

        # If no key info found, skip
        if not key_info:
            return ""
        return "\n".join(key_info)

    def refine_key_info_with_gpt(self, conversation_text: str, key_info: str) -> str:
        if not key_info:
            return ""
        system_prompt = (
            "You are an expert in extracting and validating notification-style information.\n"
            "Below is a list of candidate key items extracted via regex.\n"
            f"{key_info}\n\n"
            "Please verify, correct, and clarify each item. Output final bullet points."
        )
        try:
            response = openai_client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text[:6000]}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as e:
            logger.exception("OpenAI error refining key info")
            raise RuntimeError(f"Key info refinement failed: {e}")

    def generate_ics(self, key_info: str) -> str:
        """Generate and save an ICS file for the given key info."""
        ics = ["BEGIN:VCALENDAR", "VERSION:2.0"]
        for line in key_info.split("\n"):
            if "Meeting scheduled on" in line:
                m = re.search(r"on (\d+-\d+-\d+) at (\d+:\d+)", line)
                if m:
                    date, time = m.groups()
                    dt = date.replace("-", "") + "T" + time.replace(":", "") + "00"
                    ics += [
                        "BEGIN:VEVENT",
                        f"SUMMARY:{line}",
                        f"DTSTART:{dt}",
                        f"DTEND:{dt}",
                        "END:VEVENT"
                    ]
            if line.startswith("Deadline by"):
                d = line.split(" ")[-1]
                dt = d.replace("-", "") + "T000000"
                ics += [
                    "BEGIN:VEVENT",
                    f"SUMMARY:{line}",
                    f"DTSTART:{dt}",
                    f"DTEND:{dt}",
                    "END:VEVENT"
                ]
        ics.append("END:VCALENDAR")
        content = "\n".join(ics)
        filename = f"keyinfo_{int(time.time())}.ics"
        with open(filename, "w") as f:
            f.write(content)
        return filename
