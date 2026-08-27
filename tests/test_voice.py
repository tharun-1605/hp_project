"""Unit tests for CommandProcessor and VoiceManager."""
import pytest
from backend.voice.command_processor import CommandProcessor
from backend.voice.voice_manager import VoiceManager

def test_command_processor_intents():
    processor = CommandProcessor()

    c1 = processor.parse_command("Navigate to Railway Station")
    assert c1["intent"] == "navigate"
    assert c1["destination"] == "railway station"

    c2 = processor.parse_command("stop navigation")
    assert c2["intent"] == "stop_navigation"

    c3 = processor.parse_command("where am I?")
    assert c3["intent"] == "query_location"

    c4 = processor.parse_command("repeat")
    assert c4["intent"] == "repeat_instruction"

def test_voice_manager_cooldown():
    voice_mgr = VoiceManager(enabled=True, cooldown_seconds=2.0)
    
    # First speak should succeed
    s1 = voice_mgr.speak("Walk straight", priority="MEDIUM")
    assert s1 is True

    # Immediate duplicate speak should be suppressed by cooldown
    s2 = voice_mgr.speak("Walk straight", priority="MEDIUM")
    assert s2 is False

    # Different text should speak
    s3 = voice_mgr.speak("Turn left", priority="MEDIUM")
    assert s3 is True
