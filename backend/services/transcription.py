from loguru import logger
from typing import Optional
import os

class TranscriptionEngine:
    """Wrapper for OpenAI Whisper transcription."""

    def __init__(self, model_name: str = "base", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model = None
        logger.info(f"TranscriptionEngine initialized (model={model_name}, device={device})")

    def _load_model(self):
        """Lazy-load Whisper model on first use."""
        if self.model is None:
            try:
                import whisper
                logger.info(f"Loading Whisper model: {self.model_name}")
                self.model = whisper.load_model(self.model_name, device=self.device)
                logger.info("Whisper model loaded successfully")
            except ImportError:
                logger.error("Whisper not installed; install with: pip install openai-whisper")
                self.model = False  # Mark as failed
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                self.model = False

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Optional ISO 639-1 code (e.g., "es" for Spanish, "en" for English)

        Returns:
            Transcribed text, or error message if transcription fails
        """
        self._load_model()

        if self.model is False:
            logger.warning("Whisper unavailable; returning fallback")
            return "[Transcription unavailable: Whisper not installed]"

        try:
            logger.info(f"Transcribing: {audio_path}")
            result = self.model.transcribe(audio_path, language=language)
            text = result.get("text", "").strip()
            logger.info(f"Transcription complete ({len(text)} chars)")
            return text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return f"[Transcription error: {str(e)}]"

    def transcribe_batch(self, audio_paths: list, language: Optional[str] = None) -> list:
        """Transcribe multiple audio files."""
        results = []
        for i, path in enumerate(audio_paths):
            logger.debug(f"Transcribing batch {i+1}/{len(audio_paths)}")
            results.append(self.transcribe(path, language=language))
        return results

    def health_check(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            logger.warning("Whisper not available")
            return False
