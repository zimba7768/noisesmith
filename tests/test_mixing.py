import numpy as np
import pytest

from noisesmith import audio, mixing
from noisesmith.audio import SAMPLE_RATE as SR
from noisesmith.dsp.levels import amp_to_db

TONE = {"generator": {"type": "tone", "freq_hz": 440, "duration_s": 0.5, "envelope": {"attack_s": 0.01, "release_s": 0.01}}}


def mix(layers, duration=4.0, seed=1):
    return mixing.render_mix(layers, duration, seed)


def loud_segments(x, floor=0.01):
    """Start and end (in seconds) of each stretch where the sound is audible."""
    envelope = np.convolve(np.abs(x), np.ones(480) / 480, mode="same")  # smooth over 10 ms so a wave's zero-crossings don't count
    on = envelope > floor * np.max(envelope)
    edges = np.flatnonzero(np.diff(on.astype(int)))
    return edges / SR


def test_gain_in_decibels_changes_the_level():
    loud = mix([TONE])[0]
    quiet = mix([{**TONE, "gain_db": -6}])[0]
    assert amp_to_db(np.max(np.abs(quiet))) - amp_to_db(np.max(np.abs(loud))) == pytest.approx(-6.0, abs=0.1)


def test_start_time_and_length_place_the_sound():
    x = mix([{**TONE, "start_s": 1.5, "length_s": 0.2}])[0]
    assert np.max(np.abs(x[: int(1.49 * SR)])) == 0
    assert np.max(np.abs(x[int(1.5 * SR) : int(1.7 * SR)])) > 0.1
    assert np.max(np.abs(x[int(1.75 * SR) :])) == 0


def test_repeats_fill_the_scene_and_jitter_spreads_them():
    steady, notes = mix([{**TONE, "repeat_every_s": 1.0}], duration=4.0)
    assert notes["layers"][0]["copies"] == 4
    starts = loud_segments(steady)[::2]
    assert np.allclose(np.diff(starts), 1.0, atol=0.05)
    jittered, _ = mix([{**TONE, "repeat_every_s": 1.0, "repeat_jitter": 1.0}], duration=6.0, seed=3)
    gaps = np.diff(loud_segments(jittered)[::2])
    assert gaps.std() > 0.05
    assert mix([{**TONE, "repeat_every_s": 1.0, "repeat_count": 2}])[1]["layers"][0]["copies"] == 2


def test_recipe_repeats_are_never_identical():
    x, notes = mix([{"recipe": "impact", "style": "wood", "start_s": 0.0, "repeat_every_s": 1.0}], duration=3.0)
    first, second = x[: SR // 2], x[SR : SR + SR // 2]
    assert not np.allclose(first, second)
    assert notes["layers"][0]["recipe"] == "impact"


def test_fades_and_speed():
    x = mix([{**TONE, "fade_in_s": 0.3, "fade_out_s": 0.1, "start_s": 1.0}])[0]
    assert np.max(np.abs(x[int(1.0 * SR) : int(1.05 * SR)])) < 0.3 * np.max(np.abs(x))
    slow = mix([{**TONE, "speed": 0.5}])[0]
    assert np.fft.rfftfreq(len(slow), 1 / SR)[np.argmax(np.abs(np.fft.rfft(slow)))] == pytest.approx(220, abs=8)
    assert loud_segments(slow)[-1] == pytest.approx(1.0, abs=0.05)  # half speed: twice as long


def test_file_layers_read_other_formats(tmp_path):
    source = mix([TONE])[0]
    for fmt in ("wav", "flac"):
        path = audio.write_audio(tmp_path / f"s.{fmt}", source / np.max(np.abs(source)) * 0.5)
        x, notes = mix([{"file": str(path), "start_s": 1.0}])
        assert notes["layers"][0]["source"] == "file"
        assert np.max(np.abs(x[: int(0.99 * SR)])) == 0 and np.max(np.abs(x)) > 0.3


def test_layers_add_up():
    one = mix([TONE])[0]
    two = mix([TONE, TONE])[0]
    assert np.allclose(two, 2 * one, atol=1e-6)


@pytest.mark.parametrize(
    "layers,message",
    [
        ([], "non-empty list"),
        ("wind", "non-empty list"),
        ([{}], "give exactly one source"),
        ([{"recipe": "wind", "file": "x.wav"}], "give exactly one source"),
        ([{"recipe": "wind", "gian_db": 3}], "unknown setting"),
        ([{"file": "x.wav", "intensity": 0.5}], "unknown setting"),
        ([{"recipe": "dog_bark"}], "Unknown recipe"),
        ([{"recipe": "wind", "gain_db": 99}], "gain_db must be between"),
        ([{"recipe": "wind", "repeat_every_s": 0.001}], "repeat_every_s"),
        ([{"file": "does_not_exist.wav"}], "No such sound file"),
        ([{"generator": {"type": "tone", "freqq": 1}}], "unknown field"),
        ([{"recipe": "wind", "start_s": 99}], "silent"),
    ],
)
def test_mistakes_get_clear_messages(layers, message):
    with pytest.raises(ValueError, match=message):
        mix(layers)


def test_too_many_copies_is_refused():
    layer = {"recipe": "ui_blip", "style": "click", "repeat_every_s": 0.05}
    with pytest.raises(ValueError, match="more than"):
        mix([layer], duration=60.0)


def test_error_messages_name_the_layer():
    with pytest.raises(ValueError, match="layer 2:"):
        mix([TONE, {"recipe": "nope"}])


def test_limits():
    with pytest.raises(ValueError, match="at most"):
        mix([TONE] * 17)
    with pytest.raises(ValueError, match="duration_s"):
        mix([TONE], duration=500)
