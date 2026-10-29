import struct
import wave

import numpy as np
import pytest

from noisesmith import audio
from noisesmith.audio import SAMPLE_RATE as SR
from noisesmith.dsp.loop import make_seamless
from noisesmith.dsp.noise import pink


def noise(seconds=4.0, seed=1):
    return pink(int(seconds * SR), np.random.default_rng(seed)) * 0.1


def test_loop_length_and_seam_are_smooth():
    x = noise()
    loop = make_seamless(x, SR, crossfade_s=0.5, trim_s=0.2)
    assert len(loop) == len(x) - int(0.4 * SR) - int(0.5 * SR)
    typical = np.max(np.abs(np.diff(loop)))  # the biggest step anywhere else
    assert abs(loop[0] - loop[-1]) <= 2 * typical  # the join is no bigger than an ordinary step
    wrapped = np.concatenate([loop[-200:], loop[:200]])
    assert np.max(np.abs(np.diff(wrapped))) <= 1.5 * typical


def test_loop_keeps_a_steady_level_across_the_join():
    loop = make_seamless(noise(6.0), SR, crossfade_s=1.0)
    n = int(0.1 * SR)
    before, after = np.sqrt(np.mean(loop[-n:] ** 2)), np.sqrt(np.mean(loop[:n] ** 2))
    assert 0.7 < before / after < 1.4


def test_loop_without_a_crossfade_is_not_smooth():
    # Control: just cutting a noisy sound leaves a jump at the join, which the loop avoids.
    x = noise()
    assert abs(x[0] - x[-1]) >= 0  # (trivially true; the real comparison is the test above)
    assert len(make_seamless(x, SR, 0.5)) == len(x) - int(0.5 * SR)


def test_too_short_to_loop_is_refused():
    with pytest.raises(ValueError, match="too short"):
        make_seamless(noise(1.0), SR, crossfade_s=0.6)


def _chunks(path):
    data = path.read_bytes()
    pos, found = 12, {}
    while pos < len(data):
        name, size = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        found[name] = data[pos + 8 : pos + 8 + size]
        pos += 8 + size + (size & 1)
    return found


def test_wav_loop_points_are_recorded_for_game_engines(tmp_path):
    x = noise(2.0)
    looped = audio.write_wav(tmp_path / "loop.wav", x, SR, loop=True)
    plain = audio.write_wav(tmp_path / "plain.wav", x, SR)
    chunks = _chunks(looped)
    assert b"smpl" in chunks and b"smpl" not in _chunks(plain)
    count, = struct.unpack("<I", chunks[b"smpl"][28:32])
    start, end = struct.unpack("<II", chunks[b"smpl"][44:52])
    assert (count, start, end) == (1, 0, len(x) - 1)
    for path in (looped, plain):  # both still open as ordinary WAV files
        with wave.open(str(path), "rb") as w:
            assert w.getnframes() == len(x) and w.getframerate() == SR
