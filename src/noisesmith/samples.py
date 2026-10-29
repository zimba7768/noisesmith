"""Recorded sounds that ship with NoiseSmith (the creaks). See assets/creaks/CREDITS.md."""

import wave
from fractions import Fraction
from functools import lru_cache
from importlib import resources

import numpy as np
from scipy import signal

from noisesmith.audio import SAMPLE_RATE

# Groups of recordings that suit different jobs.
DOOR_LONG = ("hinge_spooky", "door_creak_open", "door_creak_close")  # 1.4 to 4.3 s: a whole creak
DOOR_SHORT = ("door_open", "qubodup_open_01", "qubodup_open_03", "qubodup_open_05", "qubodup_open_07")  # under 1 s
FLOOR = ("floor_creak_1", "floor_creak_2", "floor_creak_3")  # 1.7 to 2.4 s of creaking boards


@lru_cache(maxsize=None)
def load(clip_id: str) -> np.ndarray:
    """A recording as a mono float array at the standard sample rate. The result is read-only."""
    path = resources.files("noisesmith.assets").joinpath("creaks", f"{clip_id}.wav")
    with path.open("rb") as handle, wave.open(handle, "rb") as w:
        assert w.getframerate() == SAMPLE_RATE and w.getnchannels() == 1 and w.getsampwidth() == 2
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    audio = pcm.astype(np.float64) / 32768.0
    audio.setflags(write=False)
    return audio


def varispeed(x: np.ndarray, speed: float) -> np.ndarray:
    """Play faster (speed above 1: higher and shorter) or slower (below 1: lower and longer)."""
    ratio = Fraction(speed).limit_denominator(40)
    return signal.resample_poly(x, ratio.denominator, ratio.numerator)
