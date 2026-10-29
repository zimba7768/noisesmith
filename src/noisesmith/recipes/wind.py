"""Wind, from a faint breeze to a hurricane roar."""

import numpy as np

from noisesmith.dsp.curves import smooth_random
from noisesmith.dsp.filters import highpass, lowpass, swept_bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import brown, pink, white
from noisesmith.recipes.base import Params, Recipe


def _unit(x):
    """Scale to a standard deviation of 1 so layers can be mixed by simple weights."""
    return x / (np.std(x) + 1e-12)


def render(p: Params) -> np.ndarray:
    sr, rng, i = p.sr, p.rng, p.intensity
    # Filters need a moment to settle, so make a little extra and throw the start away.
    warmup = int(0.5 * sr)
    n_out = int((p.duration_s or 8.0) * sr)
    n = n_out + warmup
    gusty = p.style == "gusty"
    howling = p.style == "howling"

    # How the wind swells and fades. `gust` is slow, `flutter` is quicker turbulence.
    gust = smooth_random(n, (0.12 + 0.35 * i) * (1.8 if gusty else 1.0), rng, sr)
    flutter = smooth_random(n, 1.5 + 6.0 * i, rng, sr)
    depth = (0.8 if gusty else 0.5) - 0.2 * i  # strong wind stays strong; light wind comes and goes
    level = (1 - depth) + depth * gust
    level = level * (1 + 0.12 * i * (flutter - 0.5) * 2)

    # Layer 1: deep rumble that grows with strength.
    rumble = _unit(lowpass(brown(n, rng, sr), 90 + 260 * i, sr))

    # Layer 2: the main "whoosh" of air. Its colour brightens whenever a gust peaks.
    centre = 180 + (350 + 1800 * i) * gust
    body = _unit(swept_bandpass(pink(n, rng), centre, 0.8 + 0.5 * i, sr))

    # Layer 3: hiss and roar from turbulence, only really present in strong wind.
    hiss = _unit(highpass(lowpass(white(n, rng), 2000 + 2500 * i, sr), 1000, sr))

    # Layer 4: whistling through gaps; a narrow band that drifts up and down.
    whistle_amount = (0.5 if howling else 0.0) + max(0.0, i - 0.45) * 0.9
    sig = (
        rumble * (0.5 + 0.6 * i) * level**0.5
        + body * 0.8 * level
        + hiss * (0.04 + 0.25 * i**2) * level**1.5
    )
    if whistle_amount > 0:
        drift = smooth_random(n, 0.3 + 0.5 * i, rng, sr)
        whistle = _unit(swept_bandpass(white(n, rng), 420 + 1000 * drift + 250 * gust, 22, sr))
        sig += whistle * whistle_amount * 0.35 * level**2

    # Soft winds sit quietly; a hurricane fills the file.
    return finalize(sig[warmup:], sr, -22 + 19 * i**0.7, fade_in_s=0.15, fade_out_s=0.25)


RECIPE = Recipe(
    name="wind",
    summary="Wind ambience, from a faint breeze to a screaming hurricane.",
    intensity_meaning=(
        "Strength of the wind. 0.1 = gentle breeze, 0.3 = light wind, 0.6 = strong wind, "
        "0.8 = gale, 1.0 = hurricane. Louder, brighter, rougher and more constant as it rises."
    ),
    size_meaning="Not used.",
    styles={
        "steady": "Natural wind with moderate swells (default).",
        "gusty": "Strong, frequent gusts that rise and fall.",
        "howling": "Adds whistling, like wind through gaps or around a house.",
    },
    default_duration="8 seconds",
    render=render,
)
