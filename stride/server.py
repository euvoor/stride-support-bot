import os
import secrets

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from stride.bot import answer

app = FastAPI(title="Stride support bot")
TOKEN = os.environ["STRIDE_API_TOKEN"]


class ChatRequest(BaseModel):
    question: str
    source: str = "customer"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat")
def chat(body: ChatRequest, authorization: str = Header("")):
    if not secrets.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(status_code=401, detail="Missing or wrong API token.")
    text, docs = answer(body.question, source=body.source)
    return {"answer": text, "sources": docs}
