"""Thunder, from a distant rumble to a close crack, made from real recordings (CC0)."""

import numpy as np

from noisesmith import samples
from noisesmith.dsp.filters import lowpass
from noisesmith.dsp.levels import finalize
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    clip_id = samples.THUNDER[int(rng.integers(len(samples.THUNDER)))]
    speed = 2 ** (-0.9 * (size - 0.5)) * rng.uniform(0.95, 1.05)  # bigger storms: lower and slower
    x = samples.varispeed(samples.load_ambience(clip_id), speed)

    # Distance: far-away thunder has lost its high frequencies and is quiet.
    x = lowpass(x, 700 + 11000 * i**1.5, sr)

    if p.duration_s:  # cut, or leave silence after the thunder, to exactly the length asked
        want = int(p.duration_s * sr)
        x = x[:want] if len(x) >= want else np.pad(x, (0, want - len(x)))
    p.notes["recordings"] = [clip_id]
    return finalize(x, sr, -20 + 19 * i, fade_in_s=0.005, fade_out_s=0.3)


RECIPE = Recipe(
    name="thunder",
    summary="A clap or roll of thunder, from far-off rumble to a close crack, made from real recordings (CC0).",
    intensity_meaning=(
        "How close and violent. 0.1 = faint, distant rumble; 0.5 = clear thunder in the next valley; "
        "1.0 = a loud, sharp crack overhead."
    ),
    size_meaning="Size of the storm. 0 = short, higher and quicker; 1 = long, deep and rolling.",
    styles={"thunder": "A single clap or roll of thunder (default). Different seeds give different thunder."},
    default_duration="about 3 to 50 seconds, depending on the recording chosen and the size",
    render=render,
)
