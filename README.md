# AGH-MA-BACKEND

## Whisper Realtime WS API (FastAPI)

Simple, production-minded layout for a realtime transcription backend:
- WebSocket endpoint (`/ws/transcribe`) with Firebase ID token auth
- 5s audio chunks over JSON (base64)
- Near-realtime chunk transcription + offline full transcript
- Firebase Realtime Database for metadata, segments, and final transcript

### Quick start

```bash
python -m venv .venv
```
```bash
source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```
```bash
cp .env.example .env
```
```bash
uvicorn app.main:app --reload
```

### Endpoints

#### WebSocket
**`ws://<host>/ws/transcribe?token=<FIREBASE_ID_TOKEN>`**

Main realtime transcription channel.  
All client messages and server responses are JSON text frames.

##### Client → Server message types
- **init_session**  
  Initializes a new recording session.  
  ```json
  {
    "type": "init_session",
    "title": "My Session",
    "sampleRate": 16000,
    "language": "pl",
    "source": "web"
  }
  ```
- **audio_chunk**  
  Sends a ~5s audio fragment (base64-encoded WAV or OGG).
  ```json
  {
    "type": "audio_chunk",
    "sessionId": "sess_1234",
    "seq": 0,
    "offsetMs": 0,
    "durationSec": 5.0,
    "mime": "audio/wav",
    "audioB64": "<BASE64_DATA>"
  }
  ```
- **stop**  
  Finalizes the session and triggers offline full transcription.
  ```json
  { "type": "stop", "sessionId": "sess_1234" }
  ```
- **list_sessions**  
  Requests the list of previous sessions for the current user.
  ```json
  { "type": "list_sessions", "cursor": null, "limit": 20 }
  ```
- **get_transcript**  
  Requests the stored full transcript for a given session.
  ```json
  { "type": "get_transcript", "sessionId": "sess_1234" }
  ```
  
##### Server → Client message types
- **session_started**  
  Returned after init_session.
  ```json
  {
    "type": "session_started",
    "sessionId": "sess_1234",
    "status": "recording",
    "createdAt": "2025-01-01T10:00:00Z"
  }
  ```
- **chunk_transcribed**  
  Partial transcript for a single chunk.
  ```json
  {
    "type": "chunk_transcribed",
    "sessionId": "sess_1234",
    "seq": 0,
    "offsetMs": 0,
    "durationSec": 5.0,
    "transcript": { "text": "Hello world", "words": [] }
  } 
  ```
- **processing_started**  
  Returned after stop when offline transcription begins.
  ```json
  { "type": "processing_started", "sessionId": "sess_1234", "status": "processing" }
  ```
- **transcript_ready**  
  Final, full text from offline processing.
  ```json
  {
    "type": "transcript_ready",
    "sessionId": "sess_1234",
    "status": "done",
    "text": "Full transcript..."
  }
  ```
- **sessions_list**  
  Returned as response to list_sessions.
  ```json
  {
    "type": "sessions_list",
    "items": [
      {
        "sessionId": "sess_1234",
        "title": "My Session",
        "status": "done",
        "createdAt": "2025-01-01T10:00:00Z",
        "totalDurationSec": 180
      }
    ],
    "nextCursor": null
  }
  ```
- **error**  
  Generic error message.
  ```json
  {
    "type": "error",
    "code": "bad_request",
    "message": "Invalid payload"
  }
  ```
  
#### HTTP
- **GET** _/health_  
  Simple readiness probe.
  ```json
  { "ok": true }
  ```