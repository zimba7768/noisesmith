"""Rain, from a gentle patter to a downpour, made from real field recordings (CC0).

Steady rain, hard drops on concrete and heavy summer-storm rain blend as it gets stronger.
See assets/ambience/CREDITS.md.
"""

import numpy as np

from noisesmith import samples
from noisesmith.dsp.filters import lowpass
from noisesmith.recipes._beds import bed, blend, deepened, finish
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    sr, rng, i = p.sr, p.rng, p.intensity
    n = int((p.duration_s or 10.0) * sr)
    used: list = []

    def pick(group):
        clip_id = group[int(rng.integers(len(group)))]
        used.append(clip_id)
        return clip_id

    soft, hard, heavy = blend(
        float(np.clip((0.6 - i) / 0.5, 0, 1)),  # gentle rain fades out as it strengthens
        float(np.clip(1 - abs(i - 0.5) / 0.4, 0, 1)),  # hard drops are strongest in the middle
        float(np.clip((i - 0.4) / 0.5, 0, 1)),  # heavy storm rain takes over at the top
    )
    sig = np.zeros(n)
    if soft > 0:
        sig += soft * bed(pick(samples.RAIN_SOFT), n, rng)
    if hard > 0:
        sig += hard * bed(pick(samples.RAIN_HARD), n, rng)
    if heavy > 0:
        sig += heavy * bed(pick(samples.RAIN_HEAVY), n, rng)
    if i > 0.85:  # a torrential downpour has a deeper roar
        sig += 0.5 * (i - 0.85) / 0.15 * deepened(pick(samples.RAIN_HEAVY), n, rng, 0.85)

    sig = lowpass(sig, 8000 + 4000 * i, sr)  # take the very top off light rain
    p.notes["recordings"] = sorted(set(used))
    return finish(sig, sr, -38 + 21 * i**0.8, fade_in_s=0.1, fade_out_s=0.25)  # about -35 LUFS for a patter, -17 for a downpour


RECIPE = Recipe(
    name="rain",
    summary="Rain falling, from a gentle patter to a heavy downpour, made from real recordings (CC0).",
    intensity_meaning=(
        "How hard it rains. 0.1 = gentle steady rain, 0.4 = steady rain, "
        "0.7 = heavy rain, 1.0 = torrential downpour with a deep roar. (There is no true drizzle recording.)"
    ),
    size_meaning="Not used.",
    styles={"rain": "Rain on open ground (default)."},
    default_duration="10 seconds",
    render=render,
)
