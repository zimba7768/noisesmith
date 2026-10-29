"""Loudness: how loud a sound seems (LUFS), and matching a target for games, the web or broadcast.

LUFS is the standard unit for perceived loudness (ITU-R BS.1770). A sound at -16 LUFS seems
as loud as any other sound at -16 LUFS, which a plain peak level cannot tell you.
"""

import numpy as np
import pyloudnorm
from scipy import signal

from noisesmith.dsp.levels import amp_to_db, db_to_amp

# Common targets. Games and apps are often mixed around -16, web video around -14,
# and TV and broadcast use -23.
PRESETS = {"game": -16.0, "web": -14.0, "broadcast": -23.0}
PEAK_CEILING_DBFS = -1.0  # leave a little headroom so conversion to MP3/OGG cannot clip
_MIN_LUFS_SECONDS = 0.4  # the standard measures in 400 ms blocks


def parse_target(loudness: str | float | None) -> float | None:
    """Turn 'game', 'web', 'broadcast' or a number such as '-18' into a LUFS target."""
    if loudness in (None, "", "none"):
        return None
    if isinstance(loudness, str) and loudness.lower() in PRESETS:
        return PRESETS[loudness.lower()]
    try:
        target = float(loudness)
    except (TypeError, ValueError):
        raise ValueError(f"loudness must be one of {', '.join(PRESETS)}, none, or a number of LUFS such as -18") from None
    if not -40.0 <= target <= -5.0:
        raise ValueError("loudness must be between -40 and -5 LUFS")
    return target


def lufs(x: np.ndarray, sr: int) -> float:
    """Integrated loudness in LUFS. Very short sounds are repeated to fill one measuring block."""
    if len(x) == 0 or np.max(np.abs(x)) < 1e-9:
        return -70.0
    if len(x) < _MIN_LUFS_SECONDS * sr * 1.05:
        x = np.tile(x, int(np.ceil(_MIN_LUFS_SECONDS * sr * 1.05 / len(x))))
    value = pyloudnorm.Meter(sr).integrated_loudness(x)
    return float(value) if np.isfinite(value) else -70.0


def true_peak_dbfs(x: np.ndarray) -> float:
    """Highest level including the peaks between samples (estimated by 4x oversampling)."""
    return amp_to_db(np.max(np.abs(signal.resample_poly(x, 4, 1))))


def soft_limit(x: np.ndarray, ceiling_dbfs: float) -> np.ndarray:
    """Gently squash peaks above half the ceiling so nothing goes over it."""
    ceiling = db_to_amp(ceiling_dbfs)
    knee = 0.5 * ceiling
    mag = np.abs(x)
    squashed = knee + (ceiling - knee) * np.tanh((mag - knee) / (ceiling - knee))
    return np.where(mag > knee, np.sign(x) * squashed, x)


def match_loudness(x: np.ndarray, sr: int, target_lufs: float, ceiling_dbfs: float = PEAK_CEILING_DBFS):
    """Make `x` as loud as `target_lufs` without any peak going above the ceiling.

    A sound with tall, sharp peaks (a hit, a pop) cannot reach a high loudness without
    squashing those peaks. This limits them gently and says so in the returned notes. If even
    that cannot reach the target, the result is as loud as it can safely be.
    Returns (audio, notes) where notes has the final LUFS and whether limiting was needed.
    """
    inner_ceiling = ceiling_dbfs - 0.3  # margin for the peaks between samples
    gain_db = target_lufs - lufs(x, sr)
    y, limited, previous_error = x, False, None
    for _ in range(8):
        y = x * db_to_amp(gain_db)
        if true_peak_dbfs(y) > ceiling_dbfs:
            y = soft_limit(y, inner_ceiling)
            limited = True
        error = target_lufs - lufs(y, sr)
        if abs(error) < 0.1:
            break
        if previous_error is not None and abs(error) >= abs(previous_error) - 0.05:
            break  # more gain no longer helps: the limiter is holding the peaks down
        previous_error = error
        gain_db += error
    notes = {"loudness_target_lufs": target_lufs, "lufs": round(lufs(y, sr), 1), "limited": limited}
    return y, notes
