"""
Offline speech-to-text using Vosk.

Requires the `vosk` package and a downloaded model.
Default model path points to the small English model shipped with this repo.
"""
import os
import json
import wave
import tempfile

from termcolor import cprint

try:
    import vosk
except ImportError:
    vosk = None

try:
    import pyaudio
except ImportError:
    pyaudio = None


DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "models", "vosk", "vosk-model-small-en-us-0.15"
)

SAMPLE_RATE = 16000
CHUNK_SIZE = 4096


class OfflineSTT:
    def __init__(self, model_path=None):
        if vosk is None:
            raise RuntimeError(
                "Vosk is not installed. Run: pip install vosk"
            )
        if pyaudio is None:
            raise RuntimeError(
                "PyAudio is not installed."
            )

        model_path = model_path or DEFAULT_MODEL_PATH
        if not os.path.isdir(model_path):
            raise RuntimeError(
                "Vosk model not found at {}. "
                "Download it from https://alphacephei.com/vosk/models".format(model_path)
            )

        cprint("Loading Vosk model from {}...".format(model_path), "yellow")
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)

    def listen_once(self, timeout=None):
        """Listen from the microphone and return the recognized text."""
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        cprint("Listening offline...", "magenta")
        stream.start_stream()

        final_text = ""
        try:
            while True:
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        final_text = text
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        return final_text

    def listen_from_file(self, wav_path):
        """Recognize speech from a 16-bit mono WAV file."""
        if not os.path.isfile(wav_path):
            return ""

        recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
        with wave.open(wav_path, "rb") as wf:
            while True:
                data = wf.readframes(CHUNK_SIZE)
                if len(data) == 0:
                    break
                recognizer.AcceptWaveform(data)

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "")


def is_available():
    """Return True if Vosk and a model are available."""
    if vosk is None or pyaudio is None:
        return False
    return os.path.isdir(DEFAULT_MODEL_PATH)
