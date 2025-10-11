# python .\test_ws.py --token "<YOUR_TOKEN_ID>" --wav sample.wav

import argparse
import asyncio
import base64
import json
import math
import os
import time
from datetime import datetime
from urllib.parse import urlencode

import numpy as np
import soundfile as sf
import websockets


def chunk_audio(path, chunk_seconds=5.0):
    """Yield (seq, offset_ms, duration_sec, bytes_wav) for each 5s chunk."""
    data, sr = sf.read(path, dtype="int16")  # shape (N,) mono
    if data.ndim > 1:
        data = data[:, 0]  # use first channel if stereo

    samples_per_chunk = int(chunk_seconds * sr)
    total_samples = len(data)
    seq = 0

    for start in range(0, total_samples, samples_per_chunk):
        end = min(start + samples_per_chunk, total_samples)
        chunk = data[start:end]

        # write small wav to memory (PCM 16)
        import io
        buf = io.BytesIO()
        sf.write(buf, chunk, sr, format="WAV", subtype="PCM_16")
        wav_bytes = buf.getvalue()

        offset_ms = int(1000 * start / sr)
        duration_sec = (end - start) / sr
        yield seq, offset_ms, duration_sec, wav_bytes
        seq += 1


async def run(url, token, wav_path, language="pl"):
    # 1) Connect WS with token as query param
    qs = urlencode({"token": token})
    ws_url = f"{url}?{qs}"
    print(f"Connecting to {ws_url}")
    async with websockets.connect(ws_url, ping_interval=20, max_size=32 * 1024 * 1024) as ws:

        # 2) Send init_session
        title = f"Test_{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}"
        init_msg = {
            "type": "init_session",
            "title": title,
            "sampleRate": 16000,
            "language": language,
            "source": "web"
        }
        await ws.send(json.dumps(init_msg))
        started = json.loads(await ws.recv())
        assert started["type"] == "session_started", started
        session_id = started["sessionId"]
        print("Session started:", session_id)

        # 3) Stream audio in 5s chunks
        for seq, offset_ms, duration_sec, wav_bytes in chunk_audio(wav_path, chunk_seconds=5.0):
            msg = {
                "type": "audio_chunk",
                "sessionId": session_id,
                "seq": seq,
                "offsetMs": offset_ms,
                "durationSec": duration_sec,
                "mime": "audio/wav",
                "audioB64": base64.b64encode(wav_bytes).decode("utf-8"),
            }
            await ws.send(json.dumps(msg))

            # read server response (chunk_transcribed)
            resp = json.loads(await ws.recv())
            if resp.get("type") == "chunk_transcribed":
                print(f"[{resp['seq']:03d}] {resp['transcript']['text']}")
            elif resp.get("type") == "error":
                raise RuntimeError(resp)

        # 4) Stop & wait for final transcript
        await ws.send(json.dumps({"type": "stop", "sessionId": session_id}))

        # expect processing_started then transcript_ready
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("type") == "processing_started":
                print("Processing offline…")
            elif resp.get("type") == "transcript_ready":
                print("\n=== FULL TRANSCRIPT ===\n")
                print(resp.get("text", ""))
                break
            elif resp.get("type") == "error":
                raise RuntimeError(resp)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8000/ws/transcribe", help="WebSocket URL")
    ap.add_argument("--token", required=True, help="Firebase ID token (from web login)")
    ap.add_argument("--wav", default="sample.wav", help="Path to mono 16kHz WAV file")
    ap.add_argument("--lang", default="pl", help="Language hint for Whisper")
    args = ap.parse_args()
    asyncio.run(run(args.url, args.token, args.wav, language=args.lang))
