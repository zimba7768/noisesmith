"""Checks that every recipe makes clean sound, repeats with a seed, and responds to its settings."""

import numpy as np
import pytest

from noisesmith.audio import SAMPLE_RATE
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
    assert 0.05 <= len(x) / SAMPLE_RATE <= 12


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


def test_wind_gets_louder_and_brighter_with_intensity():
    breeze, gale, hurricane = (make("wind", intensity=i, duration_s=6) for i in (0.1, 0.6, 1.0))
    assert measure(breeze)["rms_dbfs"] < measure(gale)["rms_dbfs"] < measure(hurricane)["rms_dbfs"]
    assert centroid(breeze) < centroid(gale) < centroid(hurricane)


@pytest.mark.parametrize("intensity", [0.1, 0.5, 1.0])
def test_wind_keeps_its_energy_in_the_lows_not_static_like(intensity):
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


# ---- door creak ------------------------------------------------------------------------------


def test_creak_gets_louder_with_intensity_and_lower_with_size():
    assert measure(make("door_creak", intensity=0.9, duration_s=3))["rms_dbfs"] > measure(
        make("door_creak", intensity=0.1, duration_s=3)
    )["rms_dbfs"]
    assert centroid(make("door_creak", size=1.0, duration_s=3)) < centroid(make("door_creak", size=0.0, duration_s=3))


def test_bigger_doors_last_longer_by_default():
    short = synth.generate("door_creak", intensity=0.5, size=0.0, duration_s=None, style="", seed=1)
    long = synth.generate("door_creak", intensity=0.5, size=1.0, duration_s=None, style="", seed=1)
    assert len(long) > len(short)


# ---- rain ------------------------------------------------------------------------------------


def test_rain_gets_louder_with_intensity():
    levels = [measure(make("rain", intensity=i, duration_s=4))["rms_dbfs"] for i in (0.1, 0.5, 1.0)]
    assert levels[0] < levels[1] < levels[2]


# ---- ui blips --------------------------------------------------------------------------------


@pytest.mark.parametrize("style", list(RECIPES["ui_blip"].styles))
def test_ui_blips_have_a_fixed_comfortable_level(style):
    assert abs(measure(make("ui_blip", style=style, duration_s=None))["peak_dbfs"] - (-6.0)) < 0.2


def test_ui_pitch_follows_size():
    assert centroid(make("ui_blip", size=0.0, style="beep")) > centroid(make("ui_blip", size=1.0, style="beep"))
