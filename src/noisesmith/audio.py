"""File helpers: where sounds are saved, safe file names, and writing WAV files."""

import os
import re
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 48000  # samples per second (CD is 44100; 48000 is standard for games/video)


def safe_name(name: str) -> str:
    """Turn any text into a safe file name (letters, digits, - and _ only)."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "sound"


def resolve_output_dir(output_dir: str | None = None) -> Path:
    """Decide which folder sounds are saved in, and create it.

    Order of preference: the `output_dir` argument, then the NOISESMITH_OUTPUT_DIR
    environment variable (the Desktop extension sets this), then ./sounds in the
    folder Claude is working in.
    """
    chosen = output_dir or os.environ.get("NOISESMITH_OUTPUT_DIR") or "sounds"
    folder = Path(chosen).expanduser()
    if not folder.is_absolute():
        folder = Path.cwd() / folder
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def unique_path(folder: Path, stem: str, suffix: str = ".wav") -> Path:
    """A path that does not exist yet, so earlier sounds are never overwritten."""
    path = folder / f"{stem}{suffix}"
    counter = 2
    while path.exists():
        path = folder / f"{stem}-{counter}{suffix}"
        counter += 1
    return path


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> Path:
    """Save mono audio (values -1..1) as a 16-bit WAV file."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
    return path
