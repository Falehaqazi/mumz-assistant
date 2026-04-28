"""
FastAPI backend for Mumz Assistant.
POST /chat with {"message": "..."} returns the agent response.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

from app.agent import MumzAgent

app = FastAPI(title="Mumz Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = MumzAgent()


class ChatRequest(BaseModel):
    message: str
    k: int = 4


class ChatResponse(BaseModel):
    answer: str
    language: str
    citations: List[Dict[str, Any]]
    safety_flags: List[str]
    refused: bool


@app.get("/")
def root() -> Dict[str, str]:
    return {"service": "Mumz Assistant", "status": "ok"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "products_indexed": len(agent.retriever.products),
        "knowledge_indexed": len(agent.retriever.knowledge),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    r = agent.answer(req.message, k=req.k)
    return ChatResponse(
        answer=r.answer,
        language=r.language,
        citations=r.citations,
        safety_flags=r.safety_flags,
        refused=r.refused,
    )
