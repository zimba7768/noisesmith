"""Control curves: slow wandering values and shaped envelopes used to move other parameters."""

import numpy as np
from scipy.interpolate import PchipInterpolator


def smooth_random(n, rate_hz, rng, sr, low=0.0, high=1.0):
    """A smooth random curve that wanders between `low` and `high`.

    `rate_hz` is roughly how many new random targets it picks per second, so 0.2 gives slow
    swells (a gust every few seconds) and 8 gives quick flutter.
    """
    points = max(4, int(n / sr * rate_hz) + 3)
    targets = rng.random(points)
    positions = np.linspace(0, n - 1, points)
    curve = PchipInterpolator(positions, targets)(np.arange(n))  # smooth, never overshoots
    return low + (high - low) * curve


def bell(n, peak_pos=0.5, sharpness=1.0):
    """A hump that rises from 0 to 1 and back to 0. `peak_pos` (0..1) is where the top sits."""
    t = np.linspace(0.0, 1.0, n)
    u = np.where(t < peak_pos, 0.5 * t / peak_pos, 0.5 + 0.5 * (t - peak_pos) / (1 - peak_pos))
    return np.sin(np.pi * u) ** (2 * sharpness)


def exp_decay(n, tau_s, sr):
    """Starts at 1 and dies away; after `tau_s` seconds it has fallen to about 37%."""
    return np.exp(-np.arange(n) / (max(tau_s, 1e-4) * sr))
