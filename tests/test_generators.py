import numpy as np
import pytest

from noisesmith import generators
from noisesmith.audio import SAMPLE_RATE as SR
from noisesmith.dsp.levels import amp_to_db


def make(spec, seed=1):
    return generators.render(spec, np.random.default_rng(seed), SR)


def centroid(x):
    power = np.abs(np.fft.rfft(x)) ** 2
    return float(np.sum(np.fft.rfftfreq(len(x), 1 / SR) * power) / np.sum(power))


def test_noise_and_tone_are_levelled_and_repeatable():
    for spec in ({"type": "noise", "color": "pink"}, {"type": "tone", "freq_hz": 440}):
        x = make(spec)
        assert len(x) == SR
        assert amp_to_db(np.max(np.abs(x))) == pytest.approx(-6.0, abs=0.1)
        assert np.array_equal(x, make(spec))
    assert not np.array_equal(make({"type": "noise"}, 1), make({"type": "noise"}, 2))


def test_a_tone_has_the_pitch_asked_for_and_glides():
    steady = make({"type": "tone", "freq_hz": 1000, "duration_s": 1})
    spectrum = np.abs(np.fft.rfft(steady))
    assert np.fft.rfftfreq(len(steady), 1 / SR)[np.argmax(spectrum)] == pytest.approx(1000, abs=5)
    glide = make({"type": "tone", "freq_hz": {"from": 200, "to": 2000}, "duration_s": 1})
    assert centroid(glide[: SR // 4]) < centroid(glide[-SR // 4 :])


def test_colors_of_noise_get_darker():
    white, pink, brown = (centroid(make({"type": "noise", "color": c, "duration_s": 2})) for c in ("white", "pink", "brown"))
    assert white > pink > brown


def test_filters_shape_the_sound():
    base = {"type": "noise", "duration_s": 1}
    plain = centroid(make(base))
    low = centroid(make({**base, "filters": [{"type": "lowpass", "freq_hz": 500}]}))
    high = centroid(make({**base, "filters": [{"type": "highpass", "freq_hz": 5000}]}))
    band = centroid(make({**base, "filters": [{"type": "bandpass", "freq_hz": 1000, "q": 8}]}))
    assert low < plain < high
    assert band == pytest.approx(1000, rel=0.15)
    sweep = make({**base, "filters": [{"type": "bandpass", "freq_hz": {"from": 300, "to": 4000}, "q": 6}]})
    assert centroid(sweep[: SR // 4]) < centroid(sweep[-SR // 4 :])


def test_envelope_decay_and_fades():
    x = make({"type": "tone", "freq_hz": 300, "duration_s": 2, "envelope": {"attack_s": 0.01, "decay_s": 0.3}})
    assert np.sum(x[:SR] ** 2) > 20 * np.sum(x[SR:] ** 2)
    assert abs(x[0]) < 0.01 and abs(x[-1]) < 0.01


@pytest.mark.parametrize(
    "spec,message",
    [
        ({"type": "tone", "freqq": 5}, "unknown field"),
        ({"type": "laser"}, "must be 'noise' or 'tone'"),
        ({"type": "noise", "color": "blue"}, "color"),
        ({"type": "tone", "wave": "zigzag"}, "Unknown wave"),
        ({"type": "tone", "freq_hz": 5}, "between 20 and 20000"),
        ({"type": "tone", "duration_s": 500}, "duration_s"),
        ({"type": "noise", "filters": [{"type": "lowpass"}]}, "freq_hz is required"),
        ({"type": "noise", "filters": [{"type": "lowpass", "freq_hz": {"from": 100, "to": 900}}]}, "cannot glide"),
        ({"type": "noise", "filters": [{"type": "notch", "freq_hz": 100}]}, "lowpass, highpass or bandpass"),
        ({"type": "noise", "envelope": {"attak_s": 1}}, "unknown field"),
        ("noise", "dictionary"),
    ],
)
def test_bad_specs_explain_what_is_wrong(spec, message):
    with pytest.raises(ValueError, match=message):
        make(spec)
