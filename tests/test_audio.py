import wave

import numpy as np

from noisesmith import audio


def test_safe_name_blocks_path_tricks():
    assert audio.safe_name("../../evil name!") == "evil_name"
    assert audio.safe_name("???") == "sound"


def test_unique_path_never_overwrites(tmp_path):
    first = audio.unique_path(tmp_path, "boom")
    first.write_bytes(b"x")
    second = audio.unique_path(tmp_path, "boom")
    assert second != first and second.name == "boom-2.wav"


def test_write_wav_is_valid_and_clips_safely(tmp_path):
    path = audio.write_wav(tmp_path / "t.wav", np.array([0.0, 0.5, 5.0, -5.0]))
    with wave.open(str(path), "rb") as f:
        assert f.getframerate() == audio.SAMPLE_RATE
        assert f.getnchannels() == 1
        assert f.getsampwidth() == 2
        assert f.getnframes() == 4
