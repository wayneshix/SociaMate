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