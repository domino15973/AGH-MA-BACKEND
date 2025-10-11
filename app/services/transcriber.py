from typing import Optional
import warnings


# Prefer faster-whisper if available; otherwise fall back to openai-whisper.
# Both require ffmpeg installed in the environment.
class Transcriber:
    """
    Simple wrapper around Whisper to transcribe audio files.
    The implementation prioritizes simplicity and stability over advanced features.
    """

    def __init__(self, model_name: str = "base"):
        self._backend = None
        self._model_name = model_name
        self._init_backend()

    def _init_backend(self):
        try:
            from faster_whisper import WhisperModel  # type: ignore
            # CPU default; adjust compute_type to "int8" or "float32" as needed
            self._backend = ("faster", WhisperModel(self._model_name, device="cpu", compute_type="int8"))
        except Exception:
            try:
                import whisper  # type: ignore
                self._backend = ("openai", whisper.load_model(self._model_name))
            except Exception as e:
                raise RuntimeError(
                    "No Whisper backend available. Install 'faster-whisper' or 'openai-whisper' and ensure ffmpeg is present."
                ) from e

    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe an audio file and return plain text. Word-level timestamps are intentionally omitted.
        """
        kind, model = self._backend

        if kind == "faster":
            segments, info = model.transcribe(file_path, language=language, vad_filter=True)
            text = "".join(seg.text for seg in segments)
            return text.strip()

        # openai-whisper fallback
        import whisper  # type: ignore
        # Disable verbose options to keep it simple and fast
        result = model.transcribe(file_path, language=language, fp16=False, verbose=False)
        text = result.get("text", "")
        return text.strip()
