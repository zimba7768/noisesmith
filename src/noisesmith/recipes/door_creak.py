"""A door creaking open: a hinge sticking and slipping in uneven jerks.

This recipe was rebuilt from measurements of a real recorded creak (a CC0 recording,
studied for its numbers only; no audio from it is used). What a real creak turned out to be:

  * Not separate tonal squeaks and not a smooth gliding tone (those sound like a synthesizer
    or a siren), and not a voice (that needs narrow vowel-like resonances; a door has none).
  * A stream of sharp slips, very irregular in timing and strength (almost random). They
    start fast, around 150 a second, and slow down to about 45 a second. Near the end they
    are slow enough to hear as separate clicks, like a ratchet.
  * A broad, flat spectrum from the lows up to about 4 kHz, then a smooth roll-off, with
    only mild bumps from door and frame resonances.
  * A big pop as the door breaks free, and a slow wavering in volume 3 to 6 times a second.
"""

import numpy as np

from noisesmith.dsp.curves import bell, smooth_random
from noisesmith.dsp.filters import highpass, lowpass, resonator
from noisesmith.dsp.levels import finalize
from noisesmith.recipes.base import Params, Recipe

# Mild resonances measured in a real creak (Hz) and how strongly each shows.
BUMPS = ((540, 0.4), (880, 0.5), (1680, 0.9), (2300, 1.0), (3250, 1.0))


def _peak_normalized(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def render(p: Params) -> np.ndarray:
    sr, rng, i, size = p.sr, p.rng, p.intensity, p.size
    horror = p.style == "horror"
    duration = p.duration_s or ((5.5 + 2.0 * size) if horror else (2.8 + 2.2 * size))
    n = int(duration * sr)

    # When the door moves: one or two long strokes (horror), or a few shorter ones. For each
    # stroke, `progress` runs 0 to 1 from the moment the door breaks free until it stops.
    strokes = max(1, round(duration / 5.0)) if horror else max(2, round(duration / 1.4))
    slot = n / strokes
    moving = np.zeros(n)
    progress = np.zeros(n)
    starts = []
    for k in range(strokes):
        start = int((k + rng.uniform(0.0, 0.1)) * slot)
        length = min(int(rng.uniform(0.8, 0.95 if horror else 0.85) * slot), n - start)
        if length < 16:
            continue
        starts.append(start)
        swell = rng.uniform(0.75, 1.0) * np.maximum(bell(length, 0.35, 0.35), 0.35)  # keep it audible to the end
        moving[start : start + length] = np.maximum(moving[start : start + length], swell)
        progress[start : start + length] = np.linspace(0.0, 1.0, length)

    # How fast the hinge slips: about 150 a second at first, easing to about 45, then
    # slowing to a few a second so each slip is heard on its own. A heavier door is slower.
    lower = 2 ** (-0.6 * size)
    early = 150 * (45 / 150) ** (progress / 0.7)
    late = 45 * (6 / 45) ** (np.clip((progress - 0.7) / 0.3, 0, 1) ** 1.3)
    rate = np.where(progress < 0.7, early, late) * lower * smooth_random(n, 3, rng, sr, 0.8, 1.25)

    # The door's volume wavers slowly as the push varies.
    waver = 1 + 0.7 * (smooth_random(n, 4, rng, sr) - 0.5)

    # Place the slips one by one. Timing and strength are very uneven. Slow slips are bigger
    # (the hinge moved further before letting go), and the first slip is a big pop.
    irregular = 0.25 + 0.25 * i
    kicks = np.zeros(n)
    pending_pop = set(starts)
    pos = 0.0
    while pos < n:
        at = int(pos)
        if moving[at] > 0.02:
            strength = moving[at] * waver[at] * rng.lognormal(0.0, 0.6) * min((100 / rate[at]) ** 0.8, 4.0)
            if any(s <= at < s + int(0.05 * sr) for s in pending_pop):
                strength *= 5.0
                pending_pop = {s for s in pending_pop if not s <= at < s + int(0.05 * sr)}
            kicks[at] += strength
        # Each wait is a bit early or late, but never so long that the buzz falls silent.
        pos += sr / max(rate[at], 3.0) * float(np.clip(np.exp(rng.normal(0.0, irregular)), 0.35, 2.0))

    # Shape the slips into the creak's tone: broad and flat, rolling off above about 4 kHz
    # (darker for a bigger door), plus mild resonances and a little low thump.
    form = 2 ** (-0.5 * size)
    broad = _peak_normalized(lowpass(highpass(kicks, 220, sr), 9000 * form, sr, order=3))
    rings = _peak_normalized(sum(g * resonator(kicks, f * form * rng.uniform(0.94, 1.06), 9, sr) for f, g in BUMPS))
    sig = 0.7 * broad + (0.3 + 0.25 * i) * rings

    sig = np.tanh(sig / (3.0 * np.percentile(np.abs(sig), 95) + 1e-12))  # tame the biggest pops
    return finalize(sig, sr, -16 + 12 * i, fade_in_s=0.002, fade_out_s=0.2)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut: a rough stream of uneven hinge slips that slows to a ratchet.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = soft, fairly even groan, 0.5 = typical creaky door, "
        "1.0 = loud, very uneven, rough and stuttering."
    ),
    size_meaning="Size and weight of the door. 0 = small cupboard (quicker, brighter), 1 = huge heavy gate (slower, darker).",
    styles={
        "creak": "A few short jerks, each easing into a ratchet, like opening a door in steps (default).",
        "horror": "One long, slow, drawn-out creak that eases into a slow ratchet at the end. Use for spooky, haunted, horror doors.",
    },
    default_duration="about 3 to 5 seconds for creak; about 5.5 to 7.5 seconds for horror",
    render=render,
)
