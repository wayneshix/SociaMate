# app/infoextractor.py
import os
import re
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAIError, OpenAI
from dateparser import parse as parse_date


load_dotenv()

logger = logging.getLogger(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key)

class InfoExtractorService:
    """Service for extracting key notification information from conversations."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl

    def extract_key_info(self, text: str) -> str:
        events = []

        # Split the text into blocks and only keep blocks that look like announcements
        for block in text.split("\n\n"):
            line = block.strip()
            if not line:
                continue

            # Only consider lines containing keywords
            if not re.search(r"\b(Lecture|class|Reminder|starts|TODAY|TIME CHANGE)\b", line, re.IGNORECASE):
                continue

            # Clean out markdown and URLs
            clean = re.sub(r"\*\*|\[.*?\]\(.*?\)", "", line)
            clean = re.sub(r"http\S+", "", clean).strip()

            # Parse a date in the line
            dt = parse_date(clean, settings={"PREFER_DATES_FROM": "future"})
            # Fallback: look for YYYY-MM-DD explicitly
            m_date = re.search(r"(\d{4}-\d{2}-\d{2})", clean)
            if m_date:
                dt = dt or parse_date(m_date.group(1))

            # Parse a time, e.g. “4:00PM” or “4 pm”
            m_time = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:AM|PM))", clean, re.IGNORECASE)
            if dt and m_time:
                timestr = m_time.group(1).upper().replace(" ", "")
                events.append(f"{clean} — {dt.strftime('%Y-%m-%d')} at {timestr}")

        return "\n".join(events)

    def refine_key_info_with_gpt(self, conversation_text: str, key_info: str) -> str:
        if not key_info:
            return ""
        system_prompt = (
            "You are an expert at validating and formatting notification‐style events.\n"
            "Below are candidate events in the form “Description — YYYY-MM-DD at HH:MMAM/PM”.\n"
            "Please:\n"
            "  1. Ensure each is correctly formatted.\n"
            "  2. Remove any leftover URLs or markdown.\n"
            "  3. Deduplicate if there are repeats.\n"
            "Output each event as a bullet point, e.g.:\n"
            "- Lecture 2 w/ Jason Weston — 2025-02-03 at 4:00PM\n"
            f"{key_info}"
        )
        try:
            response = openai_client.chat.completions.create(
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
        
    def generate_ics(self, refined: str) -> str:
        ics_lines = ["BEGIN:VCALENDAR", "VERSION:2.0"]
        for line in refined.splitlines():
            m = re.match(
                r"-\s*(.+)\s+—\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})(AM|PM)",
                line
            )
            if not m:
                continue
            desc, date, time_part, ampm = m.groups()
            dt = parse_date(f"{date} {time_part}{ampm}")
            stamp = dt.strftime("%Y%m%dT%H%M%S")
            ics_lines += [
                "BEGIN:VEVENT",
                f"SUMMARY:{desc}",
                f"DTSTART:{stamp}",
                f"DTEND:{stamp}",   # you can adjust to +1h or add duration rule
                "END:VEVENT"
            ]

        ics_lines.append("END:VCALENDAR")
        content = "\n".join(ics_lines)
        filename = f"events_{int(time.time())}.ics"
        with open(filename, "w") as f:
            f.write(content)
        return filename