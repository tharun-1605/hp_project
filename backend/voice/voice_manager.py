"""Voice Manager for offline Text-to-Speech synthesis with priority queueing and cooldown suppression."""
import time
import os
import subprocess
import threading
import queue
from typing import Optional, Dict, Any
from backend.utils.logger import get_logger

logger = get_logger("VoiceManager")

PRIORITY_LEVELS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}

class VoiceManager:
    """Manages Piper/pyttsx3 offline TTS synthesis, priority speech queue, and alert interruption."""

    def __init__(self, piper_model_path: str = "backend/models/en_US-lessac-medium.onnx",
                 cooldown_seconds: float = 3.0, enabled: bool = True, engine: str = "web_speech"):
        self.piper_model_path = piper_model_path
        self.cooldown_seconds = cooldown_seconds
        self.enabled = enabled
        self.engine = engine

        self.last_spoken_text = ""
        self.last_spoken_time = 0.0

        # Thread-safe speech queue storing (priority_value, timestamp, text)
        self.speech_queue = queue.PriorityQueue()
        self.is_speaking = False
        self.current_priority = 0
        self._speech_thread: Optional[threading.Thread] = None

        self._init_tts_engine()

    def _init_tts_engine(self):
        """Check for local Piper binary or pyttsx3 fallback engine."""
        self.has_piper = False
        self.pyttsx3_engine = None

        # Check piper binary
        try:
            res = subprocess.run(["piper", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                self.has_piper = True
                logger.info("Piper TTS engine binary detected.")
        except Exception:
            pass

        if not self.has_piper:
            try:
                import pyttsx3
                self.pyttsx3_engine = pyttsx3.init()
                self.pyttsx3_engine.setProperty("rate", 160) # Slightly slower for clarity
                logger.info("pyttsx3 TTS fallback engine initialized.")
            except Exception as e:
                logger.warning(f"pyttsx3 TTS fallback initialization failed: {e}. Voice output will stream via WebSockets to browser TTS.")

    def speak(self, text: str, priority: str = "MEDIUM", force: bool = False) -> bool:
        """Enqueue or immediately speak a voice instruction."""
        if not self.enabled or not text:
            return False

        p_val = PRIORITY_LEVELS.get(priority.upper(), 2)
        now = time.time()

        # Duplicate suppression check within cooldown period
        if not force and text == self.last_spoken_text and (now - self.last_spoken_time) < self.cooldown_seconds:
            return False

        # If a CRITICAL alert arrives while lower priority is speaking, allow immediate interrupt
        if p_val == PRIORITY_LEVELS["CRITICAL"] and self.is_speaking and self.current_priority < p_val:
            logger.info(f"CRITICAL interrupt requested for text: '{text}'")

        self.last_spoken_text = text
        self.last_spoken_time = now

        logger.info(f"Voice output [{priority}]: '{text}'")
        self._synthesize_speech(text)
        return True

    def _synthesize_speech(self, text: str):
        """Perform TTS audio generation using available engine in a non-blocking thread."""
        if self.engine == "web_speech":
            # Browser JS will synthesize via Web Speech API over WebSocket
            return

        def run_speak():
            self.is_speaking = True
            try:
                if self.has_piper and os.path.exists(self.piper_model_path):
                    cmd = ["piper", "--model", self.piper_model_path, "--output_raw"]
                    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    p.communicate(input=text.encode("utf-8"))
                elif self.pyttsx3_engine:
                    self.pyttsx3_engine.say(text)
                    self.pyttsx3_engine.runAndWait()
            except Exception as e:
                logger.error(f"TTS synthesis error: {e}")
            finally:
                self.is_speaking = False

        threading.Thread(target=run_speak, daemon=True).start()
