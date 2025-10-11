import asyncio
import base64
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from app.core.firebase import verify_firebase_token
from app.models.messages import (
    ClientInitSession,
    ClientAudioChunk,
    ClientStop,
    ClientListSessions,
    ClientGetTranscript,
)
from app.services.session_store import SessionStore, SessionData, AudioChunkMeta
from app.services.realtime_db import RealtimeDB
from app.services.transcriber import Transcriber

router = APIRouter()

# Singletons for the process lifetime
session_store = SessionStore()
db = RealtimeDB()
transcriber = Transcriber(model_name=os.getenv("WHISPER_MODEL", "base"))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.websocket("/ws/transcribe")
async def ws_transcribe(
        websocket: WebSocket,
        token: str = Query(..., description="Firebase ID token"),
):
    # Authenticate via Firebase ID token
    try:
        auth = verify_firebase_token(token)
        uid = auth["uid"]
        email = auth.get("email")
    except Exception as e:
        # 4401 Unauthorized (custom close code for auth failure)
        await websocket.close(code=4401)
        return

    await websocket.accept()

    try:
        while True:
            # Receive a text message (JSON)
            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type")

            if msg_type == "init_session":
                msg = ClientInitSession(**data)
                session_id = f"sess_{uuid.uuid4().hex[:8]}"
                created_at = utc_now_iso()

                session_data = SessionData(
                    session_id=session_id,
                    uid=uid,
                    title=msg.title,
                    sample_rate=msg.sampleRate,
                    language=msg.language,
                    source=msg.source,
                    created_at=created_at,
                )
                session_store.create_session(session_data)

                # Persist metadata to Realtime DB
                db.create_session(
                    uid=uid,
                    session_id=session_id,
                    payload={
                        "title": msg.title,
                        "sampleRate": msg.sampleRate,
                        "language": msg.language,
                        "source": msg.source,
                        "status": "recording",
                        "createdAt": created_at,
                        "updatedAt": created_at,
                        "stats": {"chunksCount": 0, "totalDurationSec": 0},
                    },
                )

                await _send(websocket, {
                    "type": "session_started",
                    "sessionId": session_id,
                    "status": "recording",
                    "createdAt": created_at
                })

            elif msg_type == "audio_chunk":
                msg = ClientAudioChunk(**data)

                # Make sure session exists and belongs to uid
                session = session_store.get_owned(msg.sessionId, uid)

                # Decode audio (base64) and persist to temp file
                audio_bytes = base64.b64decode(msg.audioB64)
                chunk_path = session_store.save_chunk_bytes(
                    session_id=msg.sessionId,
                    seq=msg.seq,
                    mime=msg.mime,
                    data=audio_bytes,
                )

                # Transcribe the single chunk quickly
                # Note: word-level timestamps are not returned to keep it simple and fast.
                chunk_text = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: transcriber.transcribe_file(chunk_path, language=session.language),
                )

                # Update in-memory stats
                session_store.add_chunk_meta(
                    session_id=msg.sessionId,
                    meta=AudioChunkMeta(
                        seq=msg.seq,
                        offset_ms=msg.offsetMs or 0,
                        duration_sec=msg.durationSec or 0.0,
                        file_path=chunk_path,
                    ),
                )

                # Save segment to Realtime DB
                db.append_segment(
                    uid=uid,
                    session_id=msg.sessionId,
                    seq=msg.seq,
                    payload={
                        "offsetMs": msg.offsetMs or 0,
                        "durationSec": msg.durationSec or 0.0,
                        "text": chunk_text,
                        "words": [],  # simplified: word-level timestamps omitted
                    },
                )

                # Update stats in Realtime DB
                s = session_store.get(session.session_id)
                db.update_stats(
                    uid=uid,
                    session_id=session.session_id,
                    chunks_count=len(s.chunks),
                    total_duration_sec=sum(c.duration_sec for c in s.chunks.values()),
                )

                await _send(websocket, {
                    "type": "chunk_transcribed",
                    "sessionId": msg.sessionId,
                    "seq": msg.seq,
                    "offsetMs": msg.offsetMs or 0,
                    "durationSec": msg.durationSec or 0.0,
                    "transcript": {
                        "text": chunk_text,
                        "words": []
                    }
                })

            elif msg_type == "stop":
                msg = ClientStop(**data)
                session = session_store.get_owned(msg.sessionId, uid)

                # Mark processing start
                db.update_status(uid, session.session_id, "processing")
                await _send(websocket, {
                    "type": "processing_started",
                    "sessionId": session.session_id,
                    "status": "processing"
                })

                # Concatenate chunks and run full transcription (blocking)
                full_path = session_store.concat_session_audio(session.session_id)
                full_text = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: transcriber.transcribe_file(full_path, language=session.language),
                )

                # Persist transcript and final status
                db.save_full_transcript(uid, session.session_id, full_text)
                db.update_status(uid, session.session_id, "done")

                await _send(websocket, {
                    "type": "transcript_ready",
                    "sessionId": session.session_id,
                    "status": "done",
                    "text": full_text
                })

            elif msg_type == "list_sessions":
                msg = ClientListSessions(**data)
                items, next_cursor = db.list_sessions(uid=uid, cursor=msg.cursor, limit=msg.limit or 20)
                await _send(websocket, {
                    "type": "sessions_list",
                    "items": items,
                    "nextCursor": next_cursor
                })

            elif msg_type == "get_transcript":
                msg = ClientGetTranscript(**data)
                text = db.get_full_transcript(uid=uid, session_id=msg.sessionId)
                await _send(websocket, {
                    "type": "transcript_ready",
                    "sessionId": msg.sessionId,
                    "status": "done" if text is not None else "not_found",
                    "text": text or ""
                })

            else:
                await _send(websocket, {
                    "type": "error",
                    "code": "bad_request",
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        # Client disconnected; nothing to do
        pass
    except Exception as e:
        if websocket.application_state == WebSocketState.CONNECTED:
            await _send(websocket, {
                "type": "error",
                "code": "internal_error",
                "message": str(e),
            })
        try:
            await websocket.close()
        except Exception:
            pass


async def _send(ws: WebSocket, payload: Dict[str, Any]):
    # Always send text JSON for compatibility
    await ws.send_text(json.dumps(payload))
