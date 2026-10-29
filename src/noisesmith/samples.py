"""Recorded sounds that ship with NoiseSmith: the creaks, and the wind, rain and thunder.

See assets/creaks/CREDITS.md and assets/ambience/CREDITS.md for where each recording comes from.
"""

import wave
from fractions import Fraction
from functools import lru_cache
from importlib import resources

import numpy as np
import soundfile as sf
from scipy import signal

from noisesmith.audio import SAMPLE_RATE
from noisesmith.dsp.loop import make_seamless

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


# ---- wind, rain and thunder -------------------------------------------------------------------
WIND_LIGHT = ("wind_light_grass", "wind_light_window")  # a breeze
WIND_STRONG = ("wind_strong_trees_1", "wind_strong_trees_3", "wind_strong_leaves", "wind_strong_inside")  # storm wind
WIND_HOWL = ("wind_whistle_chimney",)  # whistling through a gap
RAIN_SOFT = ("rain_soft_umbrella",)
RAIN_HARD = ("rain_hard_concrete",)
RAIN_HEAVY = ("rain_heavy_terrace",)
THUNDER = tuple(f"thunder_{n}" for n in ("2718", "3115", "3181", "3113", "3114", "3116", "3179", "3180"))
BED_CROSSFADE_S = 2.0


@lru_cache(maxsize=None)
def load_ambience(clip_id: str) -> np.ndarray:
    """A wind, rain or thunder recording as mono float audio at the standard rate. Read-only."""
    path = resources.files("noisesmith.assets").joinpath("ambience", f"{clip_id}.ogg")
    with path.open("rb") as handle:
        audio, rate = sf.read(handle, dtype="float64", always_2d=True)
    assert rate == SAMPLE_RATE and audio.shape[1] == 1
    audio = audio[:, 0].copy()
    audio.setflags(write=False)
    return audio


@lru_cache(maxsize=None)
def seamless_bed(clip_id: str) -> np.ndarray:
    """A wind or rain recording turned into a loop that can repeat forever without a join."""
    loop = make_seamless(load_ambience(clip_id), SAMPLE_RATE, BED_CROSSFADE_S)
    loop.setflags(write=False)
    return loop
