import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    # Firebase
    FIREBASE_CREDENTIALS_FILE: str = Field(
        default="secrets/agh-ma-firebase-firebase-adminsdk-fbsvc-bc702fbf7a.json",
        description="Path to Firebase Admin SDK service account JSON",
    )
    FIREBASE_DATABASE_URL: str = Field(
        default="https://agh-ma-firebase-default-rtdb.europe-west1.firebasedatabase.app",
        description="Firebase Realtime Database URL",
    )

    # Storage for temp audio files
    TEMP_DIR: str = Field(default="/tmp/whisper_ws")

    # Whisper model name ("tiny", "base", "small", "medium", "large")
    WHISPER_MODEL: str = Field(default="base")

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure temp directory exists
Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
