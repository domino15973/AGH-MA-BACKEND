from typing import Any, Dict, List, Tuple

from app.core.firebase import db_ref


class RealtimeDB:
    """
    Small helper wrapper around Firebase Realtime Database.
    """

    def create_session(self, uid: str, session_id: str, payload: Dict[str, Any]):
        ref = db_ref(f"users/{uid}/sessions/{session_id}")
        ref.set(payload)

    def update_status(self, uid: str, session_id: str, status: str):
        ref = db_ref(f"users/{uid}/sessions/{session_id}/status")
        ref.set(status)
        # also bump updatedAt to help clients
        db_ref(f"users/{uid}/sessions/{session_id}/updatedAt").set(self._now())

    def update_stats(self, uid: str, session_id: str, chunks_count: int, total_duration_sec: float):
        ref = db_ref(f"users/{uid}/sessions/{session_id}/stats")
        ref.update({
            "chunksCount": chunks_count,
            "totalDurationSec": total_duration_sec
        })
        db_ref(f"users/{uid}/sessions/{session_id}/updatedAt").set(self._now())

    def append_segment(self, uid: str, session_id: str, seq: int, payload: Dict[str, Any]):
        ref = db_ref(f"users/{uid}/sessions/{session_id}/segments/{seq}")
        ref.set(payload)
        db_ref(f"users/{uid}/sessions/{session_id}/updatedAt").set(self._now())

    def save_full_transcript(self, uid: str, session_id: str, text: str):
        ref = db_ref(f"users/{uid}/sessions/{session_id}/transcript")
        ref.set({"text": text})
        db_ref(f"users/{uid}/sessions/{session_id}/updatedAt").set(self._now())

    def get_full_transcript(self, uid: str, session_id: str) -> str | None:
        ref = db_ref(f"users/{uid}/sessions/{session_id}/transcript")
        val = ref.get()
        if isinstance(val, dict):
            return val.get("text")
        return None

    def list_sessions(self, uid: str, cursor: str | None, limit: int) -> Tuple[List[Dict[str, Any]], str | None]:
        # Minimal list using RTDB; no strong ordering guarantees without indexes.
        # Clients should rely on createdAt/updatedAt to sort locally.
        base = db_ref(f"users/{uid}/sessions").get() or {}
        items = []
        for sid, data in base.items():
            items.append({
                "sessionId": sid,
                "title": data.get("title"),
                "status": data.get("status"),
                "createdAt": data.get("createdAt"),
                "totalDurationSec": (data.get("stats") or {}).get("totalDurationSec", 0),
            })
        # No real pagination for simplicity
        items = sorted(items, key=lambda x: x.get("createdAt") or "", reverse=True)[:limit]
        return items, None

    @staticmethod
    def _now():
        import datetime, pytz
        return datetime.datetime.now(tz=pytz.UTC).isoformat()
