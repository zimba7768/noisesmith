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


# ---- reading and writing every format --------------------------------------------------------

import pytest

from noisesmith.dsp.noise import pink


@pytest.mark.parametrize("fmt", audio.FORMATS)
def test_every_format_round_trips(tmp_path, fmt):
    x = pink(audio.SAMPLE_RATE * 2, np.random.default_rng(1)) * 0.1
    path = audio.write_audio(tmp_path / f"t.{fmt}", x)
    back = audio.read_audio(path)
    assert abs(len(back) - len(x)) < 2500  # lossy formats add a little padding
    n = min(len(back), len(x))
    if fmt in ("wav", "flac"):  # lossless (to 16 bits)
        assert np.max(np.abs(back[:n] - x[:n])) < 1e-3
    else:
        assert np.corrcoef(back[2000 : n - 2000], x[2000 : n - 2000])[0, 1] > 0.9


@pytest.mark.parametrize("fmt", audio.FORMATS)
def test_a_long_sound_can_be_saved_in_every_format(tmp_path, fmt):
    # Regression: a single big write once crashed the OGG encoder (stack overflow) beyond ~10 s.
    x = pink(audio.SAMPLE_RATE * 40, np.random.default_rng(3)) * 0.1
    path = audio.write_audio(tmp_path / f"long.{fmt}", x)
    assert abs(len(audio.read_audio(path)) - len(x)) < 4000


def test_reading_resamples_to_the_standard_rate(tmp_path):
    import soundfile as sf

    t = np.arange(44100) / 44100
    sf.write(str(tmp_path / "a.wav"), 0.3 * np.sin(2 * np.pi * 440 * t), 44100)
    back = audio.read_audio(tmp_path / "a.wav")
    assert len(back) == pytest.approx(audio.SAMPLE_RATE, abs=4)


def test_bad_inputs_give_clear_errors(tmp_path):
    with pytest.raises(ValueError, match="Unknown format"):
        audio.check_format("aac")
    with pytest.raises(FileNotFoundError, match="No such sound file"):
        audio.read_audio(tmp_path / "missing.wav")
    (tmp_path / "junk.wav").write_bytes(b"not audio at all")
    with pytest.raises(ValueError, match="Could not read"):
        audio.read_audio(tmp_path / "junk.wav")
