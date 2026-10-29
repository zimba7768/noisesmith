"""Filters: keep or remove parts of the frequency range."""

import numpy as np
from scipy import signal


def _limit(freq, sr):
    """Keep a cutoff frequency inside the range a filter can handle."""
    return np.clip(freq, 10.0, sr * 0.48)


def lowpass(x, cutoff_hz, sr, order=2):
    """Let low frequencies through, cut the highs."""
    sos = signal.butter(order, _limit(cutoff_hz, sr), btype="lowpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def highpass(x, cutoff_hz, sr, order=2):
    """Let high frequencies through, cut the lows."""
    sos = signal.butter(order, _limit(cutoff_hz, sr), btype="highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def bandpass(x, low_hz, high_hz, sr, order=2):
    """Keep only the frequencies between low_hz and high_hz."""
    band = [_limit(low_hz, sr), _limit(high_hz, sr)]
    sos = signal.butter(order, band, btype="bandpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def swept_bandpass(x, center_hz, q, sr, block=128):
    """A resonant band-pass filter whose centre frequency moves over time.

    `center_hz` is an array with one frequency per sample (or one number). `q` sets how
    narrow the band is: about 0.7 is wide and airy, 10 or more is a narrow whistle.
    The filter is updated every `block` samples, carrying its state across blocks so the
    output stays smooth. The peak gain is 1, so narrow bands come out quiet.
    """
    n = len(x)
    center = np.broadcast_to(np.asarray(center_hz, dtype=float), (n,))
    q = np.broadcast_to(np.asarray(q, dtype=float), (n,))
    out = np.empty(n)
    state = np.zeros((1, 2))
    for start in range(0, n, block):
        end = min(start + block, n)
        mid = (start + end) // 2
        w0 = 2 * np.pi * float(np.clip(center[mid], 20.0, sr * 0.45)) / sr
        alpha = np.sin(w0) / (2 * max(float(q[mid]), 0.1))
        a0 = 1 + alpha
        sos = np.array([[alpha / a0, 0.0, -alpha / a0, 1.0, -2 * np.cos(w0) / a0, (1 - alpha) / a0]])
        out[start:end], state = signal.sosfilt(sos, x[start:end], zi=state)
    return out
