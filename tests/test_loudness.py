import numpy as np
import pytest

from noisesmith.audio import SAMPLE_RATE as SR
from noisesmith.dsp import loudness as loud
from noisesmith.dsp.noise import pink


def noise(seconds=3.0, level=0.1, seed=1):
    return pink(int(seconds * SR), np.random.default_rng(seed)) * level


def test_targets_can_be_names_or_numbers():
    assert loud.parse_target("game") == -16.0
    assert loud.parse_target("WEB") == -14.0
    assert loud.parse_target("broadcast") == -23.0
    assert loud.parse_target("-18") == -18.0
    assert loud.parse_target(-20) == -20.0
    assert loud.parse_target(None) is None and loud.parse_target("none") is None
    for bad in ("loud", "-80", "5"):
        with pytest.raises(ValueError):
            loud.parse_target(bad)


def test_lufs_follows_gain_and_handles_silence_and_short_sounds():
    x = noise()
    assert loud.lufs(x * 2, SR) - loud.lufs(x, SR) == pytest.approx(6.02, abs=0.1)
    assert loud.lufs(np.zeros(SR), SR) == -70.0
    short = noise(0.1)  # shorter than one measuring block
    assert -60 < loud.lufs(short, SR) < 0


def test_match_loudness_reaches_the_target_without_passing_the_ceiling():
    for target in (-23.0, -16.0, -14.0):
        y, notes = loud.match_loudness(noise(), SR, target)
        assert notes["lufs"] == pytest.approx(target, abs=0.3)
        assert loud.true_peak_dbfs(y) <= loud.PEAK_CEILING_DBFS + 0.05
    # Quiet and moderate targets need no limiting at all.
    assert loud.match_loudness(noise(), SR, -23.0)[1]["limited"] is False
    assert loud.match_loudness(noise(), SR, -16.0)[1]["limited"] is False


def test_a_peaky_sound_is_limited_and_says_so():
    x = np.zeros(SR)
    x[::6000] = 0.9  # sharp clicks, very little energy
    y, notes = loud.match_loudness(x, SR, -16.0)
    assert notes["limited"] is True
    assert loud.true_peak_dbfs(y) <= loud.PEAK_CEILING_DBFS + 0.1
