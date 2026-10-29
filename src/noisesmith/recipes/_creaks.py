"""Shared engine for the recording-based creak recipes (door_creak and floor_creak).

Synthesizing a creak convincingly proved very hard, so these recipes reshape real CC0
recordings instead:
  * size changes the playback speed, so bigger things sound lower, slower and longer;
  * long creaks chain several recordings together with cross-fades and gaps;
  * intensity adds a deeper second layer, opens up the brightness, and raises the level;
  * the seed decides which recordings are used and how they are varied, so every variation
    is different and the same seed always repeats.
"""

import numpy as np

from noisesmith import samples
from noisesmith.dsp.filters import lowpass
from noisesmith.dsp.levels import fade, finalize
from noisesmith.recipes.base import Params


def _timeline(p: Params, pool: tuple, speed: float, want_s: float, long_style: bool, used: list) -> np.ndarray:
    """Lay recordings end to end until the timeline is at least `want_s` long."""
    sr, rng = p.sr, p.rng
    pieces, cursor, total = [], 0, 0
    while total < want_s * sr:
        clip_id = pool[int(rng.integers(len(pool)))]
        used.append(clip_id)
        piece = samples.varispeed(samples.load(clip_id), speed * rng.uniform(0.9, 1.1))
        if long_style:  # a continuous, drawn-out creak: blend each clip into the last
            piece = fade(piece, 0.06, 0.06, sr)
        pieces.append((cursor, piece))
        total = cursor + len(piece)
        gap = rng.uniform(-0.1, 0.05) if long_style else rng.uniform(-0.05, 0.3)
        cursor = max(total + int(gap * sr), 0)
    out = np.zeros(total)
    for start, piece in pieces:
        out[start : start + len(piece)] += piece
    return out


def compose(p: Params, pool: tuple, long_style: bool, default_s: float) -> np.ndarray:
    """Build one creak from recordings. `default_s` is the length to aim for when none is asked."""
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    speed = 2 ** (-1.2 * (size - 0.5)) * (0.85 if long_style else 1.0)  # bigger = slower, lower
    want = p.duration_s or default_s * (1.0 if long_style else 1.0 + size)
    used: list = []

    sig = _timeline(p, pool, speed, want, long_style, used)

    # The more worn it is, the more a deeper second creak joins in underneath.
    if i > 0.55:
        layer = _timeline(p, pool, speed * rng.uniform(0.65, 0.8), want, long_style, used)
        offset = int(rng.uniform(0.0, 0.4) * sr)
        gain = 0.7 * (i - 0.55) / 0.45
        n = max(len(sig), offset + len(layer))
        mixed = np.zeros(n)
        mixed[: len(sig)] += sig
        mixed[offset : offset + len(layer)] += gain * layer
        sig = mixed

    # Cut to length: exactly what was asked, or a little over the target when left to chance.
    limit = int((p.duration_s or want * 1.4) * sr)
    sig = sig[:limit]
    if p.duration_s and len(sig) < limit:
        sig = np.pad(sig, (0, limit - len(sig)))

    sig = lowpass(sig, 2500 + 9500 * i, sr)  # a gentler creak is softer and duller
    sig = np.tanh(sig / (2.5 * np.percentile(np.abs(sig), 95) + 1e-12))  # tame the loudest pops
    p.notes["recordings"] = sorted(set(used))
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.003, fade_out_s=0.2)
