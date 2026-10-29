"""The recorded creaks: present, consistent, credited, and reshaped correctly."""

import wave
from pathlib import Path

import numpy as np
import pytest

from noisesmith import samples
from noisesmith.audio import SAMPLE_RATE

ASSETS = Path(samples.__file__).parent / "assets" / "creaks"
ALL_CLIPS = samples.DOOR_LONG + samples.DOOR_SHORT + samples.FLOOR


def test_every_clip_is_listed_once():
    assert len(set(ALL_CLIPS)) == len(ALL_CLIPS)
    on_disk = {p.stem for p in ASSETS.glob("*.wav")}
    assert on_disk == set(ALL_CLIPS), "a recording is missing, or one is unused"


@pytest.mark.parametrize("clip_id", ALL_CLIPS)
def test_clip_is_standard_and_levelled(clip_id):
    with wave.open(str(ASSETS / f"{clip_id}.wav"), "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, SAMPLE_RATE)
    audio = samples.load(clip_id)
    assert 0.3 < len(audio) / SAMPLE_RATE < 5
    assert abs(20 * np.log10(np.max(np.abs(audio))) - (-1.0)) < 0.2
    assert abs(audio[0]) < 0.02 and abs(audio[-1]) < 0.02


def test_every_clip_is_credited_as_cc0():
    credits = (ASSETS / "CREDITS.md").read_text(encoding="utf-8")
    assert "CC0" in credits
    for clip_id in ALL_CLIPS:
        assert f"`{clip_id}`" in credits, f"{clip_id} is not credited"
    for author in ("laleksic", "qubodup", "w.forster"):
        assert author in credits


def test_loaded_clips_cannot_be_changed_by_accident():
    with pytest.raises(ValueError):
        samples.load("door_open")[0] = 1.0


def test_varispeed_changes_length_and_pitch_the_right_way():
    clip = samples.load("hinge_spooky")
    assert len(samples.varispeed(clip, 2.0)) == pytest.approx(len(clip) / 2, abs=4)
    assert len(samples.varispeed(clip, 0.5)) == pytest.approx(len(clip) * 2, abs=4)
