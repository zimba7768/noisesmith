"""A door creaking open: a hinge that sticks and slips in uneven little jerks.

A creak is not a held note. The hinge grips, then slips, then grips again, tens to a couple
of hundred times a second, and no two slips are alike. Each slip "kicks" the door and frame,
which ring at a few resonant pitches. As the door swings faster the slips come quicker and
the resonances rise, which is the rising squeal of a horror-movie door. Because the slips
are uneven and keep dropping out, it sounds rough and ratcheting instead of like a siren.

The sound is made of:
  * slip kicks (irregular pulses) rung through three rising resonances: the squeal;
  * the same kicks heard low and dull: the groan of the wood;
  * a little scraping noise.
"""

import numpy as np

from noisesmith.dsp.curves import bell, smooth_random
from noisesmith.dsp.filters import bandpass, lowpass, swept_bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe


def _peak_normalized(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    horror = p.style == "horror"
    duration = p.duration_s or ((5.5 + 2.0 * size) if horror else (2.8 + 2.2 * size))
    n = int(duration * sr)

    # When the door moves. A horror door is one or two long, slow strokes whose squeal
    # keeps climbing and trails off at the end; an ordinary creak is a few shorter jerks.
    strokes = max(1, round(duration / 5.0)) if horror else max(2, round(duration / 1.4))
    slot = n / strokes
    moving = np.zeros(n)  # how hard the door is being pushed (volume)
    rise = np.zeros(n)  # how far through the stroke we are (0..1): drives the climbing pitch
    for k in range(strokes):
        start = int((k + rng.uniform(0.0, 0.1)) * slot)
        length = min(int(rng.uniform(0.8, 0.95 if horror else 0.8) * slot), n - start)
        if length < 16:
            continue
        peak_at = rng.uniform(0.7, 0.8) if horror else rng.uniform(0.4, 0.7)
        swell = rng.uniform(0.7, 1.0) * bell(length, peak_at, 0.6)
        moving[start : start + length] = np.maximum(moving[start : start + length], swell)
        rise[start : start + length] = np.linspace(0.0, 1.0, length) ** 1.2

    # The hinge keeps catching and sputtering. More wear means more dropouts and more
    # irregular timing.
    sputter = np.clip((smooth_random(n, 9 + 10 * i, rng, sr) - 0.25) * 3, 0, 1)
    gate = 1 - 0.6 * i * (1 - sputter)
    irregularity = 0.15 + 0.3 * i

    # Place the slips one at a time. They speed up as the door swings faster, a heavier
    # door slips more slowly, and each one comes a little early or late and at a different
    # strength.
    lower = 2 ** (-0.8 * size)
    kicks = np.zeros(n)
    pos = 0.0
    while pos < n:
        at = int(pos)
        if moving[at] > 0.02:
            kicks[at] += moving[at] * gate[at] * rng.uniform(0.25, 1.0) ** 1.5
        slips_per_second = (30 + 150 * rise[at] ** 0.9) * lower
        pos += sr / slips_per_second * np.exp(rng.normal(0.0, irregularity))

    # The squeal: kicks ringing through three resonances (door, frame, hinge) that climb
    # as the door swings. A heavier door rings lower.
    form = 2 ** (-0.5 * size)
    body = np.zeros(n)
    for freq, climb, q, gain in ((450, 700, 12, 1.0), (1100, 1500, 14, 0.8), (2600, 1400, 16, 0.4)):
        body += gain * swept_bandpass(kicks, (freq + climb * rise) * form, q, sr)
    body = _peak_normalized(body)

    # The groan: the same kicks heard as slow, dull thumps from the wood.
    groan = _peak_normalized(lowpass(kicks, 250, sr))

    scrape = bandpass(white(n, rng), 2000, 6000, sr) * moving**2 * (0.03 + 0.07 * i)

    sig = 0.8 * body + (0.6 - 0.3 * i) * groan + scrape
    sig = lowpass(sig, 3500 + 5000 * i, sr)
    # A few slips are far louder than the rest. Squash those spikes so the whole creak is
    # heard clearly instead of one loud click and a quiet remainder.
    sig = np.tanh(sig / (1.5 * np.percentile(np.abs(sig), 95) + 1e-12))
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.02, fade_out_s=0.2)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut: uneven, ratcheting hinge slips with a rising squeal.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = soft, dry wooden groan, 0.5 = typical creaky door, "
        "1.0 = loud, rough, stuttering, screeching hinge."
    ),
    size_meaning="Size and weight of the door. 0 = small cupboard (higher, quicker), 1 = huge heavy gate (lower, slower).",
    styles={
        "creak": "A few short jerks, like opening a door in steps (default).",
        "horror": "One long, slow, drawn-out creak with a rising squeal that trails off. Use for spooky, haunted, horror doors.",
    },
    default_duration="about 3 to 5 seconds for creak; about 5.5 to 7.5 seconds for horror",
    render=render,
)
