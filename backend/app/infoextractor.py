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
        # More comprehensive event keywords
        academic_events = r"\b(Lecture|class|exam|test|quiz|assignment|project|presentation|demo|review|discussion|tutorial|lab|office hours)\b"
        professional_events = r"\b(meeting|consultation|check-in|catch-up|sync|standup|planning|retrospective|review|debrief|briefing|orientation|training|onboarding)\b"
        social_events = r"\b(workshop|hackathon|meetup|gathering|party|celebration|ceremony|graduation|commencement|convocation|induction|inauguration|launch|opening|closing|finale|showcase|exhibition|fair|festival)\b"
        general_events = r"\b(Reminder|starts|TODAY|TIME CHANGE|event|appointment|deadline|due|schedule|session|call|interview)\b"
        event_keywords = f"({academic_events}|{professional_events}|{social_events}|{general_events})"
        
        # More flexible date patterns
        date_patterns = [
            r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b",  # YYYY-MM-DD or YYYY/MM/DD
            r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",  # DD-MM-YYYY or DD/MM/YYYY
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",  # Month DD, YYYY
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b",  # DD Month YYYY
            r"\b(tomorrow|today|next week|next month)\b"  # Relative dates
        ]
        
        # More flexible time patterns
        time_patterns = [
            r"\b(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm|A\.M\.|P\.M\.|a\.m\.|p\.m\.))\b",  # 12-hour format
            r"\b(\d{1,2}:\d{2})\b",  # 24-hour format
            r"\b(\d{1,2}(?::\d{2})?\s*(?:o'clock|oclock|o' clock|o clock))\b",  # o'clock format
            r"\b(\d{1,2}(?::\d{2})?)\b"  # Just numbers
        ]

        for block in text.split("\n\n"):
            line = block.strip()
            if not line:
                continue
                
            # Check for event keywords
            if not re.search(event_keywords, line, re.IGNORECASE):
                continue
                
            # Clean the text but preserve more information
            clean = re.sub(r"\*\*|\[.*?\]\(.*?\)", "", line)
            clean = re.sub(r"http\S+", "", clean).strip()
            
            # Try to find a date
            dt = None
            for pattern in date_patterns:
                m_date = re.search(pattern, clean, re.IGNORECASE)
                if m_date:
                    try:
                        dt = parse_date(m_date.group(1), settings={"PREFER_DATES_FROM": "future"})
                        if dt:
                            break
                    except:
                        continue
            
            # Try to find a time
            time_str = None
            for pattern in time_patterns:
                m_time = re.search(pattern, clean, re.IGNORECASE)
                if m_time:
                    time_str = m_time.group(1).upper().replace(" ", "")
                    break
            
            # If we found either a date or time, include the event
            if dt or time_str:
                date_str = dt.strftime('%Y-%m-%d') if dt else "TBD"
                time_str = time_str or "TBD"
                events.append(f"{clean} — {date_str} at {time_str}")

        return "\n".join(events) if events else ""

    def refine_key_info_with_gpt(self, conversation_text: str, key_info: str) -> str:
        if not key_info:
            return ""
        system_prompt = (
            "You are an expert at validating and formatting notification‐style events.\n"
            "Below are candidate events in the form \"Description - YYYY-MM-DD at HH:MMAM/PM\".\n"
            "Please:\n"
            "  1. Ensure each is correctly formatted.\n"
            "  2. Remove any leftover URLs or markdown.\n"
            "  3. Deduplicate if there are repeats.\n"
            "Output each event as a bullet point, e.g.:\n"
            "- Lecture 2 w/ Jason Weston - 2025-02-03 at 4:00PM\n"
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
                f"DTEND:{stamp}",
                "END:VEVENT"
            ]

        ics_lines.append("END:VCALENDAR")
        content = "\n".join(ics_lines)
        filename = f"events_{int(time.time())}.ics"
        with open(filename, "w") as f:
            f.write(content)
        return filename