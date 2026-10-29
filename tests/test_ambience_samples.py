"""The recorded wind, rain and thunder: present, consistent, credited, and loopable."""

from pathlib import Path

import numpy as np
import pytest

from noisesmith import samples
from noisesmith.audio import SAMPLE_RATE
from noisesmith.dsp import loudness as loud

ASSETS = Path(samples.__file__).parent / "assets" / "ambience"
BEDS = samples.WIND_LIGHT + samples.WIND_STRONG + samples.WIND_HOWL + samples.RAIN_SOFT + samples.RAIN_HARD + samples.RAIN_HEAVY
ALL = BEDS + samples.THUNDER


def test_every_recording_is_listed_once_and_present():
    assert len(set(ALL)) == len(ALL)
    assert {p.stem for p in ASSETS.glob("*.ogg")} == set(ALL), "a recording is missing, or one is unused"


@pytest.mark.parametrize("clip_id", ALL)
def test_recording_is_mono_standard_rate_and_not_clipped(clip_id):
    audio = samples.load_ambience(clip_id)
    assert audio.ndim == 1 and audio.dtype == np.float64
    assert len(audio) / SAMPLE_RATE > 3
    assert 0.3 < np.max(np.abs(audio)) <= 1.0


@pytest.mark.parametrize("clip_id", BEDS)
def test_beds_share_a_loudness_and_have_a_natural_crest_factor(clip_id):
    audio = samples.load_ambience(clip_id)
    assert loud.lufs(audio, SAMPLE_RATE) == pytest.approx(-23.0, abs=1.0)
    crest = 20 * np.log10(np.max(np.abs(audio))) - loud.lufs(audio, SAMPLE_RATE)
    assert crest < 19, "one loud spike (a single raindrop?) would decide the level of a whole scene"
    assert len(audio) / SAMPLE_RATE > 30  # long enough that a loop does not repeat too soon


@pytest.mark.parametrize("clip_id", BEDS)
def test_beds_loop_without_a_seam(clip_id):
    loop = samples.seamless_bed(clip_id)
    typical = np.max(np.abs(np.diff(loop[:20000])))
    assert abs(loop[0] - loop[-1]) < 4 * typical
    wrapped = np.concatenate([loop[-300:], loop[:300]])
    assert np.max(np.abs(np.diff(wrapped))) < 2.5 * np.max(np.abs(np.diff(loop[SAMPLE_RATE : SAMPLE_RATE + 20000])))
    with pytest.raises(ValueError):
        loop[0] = 1.0  # read-only: a recipe cannot damage the shared copy


def test_thunder_peaks_are_kept():
    for clip_id in samples.THUNDER:
        assert 20 * np.log10(np.max(np.abs(samples.load_ambience(clip_id)))) == pytest.approx(-1.0, abs=1.5)


def test_every_recording_is_credited_as_cc0():
    credits = (ASSETS / "CREDITS.md").read_text(encoding="utf-8")
    assert "CC0" in credits and "Joseph Sardin" in credits and "bigsoundbank.com" in credits
    for clip_id in ALL:
        assert f"`{clip_id}`" in credits, f"{clip_id} is not credited"
