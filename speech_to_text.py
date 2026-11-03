"""Speech-to-text using the free Google Web Speech API (via the SpeechRecognition library).

No model download and no API key are needed, but an internet connection is required.
"""

import io  # Lets us treat raw audio bytes like a file

import speech_recognition as sr  # Library that wraps several speech engines, incl. Google

from dispute_tool import extract_dispute_id

try:
    # Use the Windows certificate store so HTTPS works behind a corporate proxy (fixes SSL errors)
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass  # Optional: on a normal home network the app works without it

# Re-export the library's exceptions so app.py does not need to import speech_recognition
UnknownValueError = sr.UnknownValueError  # Raised when speech is silent or unclear
RequestError = sr.RequestError  # Raised when Google cannot be reached
WaitTimeoutError = sr.WaitTimeoutError  # Raised when nobody speaks into the microphone


def _recognize_best(recognizer: sr.Recognizer, audio: sr.AudioData, language: str) -> str:
    """Ask Google for several possible transcripts and prefer one that contains a dispute ID.

    Google often returns e.g. ["check dispute the 1001", "check dispute D1001", ...];
    picking the one with an ID makes recognition of IDs much more reliable.
    """
    result = recognizer.recognize_google(audio, language=language, show_all=True)
    alternatives = [alt["transcript"] for alt in result.get("alternative", [])] if result else []
    if not alternatives:
        raise UnknownValueError()  # Google returned nothing: silence or unclear speech

    for transcript in alternatives:
        if extract_dispute_id(transcript):
            return transcript
    return alternatives[0]  # No ID anywhere: return Google's top guess


def transcribe(audio_bytes: bytes, language: str = "en-US", reduce_noise: bool = True) -> str:
    """Convert WAV/FLAC/AIFF audio bytes into text using Google Speech Recognition."""
    recognizer = sr.Recognizer()

    # Open the in-memory audio exactly like a file on disk
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        if reduce_noise:
            # Listen to the first 0.3 s to learn the background noise level
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
        audio = recognizer.record(source)  # Read the rest of the recording

    return _recognize_best(recognizer, audio, language)


def list_microphones() -> list[tuple[int, str]]:
    """Return (device_index, name) for every input device, e.g. [(1, 'Headset'), ...]."""
    pyaudio = sr.Microphone.get_pyaudio().PyAudio()
    try:
        default_api = pyaudio.get_default_host_api_info()["index"]
        mics = []
        for i in range(pyaudio.get_device_count()):
            info = pyaudio.get_device_info_by_index(i)
            # Windows lists each device once per audio API; keep only the default API's inputs
            if info["maxInputChannels"] > 0 and info["hostApi"] == default_api:
                name = info["name"]
                try:
                    name = name.encode("latin-1").decode("utf-8")  # Fixes names like "IntelÂ®" -> "Intel®"
                except UnicodeError:
                    pass
                mics.append((i, name))
        return mics
    finally:
        pyaudio.terminate()


def listen_from_microphone(
    language: str = "en-US",
    device_index: int | None = None,
    timeout: int = 8,
    phrase_time_limit: int = 12,
    on_ready=None,
) -> str:
    """Record from the PC microphone (used by the desktop app) and return the text.

    device_index: microphone from list_microphones(); None = Windows default mic.
    on_ready:     optional function called when calibration is done and the user should speak.
    Requires PyAudio. Raises WaitTimeoutError if nobody speaks within `timeout` seconds.
    """
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.2  # Allow short pauses, e.g. "check dispute ... D1001"
    recognizer.non_speaking_duration = 0.5

    with sr.Microphone(device_index=device_index) as source:
        # Measure background noise BEFORE the user speaks (speaking now would cut off the first words)
        recognizer.adjust_for_ambient_noise(source, duration=0.7)
        # Keep the threshold low enough that normal speech on a quiet headset is still detected
        recognizer.energy_threshold = min(max(recognizer.energy_threshold, 150), 1500)
        if on_ready:
            on_ready()
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

    return _recognize_best(recognizer, audio, language)
