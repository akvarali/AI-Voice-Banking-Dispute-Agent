"""Text-to-speech using pyttsx3 (offline, uses the Windows SAPI5 voices)."""

import os
import tempfile

import pyttsx3


def text_to_speech(text: str) -> bytes:
    """Convert text into WAV audio bytes so Streamlit can play it in the browser."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 170)  # Words per minute (default ~200 is a bit fast)
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        engine.stop()

        with open(wav_path, "rb") as f:
            return f.read()
    finally:
        os.remove(wav_path)


def speak(text: str) -> None:
    """Read text aloud through the PC speakers (used by the desktop app)."""
    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.say(text)
    engine.runAndWait()  # Blocks until speaking finishes, so call it from a background thread
    engine.stop()
