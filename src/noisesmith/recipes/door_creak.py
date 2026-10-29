"""A door creaking open: a hinge that squeaks in short notes, with the wood crackling around it.

What a creak is NOT: a smooth gliding tone (that is a siren) or a string of uneven pulses
fed through vowel-like resonances (that is a human "creaky voice").

What it IS: as the door swings, the hinge sticks and then slips, and each slip sets a
metal or wooden part singing at one of its own fixed, inharmonic pitches. So the sound is
a series of separate squeak notes that hop between a few pitches, each note rough inside
(a fast, uneven flutter in volume) and rising a little as it goes. Around them the old
wood crackles with small dull knocks.

The sound is made of:
  * squeak notes at inharmonic pitches, each with a raspy flutter;
  * a breathy rub of friction noise that follows the squeaks;
  * crackling wood knocks.
"""

import numpy as np

from noisesmith.dsp.curves import bell, smooth_random
from noisesmith.dsp.filters import bandpass, lowpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe

# The pitches one hinge or door part can sing at, relative to its lowest. They are NOT
# whole-number multiples, which is what makes the sound metallic and woody, not musical.
SQUEAK_MODES = (1.0, 1.28, 1.63, 2.05)

# Extra partials inside every squeak (ratio to the note's pitch, loudness).
PARTIALS = ((1.0, 1.0), (1.47, 0.5), (2.31, 0.25), (3.2, 0.12))


def _squeak_note(seconds, f_start, f_end, rasp, sustained, sr, rng):
    """One squeak: a rough, inharmonic note that glides slightly and fades."""
    n = max(int(seconds * sr), 64)
    t = np.linspace(0.0, 1.0, n)
    freq = f_start * (f_end / f_start) ** t * (1 + 0.006 * smooth_random(n, 60, rng, sr, -1, 1))
    phase = 2 * np.pi * np.cumsum(freq) / sr
    tone = sum(gain * np.sin(ratio * phase + rng.uniform(0, 2 * np.pi)) for ratio, gain in PARTIALS)

    # The raspy part: a fast, uneven flutter in volume (80 to 240 times a second).
    flutter_rate = rng.uniform(80, 240) * (1 + 0.4 * smooth_random(n, 30, rng, sr, -1, 1))
    flutter = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(flutter_rate) / sr)
    flutter *= 0.6 + 0.4 * smooth_random(n, 400, rng, sr)  # a little extra randomness
    tone = tone * (1 - rasp * (1 - flutter))

    if sustained:  # horror: swells and trails off
        env = bell(n, rng.uniform(0.5, 0.75), 0.7)
    else:  # normal: quick start, then it dies away
        env = np.minimum(1.0, np.arange(n) / (0.008 * sr)) * np.exp(-2.2 * t)
    return tone * env


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    horror = p.style == "horror"
    duration = p.duration_s or ((5.5 + 2.0 * size) if horror else (2.8 + 2.2 * size))
    n = int(duration * sr)

    # When the door moves: one or two long strokes (horror) or a few short ones.
    strokes = max(1, round(duration / 5.0)) if horror else max(2, round(duration / 1.4))
    slot = n / strokes
    moving = np.zeros(n)
    rise = np.zeros(n)
    for k in range(strokes):
        start = int((k + rng.uniform(0.0, 0.1)) * slot)
        length = min(int(rng.uniform(0.8, 0.95 if horror else 0.8) * slot), n - start)
        if length < 16:
            continue
        swell = rng.uniform(0.7, 1.0) * bell(length, rng.uniform(0.6, 0.8) if horror else rng.uniform(0.4, 0.7), 0.6)
        moving[start : start + length] = np.maximum(moving[start : start + length], swell)
        rise[start : start + length] = np.linspace(0.0, 1.0, length)

    # How high the squeaks sing: a small door is high and thin, a heavy gate is low.
    base_hz = 750 * 2 ** (-1.4 * size)

    # Squeak notes, one after another inside each stroke.
    squeak = np.zeros(n + 2 * sr)
    t = 0
    mode = int(rng.integers(len(SQUEAK_MODES)))
    while t < n:
        if moving[t] > 0.05:
            # Hop to a neighbouring pitch most of the time, sometimes jump.
            mode = int(np.clip(mode + rng.choice([-1, 0, 1, 2, -2], p=[0.3, 0.1, 0.3, 0.15, 0.15]), 0, len(SQUEAK_MODES) - 1))
            seconds = rng.uniform(0.5, 1.4) if horror else rng.uniform(0.10, 0.28)
            f_start = base_hz * SQUEAK_MODES[mode] * rng.uniform(0.97, 1.03)
            climb = rng.uniform(1.15, 1.6) if horror else rng.uniform(1.02, 1.18)
            note = _squeak_note(seconds, f_start, f_start * climb, 0.5 + 0.45 * i, horror, sr, rng)
            squeak[t : t + len(note)] += note * moving[t] * rng.uniform(0.6, 1.0)
            t += int((seconds * (0.6 if horror else 0.5) + rng.uniform(0.05, 0.3 if horror else 0.22)) * sr)
        else:
            t += int(0.02 * sr)
    squeak = squeak[:n]
    squeak = squeak / (np.max(np.abs(squeak)) + 1e-12)

    # The rub of friction: a faint breathy noise that follows the squeaks.
    follow = np.abs(lowpass(squeak, 60, sr))
    rub = bandpass(white(n, rng), 1500, 5000, sr) * follow / (np.max(follow) + 1e-12) * (0.1 + 0.15 * i)

    # Old wood crackling: small dull knocks, more of them when the door is pushed harder.
    crackle = np.zeros(n + sr)
    knock_t = np.arange(int(0.15 * sr)) / sr
    spots =rng.integers(0, n, int((4 + 14 * i) * duration))
    for at in spots:
        if moving[at] > 0.1:
            pitch = rng.uniform(90, 330) * 2 ** (-0.6 * size)
            knock = np.exp(-knock_t / rng.uniform(0.012, 0.035)) * np.sin(2 * np.pi * pitch * knock_t + rng.uniform(0, 6.28))
            crackle[at : at + len(knock)] += knock * moving[at] * rng.uniform(0.3, 1.0) ** 2
    crackle = crackle[:n]
    crackle = crackle / (np.max(np.abs(crackle)) + 1e-12)

    sig = 0.8 * squeak + rub + (0.5 - 0.2 * i) * crackle
    sig = lowpass(sig, 3500 + 5000 * i, sr)
    sig = np.tanh(sig / (1.5 * np.percentile(np.abs(sig), 95) + 1e-12))  # even out loud spikes
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.02, fade_out_s=0.2)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut: separate hinge squeaks that hop between pitches, with crackling wood.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = soft, mostly clean squeaks, 0.5 = typical creaky door, "
        "1.0 = loud, very rough, raspy, screeching hinge with lots of crackle."
    ),
    size_meaning="Size and weight of the door. 0 = small cupboard (high, thin squeaks), 1 = huge heavy gate (low, deep squeaks).",
    styles={
        "creak": "A few short jerks, each a few quick squeaks, like opening a door in steps (default).",
        "horror": "One long, slow, drawn-out creak: long swelling squeaks that climb and trail off. Use for spooky, haunted, horror doors.",
    },
    default_duration="about 3 to 5 seconds for creak; about 5.5 to 7.5 seconds for horror",
    render=render,
)
