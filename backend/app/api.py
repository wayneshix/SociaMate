from fastapi import APIRouter, Request
from app.summarizer import summarize_conversation
from app.summarizer import extract_key_info
router = APIRouter()

@router.post("/summarize")
async def summarize(request: Request):
    data = await request.json()
    text = data.get("text", "")

    if not text:
        return {"error": "No text provided."}

    summary = summarize_conversation(text)
    key_info = extract_key_info(text)
    return {
        "summary": summary,
        "key_info": key_info
        }
           