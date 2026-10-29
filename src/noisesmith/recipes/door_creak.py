"""A door creaking open: stick-slip friction in the hinges, ringing through wood."""

import numpy as np

from noisesmith.dsp.curves import bell, smooth_random
from noisesmith.dsp.filters import highpass, swept_bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    n = int((p.duration_s or 1.8 + 2.2 * size) * sr)

    # How fast the door is moving: it speeds up, wobbles a little, then slows down.
    speed = bell(n, rng.uniform(0.4, 0.65), 0.8) * (0.75 + 0.25 * smooth_random(n, 3, rng, sr))
    lower = 2 ** (-1.0 * size)  # a bigger, heavier door sounds lower

    # The hinge sticks and slips in little jerks. A faster door gives faster, more irregular jerks.
    wobble = 1 + 0.25 * (smooth_random(n, 9, rng, sr) - 0.5) * (0.4 + i)
    jerk_rate = (22 + 70 * speed) * lower * wobble
    ticks = np.flatnonzero(np.diff(np.floor(np.cumsum(jerk_rate / sr))) > 0)
    jerks = np.zeros(n)
    jerks[ticks] = rng.uniform(0.4, 1.0, len(ticks)) * speed[ticks]

    # Each jerk makes the wood ring at a few fixed "body" resonances.
    creak = np.zeros(n)
    for freq, q, gain in ((320, 7, 1.0), (900, 9, 0.8), (2100, 12, 0.5)):
        centre = (freq + 0.9 * freq * speed) * lower**0.5
        creak += gain * swept_bandpass(jerks, centre, q, sr)
    creak /= np.max(np.abs(creak)) + 1e-12

    # The squeal: a thin, wavering tone that cuts in and out as the hinge grips.
    squeal_amount = max(0.0, i - 0.15) ** 0.8
    squeal = np.zeros(n)
    if squeal_amount > 0:
        freq = (650 + 700 * speed + 120 * smooth_random(n, 11, rng, sr)) * 2 ** (-0.6 * size)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        tone = np.sin(phase) + 0.45 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)
        grip = np.clip((smooth_random(n, 5 + 8 * i, rng, sr) - 0.35) * 3, 0, 1)
        squeal = tone * speed**1.3 * grip
        squeal /= np.max(np.abs(squeal)) + 1e-12

    # A little scraping noise from the wood surfaces rubbing.
    scrape = highpass(white(n, rng), 1500, sr) * speed**2 * 0.04 * i

    sig = creak + 0.7 * squeal_amount * squeal + scrape
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.02, fade_out_s=0.15)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut: hinge friction and ringing wood.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = dry, soft wooden groan, 0.5 = typical creaky door, "
        "1.0 = loud, screeching, haunted-house hinge. Adds the high squeal as it rises."
    ),
    size_meaning="Size and weight of the door. 0 = small cupboard or cabinet, 1 = huge heavy gate.",
    styles={"creak": "One slow open or close (default)."},
    default_duration="about 2 to 4 seconds (longer for bigger doors)",
    render=render,
)
