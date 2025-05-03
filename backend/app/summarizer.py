import requests
import os
import re
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api-inference.huggingface.co/models/philschmid/bart-large-cnn-samsum"
HF_TOKEN = os.getenv("HF_TOKEN")

headers = {"Authorization": f"Bearer {HF_TOKEN}"}

def summarize_conversation(conversation_text: str) -> str:
    speakers = re.findall(r"^(.+?):", conversation_text, re.MULTILINE)
    speaker_counts = Counter(speakers)
    num_users = len(speaker_counts)
    top_users = ", ".join([f"{user} ({count} msgs)" for user, count in speaker_counts.most_common(5)])

    system_prompt = (
        f"You are a professional conversation summarizer.\n"
        f"There are {num_users} participants, mainly {top_users}.\n"
        f"Summarize the conversation:\n"
        f"- Mention key points made.\n"
        f"- Highlight important statements.\n"
        f"Be detailed and faithful to the tone.\n\n"
    )

    payload = system_prompt + conversation_text

    response = requests.post(API_URL, headers=headers, json={"inputs": payload})

    if response.status_code == 200:
        summary = response.json()
        return summary[0]['summary_text'] if isinstance(summary, list) else summary
    else:
        return "Summarization failed. API error."
    

def extract_key_info(conversation_text: str) -> str:
    # Prompt for key information extraction
    extraction_prompt = (
        "You are a specialized information extractor focused on notifications.\n"
        "From the following conversation, identify all notice-type items (e.g., meeting times, dates, deadlines, venue announcements, appointments) "
        "and any subsequent updates or changes. Make sure each important message is separated by a new line.\n"
        "Provide each as a bullet point with the final agreed details.\n\n"
        "Conversation:\n"
    )
    payload = extraction_prompt + conversation_text

    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": payload}
    )

    if response.status_code == 200:
        result = response.json()
        return result[0]['summary_text'] if isinstance(result, list) else result
    else:
        return "Key info extraction failed. API error."
