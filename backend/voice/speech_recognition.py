"""Vosk Offline Speech Recognition wrapper with fallback simulation mode."""
import os
import json
from typing import Optional, Dict, Any
from backend.utils.logger import get_logger

logger = get_logger("SpeechRecognizer")

class SpeechRecognizer:
    """Vosk-based offline STT engine."""

    def __init__(self, model_path: str = "backend/models/vosk-model-small-en-us", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.recognizer = None
        self.is_simulated = False
        self._init_vosk()

    def _init_vosk(self):
        """Load Vosk model or fallback to text API / simulation mode."""
        try:
            import vosk
            if os.path.exists(self.model_path):
                model = vosk.Model(self.model_path)
                self.recognizer = vosk.KaldiRecognizer(model, self.sample_rate)
                logger.info(f"Loaded Vosk speech recognition model from {self.model_path}")
                return
            else:
                logger.info(f"Vosk model path {self.model_path} not found. Voice recognition will accept text inputs / web speech API.")
        except Exception as e:
            logger.warning(f"Vosk STT initialization failed ({e}). Operating in text-command compatibility mode.")

        self.is_simulated = True

    def process_audio_chunk(self, chunk: bytes) -> Optional[str]:
        """Process incoming raw audio bytes and return transcribed text string if complete phrase detected."""
        if self.is_simulated or not self.recognizer:
            return None

        try:
            if self.recognizer.AcceptWaveform(chunk):
                res = json.loads(self.recognizer.Result())
                text = res.get("text", "").strip()
                if text:
                    logger.info(f"Vosk transcribed: '{text}'")
                    return text
        except Exception as e:
            logger.error(f"Error processing audio chunk in Vosk: {e}")

        return None
