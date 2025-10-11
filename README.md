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
