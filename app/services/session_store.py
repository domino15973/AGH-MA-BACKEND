import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Dict, Optional

from app.core.config import settings


@dataclass
class AudioChunkMeta:
    seq: int
    offset_ms: int
    duration_sec: float
    file_path: str


@dataclass
class SessionData:
    session_id: str
    uid: str
    title: str
    sample_rate: int
    language: str
    source: str
    created_at: str
    chunks: Dict[int, AudioChunkMeta] = field(default_factory=dict)

    @property
    def session_dir(self) -> Path:
        return Path(settings.TEMP_DIR) / self.session_id


class SessionStore:
    """
    Thread-safe in-memory session registry and local chunk storage.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._lock = RLock()

    def create_session(self, session: SessionData):
        with self._lock:
            self._sessions[session.session_id] = session
            session.session_dir.mkdir(parents=True, exist_ok=True)

    def get(self, session_id: str) -> SessionData:
        with self._lock:
            if session_id not in self._sessions:
                raise ValueError("Session not found")
            return self._sessions[session_id]

    def get_owned(self, session_id: str, uid: str) -> SessionData:
        s = self.get(session_id)
        if s.uid != uid:
            raise PermissionError("Forbidden")
        return s

    def save_chunk_bytes(self, session_id: str, seq: int, mime: str, data: bytes) -> str:
        s = self.get(session_id)
        ext = self._mime_to_ext(mime)
        path = s.session_dir / f"{seq:06d}{ext}"
        with open(path, "wb") as f:
            f.write(data)
        return str(path)

    def add_chunk_meta(self, session_id: str, meta: AudioChunkMeta):
        with self._lock:
            s = self.get(session_id)
            s.chunks[meta.seq] = meta

    def concat_session_audio(self, session_id: str) -> str:
        """
        Concatenate chunk files (ordered by seq) into a single WAV file.
        Uses pydub; requires ffmpeg installed in the environment.
        """
        from pydub import AudioSegment  # local import to avoid global dependency issues

        s = self.get(session_id)
        ordered = [s.chunks[k] for k in sorted(s.chunks.keys())]
        if not ordered:
            raise ValueError("No chunks to concatenate")

        combined: Optional[AudioSegment] = None
        for meta in ordered:
            seg = AudioSegment.from_file(meta.file_path)
            combined = seg if combined is None else (combined + seg)

        out_path = s.session_dir / "full.wav"
        combined = combined.set_channels(1)
        combined = combined.set_frame_rate(s.sample_rate)
        combined.export(out_path, format="wav")
        return str(out_path)

    @staticmethod
    def _mime_to_ext(mime: str) -> str:
        if mime == "audio/wav":
            return ".wav"
        if mime == "audio/ogg":
            return ".ogg"
        if mime == "audio/m4a" or mime == "audio/mp4":
            return ".m4a"
        # default to wav if unknown
        return ".wav"
