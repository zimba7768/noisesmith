"""Noise generators. Each returns `n` samples with a standard deviation of about 1."""

import numpy as np

from noisesmith.dsp.filters import highpass


def white(n, rng):
    """Equal energy at every frequency: a bright hiss."""
    return rng.standard_normal(n)


def _shaped(n, rng, exponent):
    """Noise whose power falls off as 1 / frequency**exponent."""
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n)
    freqs[0] = freqs[1]  # avoid dividing by zero at 0 Hz
    spectrum *= freqs ** (-exponent / 2)
    spectrum[0] = 0.0  # no constant offset
    out = np.fft.irfft(spectrum, n)
    return out / (np.std(out) + 1e-12)


def pink(n, rng):
    """Power falls 3 dB per octave: sounds natural and balanced (rain, wind, surf)."""
    return _shaped(n, rng, 1.0)


def brown(n, rng, sr=48000):
    """Power falls 6 dB per octave: a deep rumble. Very slow drift is filtered out."""
    out = highpass(_shaped(n, rng, 2.0), 25, sr)
    return out / (np.std(out) + 1e-12)
