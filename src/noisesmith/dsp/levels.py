"""Loudness helpers: decibel maths, fades, normalising and measuring."""

import numpy as np


def db_to_amp(db):
    return 10.0 ** (db / 20.0)


def amp_to_db(amp):
    return 20.0 * np.log10(max(float(amp), 1e-9))


def normalize_peak(x, peak_dbfs):
    """Scale so the loudest sample sits at `peak_dbfs` (0 dBFS is the digital maximum)."""
    peak = np.max(np.abs(x))
    return x if peak == 0 else x * (db_to_amp(peak_dbfs) / peak)


def fade(x, fade_in_s, fade_out_s, sr):
    """Short linear fades at the start and end so the sound never clicks."""
    out = x.copy()
    n_in = min(int(fade_in_s * sr), len(out) // 2)
    n_out = min(int(fade_out_s * sr), len(out) // 2)
    if n_in > 0:
        out[:n_in] *= np.linspace(0.0, 1.0, n_in)
    if n_out > 0:
        out[-n_out:] *= np.linspace(1.0, 0.0, n_out)
    return out


def finalize(x, sr, peak_dbfs, fade_in_s=0.003, fade_out_s=0.02):
    """Standard last step for every recipe: remove DC offset, set the level, fade the edges."""
    x = x - np.mean(x)
    return normalize_peak(fade(x, fade_in_s, fade_out_s, sr), peak_dbfs)  # fade first: the peak is then exact


def measure(x):
    """Peak and RMS level in dBFS, for the notes file saved next to each sound."""
    return {
        "peak_dbfs": round(float(amp_to_db(np.max(np.abs(x)))), 1),
        "rms_dbfs": round(float(amp_to_db(np.sqrt(np.mean(np.square(x))))), 1),
    }
