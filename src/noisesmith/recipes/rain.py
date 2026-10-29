"""Rain: a bed of hiss with thousands of individual drops on top."""

import numpy as np

from noisesmith.dsp.curves import smooth_random
from noisesmith.dsp.filters import bandpass, lowpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import brown, pink
from noisesmith.recipes.base import Params, Recipe


def _unit(x):
    return x / (np.std(x) + 1e-12)


def render(p: Params) -> np.ndarray:
    sr, rng, i = p.sr, p.rng, p.intensity
    # Filters need a moment to settle, so make a little extra and throw the start away.
    warmup = int(0.5 * sr)
    n_out = int((p.duration_s or 10.0) * sr)
    n = n_out + warmup

    # Layer 1: the steady hiss of countless tiny drops far away.
    wobble = smooth_random(n, 0.5, rng, sr, 0.9, 1.1)
    bed = _unit(bandpass(pink(n, rng), 700, 9000 + 3000 * i, sr)) * wobble
    bed_level = 0.15 + 0.8 * i**1.3

    # Layer 2: individual drops. Each is a short, quickly fading ping with a small upward chirp.
    drop_count = int((15 + 1800 * i**1.6) * n / sr)
    length = int(0.025 * sr)
    t = np.arange(length) / sr
    drops = np.zeros(n + length)
    starts = rng.integers(0, n, drop_count)
    freqs = np.exp(rng.normal(np.log(3500), 0.45, drop_count)).clip(1500, 9000)
    taus = rng.uniform(0.002, 0.007, drop_count)
    amps = np.exp(rng.normal(0, 0.6, drop_count))
    for start, freq, tau, amp in zip(starts, freqs, taus, amps):
        drops[start : start + length] += amp * np.exp(-t / tau) * np.sin(2 * np.pi * freq * t * (1 + 60 * t))
    drops = _unit(drops[:n])

    # Layer 3: a low roar that only appears in heavy downpours.
    roar = _unit(lowpass(brown(n, rng, sr), 300 + 400 * i, sr))

    sig = bed * bed_level + drops * 0.6 + roar * i**2.2 * 0.6
    return finalize(sig[warmup:], sr, -24 + 21 * i**0.8, fade_in_s=0.1, fade_out_s=0.25)


RECIPE = Recipe(
    name="rain",
    summary="Rain falling, from a light drizzle to a heavy downpour.",
    intensity_meaning=(
        "How hard it rains. 0.1 = drizzle with sparse drops, 0.4 = steady rain, "
        "0.7 = heavy rain, 1.0 = torrential downpour with a deep roar."
    ),
    size_meaning="Not used.",
    styles={"rain": "Rain on open ground (default)."},
    default_duration="10 seconds",
    render=render,
)
