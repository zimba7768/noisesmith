"""Shared helpers for the recording-based ambience recipes (wind, rain, thunder)."""

import numpy as np

from noisesmith import samples
from noisesmith.dsp import loudness
from noisesmith.dsp.levels import db_to_amp, fade

CEILING_DBFS = -1.0  # nothing in a finished bed goes above this


def bed(clip_id: str, n: int, rng: np.random.Generator) -> np.ndarray:
    """`n` samples of a wind or rain recording, starting somewhere random.

    The recording is looped seamlessly, so any length works, and a different seed starts at a
    different place, so no two sounds are the same take.
    """
    loop = samples.seamless_bed(clip_id)
    start = int(rng.integers(len(loop)))
    return np.take(loop, np.arange(start, start + n), mode="wrap")


def deepened(clip_id: str, n: int, rng: np.random.Generator, speed: float) -> np.ndarray:
    """The same kind of bed played slower (`speed` below 1), which makes it lower and heavier."""
    piece = bed(clip_id, int(n * speed) + 2000, rng)
    return samples.varispeed(piece, speed)[:n]


def blend(*weights: float) -> tuple:
    """Scale the weights so the layers add up at an even loudness (equal power)."""
    total = float(np.sqrt(sum(w * w for w in weights)))
    return tuple(w / total for w in weights) if total > 0 else weights


def finish(x: np.ndarray, sr: int, target_lufs: float, fade_in_s: float, fade_out_s: float) -> np.ndarray:
    """Last step for a bed: set how loud it SEEMS (LUFS), fade the edges, and keep peaks under the ceiling.

    Wind and rain are set by loudness, not by their highest peak, because a single big raindrop
    would otherwise decide how loud a whole minute of rain is.
    """
    x = fade(x - np.mean(x), fade_in_s, fade_out_s, sr)
    x = x * db_to_amp(target_lufs - loudness.lufs(x, sr))
    if np.max(np.abs(x)) > db_to_amp(CEILING_DBFS):
        x = loudness.soft_limit(x, CEILING_DBFS)
    return x
