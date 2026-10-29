"""Checks that every recipe makes clean sound, repeats with a seed, and responds to its settings."""

import numpy as np
import pytest

from noisesmith.audio import SAMPLE_RATE
from noisesmith.dsp import loudness as loud
from noisesmith.dsp.levels import measure
from noisesmith.engines import synth
from noisesmith.recipes import RECIPES

ALL_CASES = [(name, style) for name, r in RECIPES.items() for style in r.styles]


def make(recipe, intensity=0.5, size=0.5, duration_s=1.5, style="", seed=1):
    return synth.generate(recipe, intensity=intensity, size=size, duration_s=duration_s, style=style, seed=seed)


def centroid(x):
    """Where the 'centre of mass' of the spectrum sits, in Hz. Higher means brighter."""
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)
    return float(np.sum(freqs * power) / np.sum(power))


def band_energy(x, low, high):
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)
    return float(np.sum(power[(freqs >= low) & (freqs < high)]))


# ---- every recipe and style ----------------------------------------------------------------


@pytest.mark.parametrize("recipe,style", ALL_CASES)
def test_output_is_clean(recipe, style):
    x = make(recipe, style=style)
    assert np.all(np.isfinite(x))
    assert np.max(np.abs(x)) <= 1.0
    assert measure(x)["peak_dbfs"] > -40, "sound is silent"
    assert abs(np.mean(x)) < 0.01 * np.max(np.abs(x)) + 1e-4, "DC offset"
    assert abs(x[0]) < 0.02 and abs(x[-1]) < 0.02, "edges should fade so there is no click"
    assert abs(len(x) - int(1.5 * SAMPLE_RATE)) <= 64


@pytest.mark.parametrize("recipe,style", ALL_CASES)
def test_same_seed_repeats_exactly(recipe, style):
    assert np.array_equal(make(recipe, style=style, seed=7), make(recipe, style=style, seed=7))


@pytest.mark.parametrize("recipe", [r for r in RECIPES if r != "ui_blip"])
def test_different_seeds_differ(recipe):
    assert not np.array_equal(make(recipe, seed=1), make(recipe, seed=2))


@pytest.mark.parametrize("recipe", list(RECIPES))
def test_default_duration_is_reasonable(recipe):
    x = synth.generate(recipe, intensity=0.5, size=0.5, duration_s=None, style="", seed=1)
    longest = 60 if recipe == "thunder" else 12  # thunder can roll on for half a minute
    assert 0.05 <= len(x) / SAMPLE_RATE <= longest


def test_bad_arguments_are_rejected():
    with pytest.raises(ValueError, match="Unknown recipe"):
        make("dog_bark")
    with pytest.raises(ValueError, match="intensity"):
        make("wind", intensity=1.5)
    with pytest.raises(ValueError, match="size"):
        make("wind", size=-0.1)
    with pytest.raises(ValueError, match="style"):
        make("wind", style="tornado")
    with pytest.raises(ValueError, match="duration_s"):
        make("wind", duration_s=500)


# ---- wind: breeze to hurricane ---------------------------------------------------------------


def test_wind_gets_louder_and_heavier_with_intensity():
    breeze, gale, hurricane = (make("wind", intensity=i, duration_s=6) for i in (0.1, 0.6, 1.0))
    levels = [loud.lufs(x, SAMPLE_RATE) for x in (breeze, gale, hurricane)]
    assert levels[0] + 4 < levels[1] < levels[2] - 2
    # Real strong wind is a deep rumble; a breeze is a light hiss. So it gets lower, not brighter.
    assert centroid(gale) < centroid(breeze)


def test_gusty_wind_swells_more_than_steady_wind():
    def swing(style):
        x = make("wind", intensity=0.7, duration_s=20, style=style, seed=2)
        w = SAMPLE_RATE // 2
        db = [20 * np.log10(np.sqrt(np.mean(x[i : i + w] ** 2)) + 1e-9) for i in range(SAMPLE_RATE, len(x) - w, w)]
        return max(db) - min(db)

    assert swing("gusty") > swing("steady")


def test_howling_wind_uses_the_whistling_recording():
    _, notes = synth.generate_full("wind", intensity=0.5, size=0.5, duration_s=3, style="howling", seed=1)
    assert "wind_whistle_chimney" in notes["recordings"]
    _, plain = synth.generate_full("wind", intensity=0.5, size=0.5, duration_s=3, style="steady", seed=1)
    assert "wind_whistle_chimney" not in plain["recordings"]


@pytest.mark.parametrize("intensity", [0.5, 1.0])
def test_strong_wind_keeps_its_energy_in_the_lows_not_static_like(intensity):  # (a breeze is a light hiss, and that is right)
    x = make("wind", intensity=intensity, duration_s=6)
    assert band_energy(x, 4000, 20000) < 0.2 * band_energy(x, 20, 1000)


# ---- impacts ---------------------------------------------------------------------------------


@pytest.mark.parametrize("style", list(RECIPES["impact"].styles))
def test_bigger_objects_sound_lower(style):
    small = make("impact", size=0.0, style=style, duration_s=2)
    large = make("impact", size=1.0, style=style, duration_s=2)
    assert centroid(large) < centroid(small)


