import sys
import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel("small", compute_type="int8", device="cpu")
    return _model


def transcribe(audio: np.ndarray) -> str:
    """Transcribe float32 16kHz mono audio to text."""
    if len(audio) == 0:
        return ""
    try:
        model = _get_model()
        segments, _ = model.transcribe(audio, language=None, beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        print(f"vent: transcription error: {e}", file=sys.stderr)
        return ""
