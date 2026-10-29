"""Modal synthesis: a struck object is a handful of ringing tones that fade away."""

import numpy as np


def modal(freqs_hz, t60_s, amps, n, sr, rng):
    """Add up decaying sine waves, one per vibration mode of the object.

    `t60_s` is how long each mode takes to fade by 60 dB (to roughly silence).
    """
    t = np.arange(n) / sr
    out = np.zeros(n)
    for f, t60, a in zip(freqs_hz, t60_s, amps):
        if f >= sr * 0.45:  # above what we can represent
            continue
        out += a * np.exp(-6.91 * t / t60) * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    return out
