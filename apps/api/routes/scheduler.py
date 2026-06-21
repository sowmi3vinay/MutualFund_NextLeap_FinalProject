from fastapi import APIRouter
from pydantic import BaseModel

from services.voice_scheduler import handle_voice_turn, scheduler_greeting

router = APIRouter()


class VoiceTurnRequest(BaseModel):
    transcript: str


@router.post("/voice-turn")
def voice_turn(request: VoiceTurnRequest):
    return handle_voice_turn(request.transcript)


@router.get("/greeting")
def greeting():
    return {"greeting": scheduler_greeting()}
