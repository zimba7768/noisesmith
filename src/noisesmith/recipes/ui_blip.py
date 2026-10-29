"""Short interface and game sounds: beeps, clicks, coins, jumps, power-ups, lasers."""

import numpy as np

from noisesmith.dsp import oscillators
from noisesmith.dsp.curves import exp_decay
from noisesmith.dsp.filters import highpass
from noisesmith.dsp.levels import finalize
from noisesmith.dsp.noise import white
from noisesmith.recipes.base import Params, Recipe


def _note(f_start, f_end, seconds, wave, sr, percussive=False, vibrato=0.0):
    """One note that glides from f_start to f_end, with clean edges."""
    n = max(int(seconds * sr), 8)
    t = np.arange(n) / sr
    freq = f_start * (f_end / f_start) ** np.linspace(0, 1, n)
    if vibrato:
        freq = freq * (1 + vibrato * np.sin(2 * np.pi * 12 * t))
    release = max(0.008, 0.15 * seconds)
    env = np.minimum(1, t / 0.003) * np.minimum(1, (seconds - t) / release)
    if percussive:
        env = env * np.exp(-2.5 * t / seconds)
    return oscillators.wave(freq, wave, sr) * env


# Each style: a list of notes (start Hz, end Hz, seconds, percussive?) plus options.
STYLES = {
    "beep": ([(880, 880, 0.25, False)], "A plain, steady beep (default)."),
    "blip": ([(1200, 1800, 0.09, True)], "A short rising blip, like a menu selection."),
    "coin": ([(988, 988, 0.07, False), (1319, 1319, 0.28, True)], "A bright two-note pickup chime."),
    "jump": ([(250, 700, 0.22, False)], "A quick rising bounce."),
    "error": ([(311, 311, 0.13, False), (233, 233, 0.25, False)], "Two low, falling buzzes: something is wrong."),
    "success": (
        [(523, 523, 0.09, False), (659, 659, 0.09, False), (784, 784, 0.09, False), (1047, 1047, 0.32, True)],
        "Four rising notes: task complete.",
    ),
    "power_up": ([(200, 1600, 0.5, False)], "A rising, wobbling sweep."),
    "power_down": ([(1200, 120, 0.6, False)], "A falling sweep as something winds down."),
    "laser": ([(2400, 200, 0.25, False)], "A fast falling zap."),
    "click": ([], "A tiny button click."),
}


def render(p: Params) -> np.ndarray:
    sr, i = p.sr, p.intensity
    style = p.style or "beep"
    notes, _ = STYLES[style]
    pitch = 2 ** (1 - 2 * p.size)  # small = high, large = low
    wave = "sine" if i < 0.34 else "triangle" if i < 0.67 else "square"
    if style in ("laser", "error"):
        wave = "saw" if i >= 0.34 else "triangle"

    if style == "click":
        n = int((p.duration_s or 0.06) * sr)
        t = np.arange(n) / sr
        burst = highpass(white(n, p.rng), 1500, sr) * exp_decay(n, 0.0012, sr)
        thump = np.sin(2 * np.pi * 1500 * pitch * t) * exp_decay(n, 0.004, sr)
        sig = burst / (np.max(np.abs(burst)) + 1e-12) + 0.6 * thump
    else:
        default_total = sum(seconds for _, _, seconds, _ in notes)
        stretch = (p.duration_s / default_total) if p.duration_s else 1.0
        vibrato = 0.03 if style == "power_up" else 0.0
        sig = np.concatenate(
            [_note(f0 * pitch, f1 * pitch, seconds * stretch, wave, sr, percussive, vibrato) for f0, f1, seconds, percussive in notes]
        )
    return finalize(sig, sr, -6.0, fade_in_s=0.0005, fade_out_s=0.01)


RECIPE = Recipe(
    name="ui_blip",
    summary="Short interface and retro-game sounds: beeps, clicks, coins, jumps, power-ups, lasers.",
    intensity_meaning=(
        "Harshness of the tone, not loudness. Below 0.34 = soft sine, up to 0.67 = mellow "
        "triangle, above = buzzy square (saw for laser and error). Always saved at a "
        "fixed, comfortable loudness."
    ),
    size_meaning="Pitch. 0 = high and small, 0.5 = normal, 1 = low and large.",
    styles={name: spec[1] for name, spec in STYLES.items()},
    default_duration="chosen by style (0.06 to 0.6 seconds)",
    render=render,
)
