"""Voice Command NLU Processor for parsing spoken text into structured intents."""
import re
from typing import Dict, Any
from backend.utils.logger import get_logger

logger = get_logger("CommandProcessor")

class CommandProcessor:
    """Parses spoken text queries into structured command intents."""

    def parse_command(self, text: str) -> Dict[str, Any]:
        """Convert natural text into intent dictionary."""
        if not text:
            return {"intent": "unknown", "raw_text": ""}

        clean = text.strip().lower()

        # 1. Destination Navigation Intent
        # Patterns: "navigate to X", "go to X", "take me to X", "direct me to X"
        nav_match = re.search(r"(?:navigate|go|take me|direct me)\s+(?:to\s+)?(.+)", clean)
        if nav_match:
            dest = nav_match.group(1).strip()
            # Remove filler words
            dest = re.sub(r"^(the|a|an)\s+", "", dest)
            return {
                "intent": "navigate",
                "destination": dest,
                "raw_text": text
            }

        # 2. Control Intents
        if "start navigation" in clean or "start route" in clean or "start" == clean:
            return {"intent": "start_navigation", "raw_text": text}
        elif "stop navigation" in clean or "end navigation" in clean or "stop" == clean or "cancel" == clean:
            return {"intent": "stop_navigation", "raw_text": text}
        elif "pause navigation" in clean or "pause" in clean:
            return {"intent": "pause_navigation", "raw_text": text}
        elif "resume navigation" in clean or "resume" in clean:
            return {"intent": "resume_navigation", "raw_text": text}

        # 3. Telemetry Queries
        elif "where am i" in clean or "my location" in clean:
            return {"intent": "query_location", "raw_text": text}
        elif "repeat" in clean or "say again" in clean:
            return {"intent": "repeat_instruction", "raw_text": text}
        elif "what's ahead" in clean or "what is ahead" in clean or "ahead" in clean:
            return {"intent": "query_ahead", "raw_text": text}
        elif "how far" in clean or "distance to destination" in clean:
            return {"intent": "query_distance", "raw_text": text}

        # Fallback keyword match if destination spoken alone (e.g., "railway station")
        if len(clean) > 3 and not any(w in clean for w in ["what", "how", "where", "yes", "no"]):
            return {
                "intent": "navigate",
                "destination": clean,
                "raw_text": text
            }

        return {
            "intent": "unknown",
            "raw_text": text
        }
