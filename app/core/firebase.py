from pathlib import Path
from typing import Dict, Any

import firebase_admin
from firebase_admin import credentials, auth, db

from app.core.config import settings

# Initialize Firebase Admin at import time (single app instance)
if not firebase_admin._apps:
    cred_path = Path(settings.FIREBASE_CREDENTIALS_FILE)
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {
        "databaseURL": settings.FIREBASE_DATABASE_URL
    })


def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """
    Verify Firebase ID token and return decoded claims.
    Raises if token invalid/expired.
    """
    decoded = auth.verify_id_token(id_token)
    return decoded


def db_ref(path: str):
    """Return a database reference for a given absolute path."""
    if not path.startswith("/"):
        path = f"/{path}"
    return db.reference(path)
