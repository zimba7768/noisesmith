"""Tones: sine, triangle, square and saw waves that follow a changing pitch."""

import numpy as np

WAVES = ("sine", "triangle", "square", "saw")


def wave(freq, shape, sr):
    """A tone that follows a per-sample frequency curve (in Hz).

    Square, saw and triangle are built from harmonics, so nothing above the Nyquist limit
    is ever generated. That avoids the harsh false tones a naive sawtooth produces.
    """
    phase = np.cumsum(freq) / sr  # in cycles
    if shape == "sine":
        return np.sin(2 * np.pi * phase)
    out = np.zeros(len(freq))
    if shape == "triangle":
        for h in range(1, 40, 2):
            out += (h * freq < sr * 0.45) * np.sin(2 * np.pi * h * phase) * (-1) ** ((h - 1) // 2) / h**2
    elif shape in ("square", "saw"):
        step = 2 if shape == "square" else 1
        for h in range(1, 40, step):
            out += (h * freq < sr * 0.45) * np.sin(2 * np.pi * h * phase) / h
    else:
        raise ValueError(f"Unknown wave {shape!r}. Choose from: {', '.join(WAVES)}")
    return out
