"""A door creaking open: a hinge that sticks and slips, squealing as it goes.

The sound has three parts, like a bowed string made of metal and wood:
  * a squeal: a rough, pitched buzz (stick-slip friction) that glides up and down,
    colored by the resonances of the door and frame;
  * a groan: the same friction an octave or two lower, from the wood itself;
  * a little scraping noise.
A door does not creak continuously. It moves in a few separate jerks, so the sound
comes in several strokes with quiet gaps between.
"""

import numpy as np

from noisesmith.dsp.curves import bell, smooth_random
from noisesmith.dsp.filters import bandpass, lowpass, swept_bandpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe


def _buzz(freq, sr, max_hz=7000.0, harmonics=40, rolloff=1.0):
    """A bright, buzzy tone (a sawtooth) that follows a per-sample frequency curve.

    Built from harmonics so nothing above `max_hz` is ever generated, which avoids the
    harsh false tones that come from a naive sawtooth.
    """
    phase = 2 * np.pi * np.cumsum(freq) / sr
    out = np.zeros(len(freq))
    for h in range(1, harmonics + 1):
        allowed = h * freq < max_hz
        if not allowed.any():
            break
        out += allowed * np.sin(h * phase) / h**rolloff
    return out


def _peak_normalized(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    duration = p.duration_s or 1.8 + 2.2 * size
    n = int(duration * sr)

    # When the door is moving: a few separate strokes, each swelling and fading.
    strokes = max(2, round(duration / 0.9))
    slot = n / strokes
    moving = np.zeros(n)
    for k in range(strokes):
        start = int((k + rng.uniform(0.0, 0.2)) * slot)
        length = min(int(rng.uniform(0.45, 0.85) * slot), n - start)
        swell = rng.uniform(0.6, 1.0) * bell(length, rng.uniform(0.3, 0.6), 0.7)
        moving[start : start + length] = np.maximum(moving[start : start + length], swell)

    # The pitch of the squeal: a heavier door is lower. It wanders, and rises while the
    # door is moving faster. Roughness (random pitch wobble) grows with wear.
    base_hz = 700 * 2 ** (-1.8 * size)
    wander = smooth_random(n, 1.2, rng, sr, -0.3, 0.3)  # in octaves
    roughness = 0.012 + 0.05 * i
    wobble = smooth_random(n, 140, rng, sr, -1.0, 1.0) * roughness
    pitch = base_hz * 2 ** (wander + 0.35 * moving) * (1 + wobble)

    # The squeal: a gritty buzz that trembles in volume and gets harsher with wear.
    flutter = 1 + 0.35 * (smooth_random(n, 28, rng, sr) - 0.5) * (0.5 + i)
    squeal = np.tanh((1.0 + 2.0 * i) * _peak_normalized(_buzz(pitch, sr)))  # harsher with wear
    squeal = squeal * moving * flutter  # shape the volume afterwards so each stroke keeps its swell

    # The door and frame ring at a few resonances, which move a little as it swings.
    # This is what turns a plain buzz into something that sounds like wood and metal.
    lean = 0.5 * moving + 0.5 * (wander + 0.3) / 0.6
    body = np.zeros(n)
    for freq, q, gain in ((500, 5, 1.0), (1250, 7, 0.8), (2400, 9, 0.5)):
        centre = freq * (0.8 + 0.5 * lean) * 2 ** (-0.5 * size)
        body += gain * swept_bandpass(squeal, centre, q, sr)
    body = _peak_normalized(body)

    # The groan: friction in the wood itself, much lower and rougher. Softer, older-wood
    # doors (low intensity) are mostly groan.
    groan = lowpass(_buzz(pitch * 0.25 * (1 + 3 * wobble), sr, max_hz=1500, rolloff=1.3), 800, sr)
    groan = _peak_normalized(groan * moving**0.8)

    scrape = bandpass(white(n, rng), 2000, 6000, sr) * moving**2 * (0.04 + 0.08 * i)

    sig = 0.5 * body + 0.3 * squeal + (0.5 - 0.3 * i) * groan + scrape
    sig = lowpass(sig, 2500 + 6000 * i, sr)
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.02, fade_out_s=0.15)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut: a squealing hinge and groaning wood, in a few jerks.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = dry, soft wooden groan, 0.5 = typical creaky door, "
        "1.0 = loud, rough, screeching haunted-house hinge."
    ),
    size_meaning="Size and weight of the door. 0 = small cupboard (high squeak), 1 = huge heavy gate (low groan).",
    styles={"creak": "One slow open or close (default)."},
    default_duration="about 2 to 4 seconds (longer for bigger doors)",
    render=render,
)
