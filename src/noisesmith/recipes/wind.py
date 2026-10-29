"""Wind, from a faint breeze to a hurricane roar, made from real field recordings (CC0).

Light wind recordings carry the breeze end; strong wind in trees, leaves and storm gusts carries
the other end; the two blend smoothly in between. See assets/ambience/CREDITS.md.
"""

import numpy as np

from noisesmith import samples
from noisesmith.dsp.curves import smooth_random
from noisesmith.dsp.filters import lowpass
from noisesmith.recipes._beds import bed, blend, deepened, finish
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    sr, rng, i = p.sr, p.rng, p.intensity
    n = int((p.duration_s or 8.0) * sr)
    used: list = []

    def pick(group):
        clip_id = group[int(rng.integers(len(group)))]
        used.append(clip_id)
        return clip_id

    # A breeze is light-wind recordings, a gale is strong-wind recordings, and in between they blend.
    light, strong = blend(float(np.clip((0.65 - i) / 0.5, 0, 1)), float(np.clip((i - 0.2) / 0.5, 0, 1)))
    sig = np.zeros(n)
    if light > 0:
        sig += light * bed(pick(samples.WIND_LIGHT), n, rng)
    if strong > 0:
        sig += strong * bed(pick(samples.WIND_STRONG), n, rng)
    if i > 0.75:  # a hurricane has a deep roar underneath
        sig += 0.7 * (i - 0.75) / 0.25 * deepened(pick(samples.WIND_STRONG), n, rng, 0.8)

    # Whistling through gaps: always in "howling", and creeping in at hurricane strength.
    howl = 0.6 + 0.4 * i if p.style == "howling" else 0.4 * max(0.0, (i - 0.85) / 0.15)
    if howl > 0:
        sig += 0.5 * howl * bed(pick(samples.WIND_HOWL), n, rng)

    if p.style == "gusty":  # swell and fall in strong, frequent gusts
        sig *= 0.45 + 0.55 * smooth_random(n, 0.35, rng, sr)

    sig = lowpass(sig, 8000 + 4000 * i, sr)  # take the very top off a faint breeze; a gale keeps its edge
    p.notes["recordings"] = sorted(set(used))
    return finish(sig, sr, -36 + 19 * i**0.7, fade_in_s=0.15, fade_out_s=0.25)  # about -34 LUFS for a breeze, -17 for a hurricane


RECIPE = Recipe(
    name="wind",
    summary="Wind ambience, from a faint breeze to a screaming hurricane, made from real recordings (CC0).",
    intensity_meaning=(
        "Strength of the wind. 0.1 = gentle breeze, 0.3 = light wind, 0.6 = strong wind, "
        "0.8 = gale, 1.0 = hurricane. Louder, and heavier with more low rumble, as it rises."
    ),
    size_meaning="Not used.",
    styles={
        "steady": "Natural wind as recorded (default).",
        "gusty": "Strong, frequent gusts that rise and fall.",
        "howling": "Adds whistling, like wind through gaps or around a house.",
    },
    default_duration="8 seconds",
    render=render,
)
