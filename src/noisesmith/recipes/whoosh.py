"""Whooshes: air rushing past something, from a quiet swish to a jet fly-by."""

import numpy as np

from noisesmith.dsp.curves import bell
from noisesmith.dsp.filters import lowpass, swept_bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import brown, pink, white
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    flyby = p.style == "flyby"
    swish = p.style == "swish"

    duration = p.duration_s or (0.45 + 0.9 * size) * (2.2 if flyby else 0.55 if swish else 1.0)
    n = int(duration * sr)
    peak_pos = 0.3 if flyby else 0.45 if swish else 0.4

    # The object passes: the sound swells to a peak and fades.
    hump = bell(n, peak_pos, 1.0)

    # The band of air noise sweeps up towards the peak and falls away again. Bigger = lower.
    low = 400 * 2 ** (-1.5 * size)
    high = 2500 * 2 ** (-1.2 * size) * (1 + 0.8 * i) * (1.8 if swish else 1.0)
    centre = low * (high / low) ** hump
    if flyby:  # pitch drops after passing, like a Doppler shift
        after = np.clip((np.linspace(0, 1, n) - peak_pos) / (1 - peak_pos), 0, 1)
        centre = centre * (1 - 0.55 * after**0.8)

    q = 2.0 - 1.3 * i  # gentle whooshes are focused, powerful ones are broad
    air = swept_bandpass(0.8 * pink(n, rng) + 0.2 * white(n, rng), centre, q, sr)
    air = air / (np.std(air) + 1e-12) * hump**1.5

    # Heavy objects also push a low body of air.
    body = lowpass(brown(n, rng, sr), 220, sr)
    body = body / (np.std(body) + 1e-12) * hump**2 * (0.3 * size + 0.2 * i)

    return finalize(air + body, sr, -20 + 17 * i, fade_in_s=0.005, fade_out_s=0.03)


RECIPE = Recipe(
    name="whoosh",
    summary="A swoosh of air as something passes by: a swish, a sword swing, a fly-by.",
    intensity_meaning=(
        "Power and speed. 0.1 = faint, delicate swish, 0.5 = clear whoosh, 1.0 = violent "
        "rush. Louder, broader and brighter as it rises."
    ),
    size_meaning="Size of the passing object. 0 = tiny and high (a wand), 1 = huge and deep (a truck).",
    styles={
        "whoosh": "A single pass with a rising then falling sweep (default).",
        "swish": "Short, thin and bright, like a quick hand or sword flick.",
        "flyby": "Long pass with the pitch dropping afterwards, like a jet or car going by.",
    },
    default_duration="about 0.5 to 1.4 seconds (swish shorter, flyby longer)",
    render=render,
)
