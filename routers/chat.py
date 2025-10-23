# routers/chat.py  
import os, httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

GROQ_API_KEY ="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"
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in environment")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatIn(BaseModel):
    prompt: str                    # full prompt from the frontend
    system: str | None = None      # optional system prompt (also from frontend)


@router.post("") 
async def chat(inp: ChatIn):
    messages = []

# Use explicit system message if provided; otherwise set a minimal hard rule
    system_text = inp.system or "Return ONLY a valid, minified JSON object. No prose."
    messages.append({"role": "system", "content": system_text})

# User content is the actual inputs + JSON directive
    messages.append({"role": "user", "content": inp.prompt})

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 750,
        "stream": False
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(GROQ_URL, headers=headers, json=payload)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return JSONResponse({"reply": text})  