"""Seamless loops: a sound that can repeat forever with no click or jump at the join."""

import numpy as np


def make_seamless(x: np.ndarray, sr: int, crossfade_s: float = 1.0, trim_s: float = 0.0) -> np.ndarray:
    """Turn a sound into a loop. The result is shorter than the input by `crossfade_s` plus the trims.

    How it works: the last `crossfade_s` seconds are blended into the start. The end of the
    loop is then the original, untouched audio, and the start is a blend that begins exactly
    where the audio would have continued. Played end to end there is no discontinuity.
    `trim_s` is cut from both ends first, which removes any fade-in and fade-out baked into
    the sound.
    """
    region = x[int(trim_s * sr) : len(x) - int(trim_s * sr)] if trim_s > 0 else x
    fade = int(crossfade_s * sr)
    if fade < 16 or len(region) < 3 * fade:
        raise ValueError(
            f"The sound is too short to loop with a {crossfade_s} s crossfade. "
            "Use a longer sound or a shorter crossfade (the sound should be at least three times the crossfade)."
        )
    length = len(region) - fade
    loop = region[:length].copy()
    t = np.linspace(0.0, np.pi / 2, fade)
    # Equal-power blend: the two parts are different stretches of audio, so their powers add.
    loop[:fade] = region[:fade] * np.sin(t) + region[length : length + fade] * np.cos(t)
    return loop
