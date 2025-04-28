from fastapi import APIRouter, Request
from app.summarizer import summarize_conversation

router = APIRouter()

@router.post("/summarize")
async def summarize(request: Request):
    data = await request.json()
    text = data.get("text", "")

    if not text:
        return {"error": "No text provided."}

    summary = summarize_conversation(text)
    return {"summary": summary}