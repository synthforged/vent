import sys
import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 512  # ~32ms at 16kHz
NUM_BARS = 5


class Recorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._rms_history: list[float] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def start(self) -> bool:
        self._chunks.clear()
        self._rms_history.clear()
        return self._open_stream()

    def pause(self) -> None:
        """Stop the stream but keep accumulated chunks."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def resume(self) -> None:
        """Reopen the stream, continuing to append to existing chunks."""
        self._open_stream()

    def _open_stream(self) -> bool:
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                callback=self._callback,
            )
            self._stream.start()
            return True
        except sd.PortAudioError as e:
            print(f"vent: audio device error: {e}", file=sys.stderr)
            self._stream = None
            return False

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype="float32")
            return np.concatenate(self._chunks)

    def get_levels(self) -> list[float]:
        """Return NUM_BARS RMS levels (0.0–1.0) from recent audio."""
        with self._lock:
            history = list(self._rms_history[-NUM_BARS:])
        # Pad to NUM_BARS if not enough data yet
        while len(history) < NUM_BARS:
            history.insert(0, 0.0)
        return history

    def _callback(self, indata: np.ndarray, frames, time_info, status) -> None:
        chunk = indata[:, 0].copy()
        rms = float(np.sqrt(np.mean(chunk**2)))
        # Normalize: typical speech RMS is 0.01–0.1, scale to 0–1
        level = min(1.0, rms * 15.0)
        with self._lock:
            self._chunks.append(chunk)
            self._rms_history.append(level)
            # Keep only recent history
            if len(self._rms_history) > 60:
                self._rms_history = self._rms_history[-60:]
