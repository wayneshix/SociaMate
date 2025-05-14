# app/infoextractor.py
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

    def extract_key_info(self, text: str) -> str:
        key_info = []
        for kind in ("meeting","call","appointment","class"):
            for d,t in re.findall(
                rf"{kind} on (\d{{4}}-\d{{2}}-\d{{2}}) at (\d{{1,2}}:\d{{2}})",
                text, flags=re.IGNORECASE):
                key_info.append(f"{kind.capitalize()} on {d} at {t}")
        for date_str, time_str, ampm in re.findall(
            r"([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?(?:, \d{4})?)\s+at\s+(\d{1,2}:\d{2})\s*(AM|PM)",
            text):
            dt = dateparser.parse(f"{date_str} {time_str}{ampm}")
            if dt:
                key_info.append(f"Event on {dt.strftime('%Y-%m-%d')} at {dt.strftime('%H:%M')}")
        for start, end, ampm in re.findall(
            r"(\d{1,2}:\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}:\d{2})\s*(AM|PM)\s*(?:PST|EST|CET)?",
            text):
            s = dateparser.parse(f"{start}{ampm}")
            e = dateparser.parse(f"{end}{ampm}")
            if s and e:
                key_info.append(f"Time slot {s.strftime('%H:%M')}–{e.strftime('%H:%M')}")
        for start, end in re.findall(
            r"starting\s+([A-Za-z0-9 ,thndsr]+?)\s+through\s+([A-Za-z0-9 ,thndsr]+?)(?:\.|\s|$)",
            text, flags=re.IGNORECASE):
            sd = dateparser.parse(start)
            ed = dateparser.parse(end)
            if sd and ed:
                key_info.append(f"From {sd.strftime('%Y-%m-%d')} through {ed.strftime('%Y-%m-%d')}")
        for sentence in re.findall(
            r"([^.]*\b(class|livestream|starts)\b[^.]*\.)", text, flags=re.IGNORECASE):
            key_info.append(sentence[0].strip())

        return "\n".join(key_info) if key_info else ""

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
