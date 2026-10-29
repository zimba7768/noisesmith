"""Prepare the recorded creaks used by the door_creak and floor_creak recipes.

Each source recording (all CC0, see src/noisesmith/assets/creaks/CREDITS.md) is turned into a
small, consistent file: mono, 48 kHz, silence trimmed, leveled to -1 dBFS peak, tiny edge fades,
saved as 16-bit WAV.

The original downloads are not in this repository. To re-run, download the packs listed in
CREDITS.md and point this script at the folder that holds them:

    uv run --no-project --with numpy --with scipy --with soundfile python -I scripts/prepare_creak_assets.py <sources folder>

where <sources folder> contains: qubodup/, laleksic/, rubberduck/ (unpacked packs) and
hinge/creaky_door_hinge.wav.
"""

import sys
import wave
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

TARGET_SR = 48000
OUT = Path(__file__).resolve().parent.parent / "src" / "noisesmith" / "assets" / "creaks"

# output name -> source file, relative to the sources folder
CLIPS = {
    "door_creak_open": "laleksic/door_creak_open.wav",
    "door_creak_close": "laleksic/door_creak_close.wav",
    "door_open": "laleksic/door_open.wav",
    "hinge_spooky": "hinge/creaky_door_hinge.wav",
    "qubodup_open_01": "qubodup/qubodup-DoorSet/flac/qubodup-DoorOpen01.flac",
    "qubodup_open_03": "qubodup/qubodup-DoorSet/flac/qubodup-DoorOpen03.flac",
    "qubodup_open_05": "qubodup/qubodup-DoorSet/flac/qubodup-DoorOpen05.flac",
    "qubodup_open_07": "qubodup/qubodup-DoorSet/flac/qubodup-DoorOpen07.flac",
    "floor_creak_1": "laleksic/floor_creak1.wav",
    "floor_creak_2": "laleksic/floor_creak2.wav",
    "floor_creak_3": "laleksic/floor_creak3.wav",
}


def prepare(path: Path) -> np.ndarray:
    x, sr = sf.read(str(path), always_2d=True)
    x = x.mean(axis=1)
    if sr != TARGET_SR:
        ratio = Fraction(TARGET_SR, sr).limit_denominator(1000)
        x = signal.resample_poly(x, ratio.numerator, ratio.denominator)
    x = x - np.mean(x)

    # Trim leading and trailing near-silence, keeping 20 ms of room at each end.
    loud = np.flatnonzero(np.abs(x) > 0.01 * np.max(np.abs(x)))
    pad = int(0.02 * TARGET_SR)
    x = x[max(loud[0] - pad, 0) : loud[-1] + pad]

    x = x / np.max(np.abs(x)) * 10 ** (-1 / 20)  # peak at -1 dBFS
    edge = int(0.005 * TARGET_SR)
    x[:edge] *= np.linspace(0, 1, edge)
    x[-edge:] *= np.linspace(1, 0, edge)
    return x


def main() -> None:
    sources = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, rel in CLIPS.items():
        x = prepare(sources / rel)
        pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
        path = OUT / f"{name}.wav"
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(TARGET_SR)
            f.writeframes(pcm.tobytes())
        total += path.stat().st_size
        print(f"{name:18s} {len(x)/TARGET_SR:5.2f}s  {path.stat().st_size/1000:6.0f} KB")
    print(f"total {total/1e6:.2f} MB")


if __name__ == "__main__":
    main()