def test_metal_rings_longer_than_wood_and_stone():
    def late_energy_fraction(style):
        x = make("impact", style=style, duration_s=3)
        return float(np.sum(x[SAMPLE_RATE:] ** 2) / np.sum(x**2))

    assert late_energy_fraction("metal") > 5 * late_energy_fraction("wood")
    assert late_energy_fraction("metal") > 5 * late_energy_fraction("stone")


def test_harder_hits_are_louder_and_brighter():
    soft, hard = make("impact", intensity=0.1, duration_s=1), make("impact", intensity=1.0, duration_s=1)
    assert measure(hard)["rms_dbfs"] > measure(soft)["rms_dbfs"]
    assert centroid(hard) > centroid(soft)


# ---- whoosh ----------------------------------------------------------------------------------


def test_whoosh_size_and_style():
    assert centroid(make("whoosh", size=1.0)) < centroid(make("whoosh", size=0.0))
    default, flyby, swish = (
        synth.generate("whoosh", intensity=0.5, size=0.5, duration_s=None, style=s, seed=1) for s in ("", "flyby", "swish")
    )
    assert len(swish) < len(default) < len(flyby)


# ---- creaks (recording-based) ----------------------------------------------------------------


@pytest.mark.parametrize("recipe", ["door_creak", "floor_creak"])
def test_creaks_get_louder_with_intensity_and_lower_with_size(recipe):
    assert measure(make(recipe, intensity=0.9, duration_s=3))["rms_dbfs"] > measure(make(recipe, intensity=0.1, duration_s=3))["rms_dbfs"]

    # The choice of recording is random, so compare the average over several seeds.
    def average_centroid(size):
        return np.mean([centroid(make(recipe, size=size, duration_s=3, seed=s)) for s in range(1, 7)])

    assert average_centroid(1.0) < average_centroid(0.0)


@pytest.mark.parametrize("recipe", ["door_creak", "floor_creak"])
def test_bigger_things_last_longer_by_default(recipe):
    def average_length(size):
        return np.mean([len(synth.generate(recipe, intensity=0.5, size=size, duration_s=None, style="", seed=s)) for s in range(1, 9)])

    assert average_length(1.0) > average_length(0.0)


def test_long_styles_are_longer_than_the_default():
    for recipe, style in (("door_creak", "horror"), ("floor_creak", "long")):
        long = synth.generate(recipe, intensity=0.5, size=0.5, duration_s=None, style=style, seed=1)
        short = synth.generate(recipe, intensity=0.5, size=0.5, duration_s=None, style="", seed=1)
        assert len(long) > len(short)


def test_creak_notes_list_the_recordings_used():
    _, notes = synth.generate_full("door_creak", intensity=0.5, size=0.5, duration_s=2, style="", seed=2)
    assert notes["recordings"] and all(isinstance(c, str) for c in notes["recordings"])
    _, no_notes = synth.generate_full("impact", intensity=0.5, size=0.5, duration_s=1, style="", seed=2)
    assert no_notes == {}  # synthesized sounds use no recordings


# ---- rain ------------------------------------------------------------------------------------


def test_rain_gets_louder_with_intensity():
    levels = [loud.lufs(make("rain", intensity=i, duration_s=6), SAMPLE_RATE) for i in (0.1, 0.5, 1.0)]
    assert levels[0] + 4 < levels[1] < levels[2] - 2


# ---- thunder ---------------------------------------------------------------------------------


def test_thunder_gets_louder_brighter_and_longer_with_intensity_and_size():
    def averages(**settings):
        xs = [synth.generate("thunder", **{"intensity": 0.5, "size": 0.5, "duration_s": None, "style": "", **settings, "seed": s}) for s in range(1, 9)]
        return np.mean([centroid(x) for x in xs]), np.mean([len(x) for x in xs]), np.mean([measure(x)["peak_dbfs"] for x in xs])

    far, close = averages(intensity=0.1), averages(intensity=0.9)
    assert far[0] < close[0] and far[2] < close[2] - 8  # distant thunder is duller and much quieter
    small, big = averages(size=0.0), averages(size=1.0)
    assert big[1] > 1.3 * small[1]  # a bigger storm rolls on for longer
    assert centroid(synth.generate("thunder", intensity=0.5, size=1.0, duration_s=None, style="", seed=3)) < centroid(
        synth.generate("thunder", intensity=0.5, size=0.0, duration_s=None, style="", seed=3)
    )


def test_thunder_variations_use_different_recordings():
    used = {tuple(synth.generate_full("thunder", intensity=0.5, size=0.5, duration_s=None, style="", seed=s)[1]["recordings"]) for s in range(1, 25)}
    assert len(used) >= 5


def test_thunder_can_be_given_an_exact_length():
    assert len(make("thunder", duration_s=2.0)) == 2 * SAMPLE_RATE
    assert len(make("thunder", duration_s=30.0)) == 30 * SAMPLE_RATE


# ---- ui blips --------------------------------------------------------------------------------


@pytest.mark.parametrize("style", list(RECIPES["ui_blip"].styles))
def test_ui_blips_have_a_fixed_comfortable_level(style):
    assert abs(measure(make("ui_blip", style=style, duration_s=None))["peak_dbfs"] - (-6.0)) < 0.2


def test_ui_pitch_follows_size():
    assert centroid(make("ui_blip", size=0.0, style="beep")) > centroid(make("ui_blip", size=1.0, style="beep"))
