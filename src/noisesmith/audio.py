"""File helpers: where sounds are saved, safe file names, and reading and writing audio files."""

import io
import os
import re
import struct
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SAMPLE_RATE = 48000  # samples per second (CD is 44100; 48000 is standard for games/video)
FORMATS = ("wav", "flac", "ogg", "mp3")
_WRITE_CHUNK = 16384  # samples handed to the encoder at a time
# Quality settings for the compressed formats: about 120 kbps, which is clean for sound effects.
_SOUNDFILE_FORMATS = {
    "flac": dict(format="FLAC", subtype="PCM_16"),
    "ogg": dict(format="OGG", subtype="VORBIS", compression_level=0.3),
    "mp3": dict(format="MP3", subtype="MPEG_LAYER_III", compression_level=0.15),
}


def safe_name(name: str) -> str:
    """Turn any text into a safe file name (letters, digits, - and _ only)."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or "sound"


def check_format(fmt: str) -> str:
    fmt = (fmt or "wav").lower().lstrip(".")
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format {fmt!r}. Choose from: {', '.join(FORMATS)}")
    return fmt


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


def write_wav(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE, loop: bool = False) -> Path:
    """Save mono audio (values -1..1) as a 16-bit WAV file.

    With `loop=True` the file also records "this whole sound is a loop" in a standard `smpl`
    chunk, which game engines such as Godot and FMOD read to loop it without gaps.
    """
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).round().astype("<i2").tobytes()
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if loop:
        loop_body = struct.pack("<IIIIII", 0, 0, 0, len(samples) - 1, 0, 0)  # forward loop over the whole sound
        smpl = struct.pack("<IIIIIIIII", 0, 0, round(1e9 / sample_rate), 60, 0, 0, 0, 1, 0) + loop_body
        chunks += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    chunks += b"data" + struct.pack("<I", len(pcm)) + pcm
    path.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)
    return path


def write_audio(path: Path, samples: np.ndarray, sample_rate: int = SAMPLE_RATE, loop: bool = False) -> Path:
    """Save mono audio in the format given by the file's extension (wav, flac, ogg or mp3)."""
    fmt = check_format(path.suffix)
    if fmt == "wav":
        return write_wav(path, samples, sample_rate, loop)
    data = np.clip(samples, -1.0, 1.0).astype("float32")
    # Hand the encoder small pieces. Writing a long sound in one go crashed the OGG encoder
    # (a stack overflow that took the whole program down) once the sound passed about 10 seconds.
    with sf.SoundFile(str(path), mode="w", samplerate=sample_rate, channels=1, **_SOUNDFILE_FORMATS[fmt]) as out:
        for start in range(0, len(data), _WRITE_CHUNK):
            out.write(data[start : start + _WRITE_CHUNK])
    return path


def read_audio(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Read any wav, flac, ogg or mp3 file as mono audio at the standard sample rate."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No such sound file: {path}")
    check_format(path.suffix)
    try:
        data, rate = sf.read(str(path), always_2d=True, dtype="float64")
    except Exception as exc:  # soundfile raises its own error type for unreadable files
        raise ValueError(f"Could not read {path.name} as audio: {exc}") from exc
    return _to_standard(data, rate, sample_rate)


def _to_standard(data: np.ndarray, rate: int, sample_rate: int) -> np.ndarray:
    """Mono, at the standard sample rate."""
    mono = data.mean(axis=1)
    if rate != sample_rate:
        ratio = Fraction(sample_rate, rate).limit_denominator(1000)
        mono = signal.resample_poly(mono, ratio.numerator, ratio.denominator)
    return mono


def decode_bytes(content: bytes, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Turn audio that arrived over the network (an MP3, say) into mono audio at the standard rate."""
    try:
        data, rate = sf.read(io.BytesIO(content), always_2d=True, dtype="float64")
    except Exception as exc:
        raise ValueError(f"The service returned something that is not valid audio: {exc}") from exc
    return _to_standard(data, rate, sample_rate)
