import wave

import numpy as np

from noisesmith import audio, server


def test_safe_name_blocks_path_tricks():
    assert audio.safe_name("../../evil name!") == "evil_name"
    assert audio.safe_name("???") == "sound"


def test_beep_is_not_silent_and_does_not_clip():
    samples = audio.beep(440, 0.2)
    assert np.max(np.abs(samples)) > 0.3
    assert np.max(np.abs(samples)) <= 1.0
    assert abs(samples[0]) < 0.01 and abs(samples[-1]) < 0.01  # faded, so no click


def test_make_beep_writes_valid_wav(tmp_path):
    result = server.make_beep(name="test beep", output_dir=str(tmp_path))
    with wave.open(result, "rb") as f:
        assert f.getframerate() == audio.SAMPLE_RATE
        assert f.getnchannels() == 1
        assert f.getnframes() == int(audio.SAMPLE_RATE * 0.3)
    assert result.endswith("test_beep.wav")
