from typing import Optional, Literal
from pydantic import BaseModel, Field


# Client → Server messages

class ClientInitSession(BaseModel):
    type: Literal["init_session"] = "init_session"
    title: str
    sampleRate: int
    language: str
    source: str  # "mobile" | "web"


class ClientAudioChunk(BaseModel):
    type: Literal["audio_chunk"] = "audio_chunk"
    sessionId: str
    seq: int
    offsetMs: Optional[int] = 0
    durationSec: Optional[float] = 0.0
    mime: str  # "audio/wav" | "audio/ogg" | "audio/m4a"
    audioB64: str


class ClientStop(BaseModel):
    type: Literal["stop"] = "stop"
    sessionId: str


class ClientListSessions(BaseModel):
    type: Literal["list_sessions"] = "list_sessions"
    cursor: Optional[str] = None
    limit: Optional[int] = 20


class ClientGetTranscript(BaseModel):
    type: Literal["get_transcript"] = "get_transcript"
    sessionId: str
