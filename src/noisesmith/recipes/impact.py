"""One-off hits: an object struck once, from a tiny tap to a huge boom."""

import numpy as np

from noisesmith.dsp.curves import exp_decay
from noisesmith.dsp.filters import bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.modal import modal
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe

# Each material: (pitch of a small piece, pitch of a huge piece, ring ratios of the extra
# tones relative to the main one, ring time of a small piece in seconds, how fast loudness
# falls across the tones in dB per tone, description).
MATERIALS = {
    "wood": (900, 90, [1, 2.4, 4.1, 6.3, 9.0], 0.12, -6.0, "A dull knock or thud on wood (default)."),
    "metal": (1800, 140, [1, 1.58, 2.32, 4.25, 6.63, 9.38, 12.6], 1.2, -3.0, "A ringing clang on metal."),
    "glass": (3200, 400, [1, 1.01, 2.76, 2.79, 5.4, 8.9], 0.8, -2.0, "A bright, glassy clink."),
    "stone": (700, 70, [1, 1.9, 3.2, 5.1, 7.7], 0.09, -8.0, "A hard, dry knock on stone or concrete."),
}


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    material = p.style or "wood"
    high_hz, low_hz, ratios, ring, tilt_db, _ = MATERIALS[material]

    base = high_hz * (low_hz / high_hz) ** size  # bigger pieces ring lower
    t60_base = ring * (1 + (4 if material in ("wood", "stone") else 3) * size)
    n = int((p.duration_s or float(np.clip(1.6 * t60_base, 0.25, 5.0))) * sr)

    # A softer hit excites mostly the low tones; a harder hit rings brighter.
    tilt = tilt_db * (1.6 - 1.2 * i)
    freqs, t60s, amps = [], [], []
    for k, ratio in enumerate(ratios):
        freqs.append(base * ratio * rng.uniform(0.985, 1.015))
        t60s.append(t60_base / (1 + 0.6 * k))
        amps.append(10 ** (tilt * k / 20) * rng.uniform(0.6, 1.0))
    tones = modal(freqs, t60s, amps, n, sr, rng)
    tones /= np.max(np.abs(tones)) + 1e-12

    # The sharp "tick" at the instant of contact.
    tick = bandpass(white(n, rng), base * 1.5, 4000 + 8000 * i, sr)
    tick = tick * exp_decay(n, 0.0015 + 0.004 * size, sr)
    tick = tick / (np.max(np.abs(tick)) + 1e-12) * (0.3 + 0.9 * i)

    sig = tones + tick

    # Big hits have a deep thump underneath that drops in pitch.
    if size > 0.4:
        t = np.arange(n) / sr
        drop = 1 + 1.5 * np.exp(-t / 0.03)
        thump = np.sin(2 * np.pi * np.cumsum(base * 0.5 * drop) / sr) * exp_decay(n, 0.05 + 0.15 * size, sr)
        sig = sig + thump * size**1.5 * 0.8

    return finalize(sig, sr, -20 + 17 * i, fade_in_s=0.0005, fade_out_s=0.05)


RECIPE = Recipe(
    name="impact",
    summary="A single hit, knock, clang or boom on a material.",
    intensity_meaning=(
        "How hard the hit is. 0.1 = a soft tap, 0.5 = a normal hit, 1.0 = a hard smash. "
        "Louder and brighter as it rises."
    ),
    size_meaning=(
        "Size of the object. 0 = tiny (a coin or pebble), 0.5 = everyday object, "
        "1 = enormous (a boulder or a giant bell). Bigger means lower and longer ringing."
    ),
    styles={name: spec[5] for name, spec in MATERIALS.items()},
    default_duration="chosen automatically from the material and size (0.25 to 5 seconds)",
    render=render,
)
