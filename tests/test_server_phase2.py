"""The Phase 2 tools: loops, formats, loudness, mixing, exporting."""

import json
import struct
import wave
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from mcp.server.mcpserver.exceptions import ToolError

from noisesmith import audio, server
from noisesmith.audio import SAMPLE_RATE as SR


def read_chunks(path):
    data = Path(path).read_bytes()
    pos, found = 12, {}
    while pos < len(data):
        name, size = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        found[name] = data[pos + 8 : pos + 8 + size]
        pos += 8 + size + (size & 1)
    return found


def notes_of(path):
    return json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))


def test_a_looped_recipe_has_the_requested_length_and_loop_points(tmp_path):
    info = server.create_sound("wind", duration_s=4, loop=True, loop_crossfade_s=0.5, seed=2, output_dir=str(tmp_path))["files"][0]
    assert info["loop"] is True and info["duration_s"] == 4.0
    with wave.open(info["path"], "rb") as w:
        assert w.getnframes() == 4 * SR
    assert b"smpl" in read_chunks(info["path"])
    notes = notes_of(info["path"])
    assert notes["loop"] is True and notes["loop_crossfade_s"] == 0.5


def test_loop_defaults_and_limits(tmp_path):
    info = server.create_sound("rain", loop=True, output_dir=str(tmp_path), seed=1)["files"][0]
    assert info["duration_s"] == 10.0
    with pytest.raises(ToolError, match="too short"):
        server.create_sound("wind", duration_s=1.5, loop=True, output_dir=str(tmp_path))


@pytest.mark.parametrize("fmt", ["flac", "ogg", "mp3"])
def test_other_formats_are_real_files_of_the_right_length(tmp_path, fmt):
    info = server.create_sound("rain", duration_s=2, format=fmt, seed=1, output_dir=str(tmp_path))["files"][0]
    assert info["path"].endswith(f".{fmt}") and info["format"] == fmt
    assert abs(len(audio.read_audio(Path(info["path"]))) - 2 * SR) < 2500
    assert notes_of(info["path"])["format"] == fmt


def test_loudness_presets_hit_their_targets(tmp_path):
    for preset, target in (("game", -16.0), ("web", -14.0), ("broadcast", -23.0), (-20, -20.0)):
        info = server.create_sound("rain", intensity=0.5, duration_s=3, loudness=preset, seed=1, output_dir=str(tmp_path))["files"][0]
        assert info["lufs"] == pytest.approx(target, abs=0.3)
        assert info["peak_dbfs"] <= -0.9


def test_a_recipe_keeps_its_natural_level_without_a_loudness_target(tmp_path):
    info = server.create_sound("wind", intensity=0.1, duration_s=3, seed=1, output_dir=str(tmp_path))["files"][0]
    assert info["lufs"] == pytest.approx(-36 + 19 * 0.1**0.7, abs=0.7)  # a breeze is quiet; ambience is set by loudness
    assert "loudness_target_lufs" not in info


STORM = [
    {"recipe": "wind", "intensity": 0.9, "style": "gusty", "duration_s": 6, "gain_db": -3},
    {"recipe": "rain", "intensity": 0.8, "duration_s": 6, "gain_db": -6},
    {"recipe": "impact", "style": "stone", "size": 1.0, "gain_db": -12, "start_s": 1, "repeat_every_s": 2, "repeat_jitter": 0.4},
]


def test_a_mix_is_saved_with_a_description_of_its_layers(tmp_path):
    result = server.mix_sounds(STORM, duration_s=6, name="storm", description="a storm", seed=4, output_dir=str(tmp_path))
    info = result["files"][0]
    assert Path(info["path"]).name == "storm.wav" and info["duration_s"] == 6.0
    assert [(layer["source"], layer["copies"]) for layer in result["layers"]] == [("recipe", 1), ("recipe", 1), ("recipe", 3)]
    notes = notes_of(info["path"])
    assert notes["engine"] == "mix" and notes["output_license"] == "CC0-1.0" and notes["layers"][2]["copies"] == 3
    assert notes["description"] == "a storm" and notes["seed"] == 4
    assert info["peak_dbfs"] <= -0.9


def test_a_mix_that_is_too_loud_is_turned_down_not_clipped(tmp_path):
    loud_layers = [{"recipe": "wind", "intensity": 1.0, "duration_s": 3, "gain_db": 12}] * 2
    result = server.mix_sounds(loud_layers, duration_s=3, output_dir=str(tmp_path), seed=1)
    assert result["files"][0]["peak_dbfs"] == pytest.approx(-1.0, abs=0.1)
    assert notes_of(result["files"][0]["path"])["turned_down_db"] > 0


def test_mixes_are_repeatable_and_can_loop_and_match_loudness(tmp_path):
    a = server.mix_sounds(STORM, duration_s=6, seed=7, output_dir=str(tmp_path))["files"][0]["path"]
    b = server.mix_sounds(STORM, duration_s=6, seed=7, output_dir=str(tmp_path))["files"][0]["path"]
    assert Path(a).read_bytes() == Path(b).read_bytes()
    looped = server.mix_sounds(STORM[:2], duration_s=5, loop=True, loop_crossfade_s=0.5, loudness="game", seed=7, output_dir=str(tmp_path))["files"][0]
    assert looped["loop"] is True and looped["duration_s"] == 5.0 and looped["lufs"] == pytest.approx(-16.0, abs=0.3)


def test_a_mix_with_a_file_layer_says_the_license_depends_on_the_file(tmp_path):
    source = Path(server.create_sound("impact", duration_s=1, seed=1, output_dir=str(tmp_path))["files"][0]["path"])
    result = server.mix_sounds([{"file": str(source)}, {"recipe": "rain", "duration_s": 2}], duration_s=2, seed=1, output_dir=str(tmp_path))
    assert "depends on the licenses" in result["license"]


def test_mix_errors_reach_claude_with_the_layer_number(tmp_path):
    with pytest.raises(ToolError, match="layer 1: unknown setting"):
        server.mix_sounds([{"recipe": "wind", "gian_db": 3}], duration_s=3, output_dir=str(tmp_path))
    with pytest.raises(ToolError, match="Unknown format"):
        server.mix_sounds(STORM, duration_s=3, format="aac", output_dir=str(tmp_path))


def test_export_converts_format_loudness_rate_and_trims(tmp_path):
    source = Path(server.create_sound("impact", style="wood", duration_s=2, seed=1, output_dir=str(tmp_path))["files"][0]["path"])
    original_bytes = source.read_bytes()
    result = server.export_sound(
        str(source), format="ogg", loudness="web", sample_rate=44100, trim_silence=True, fade_out_s=0.05, name="hit_web", output_dir=str(tmp_path)
    )
    info = result["files"][0]
    assert info["path"].endswith("hit_web.ogg") and info["lufs"] == pytest.approx(-14.0, abs=0.5)
    assert sf.info(info["path"]).samplerate == 44100
    assert info["duration_s"] < 2.0  # trailing silence was removed
    assert result["license"] == "CC0-1.0"  # inherited from the source file's notes
    assert source.read_bytes() == original_bytes  # the original is untouched


def test_export_of_a_foreign_file_does_not_claim_a_license(tmp_path):
    foreign = audio.write_wav(tmp_path / "someone_elses.wav", np.sin(np.arange(SR) * 0.05) * 0.3)
    result = server.export_sound(str(foreign), format="flac", output_dir=str(tmp_path / "out"))
    assert result["license"].startswith("unknown")


def test_make_loop_from_a_file(tmp_path):
    source = server.create_sound("rain", duration_s=6, seed=1, output_dir=str(tmp_path))["files"][0]["path"]
    info = server.make_loop(source, crossfade_s=1.0, trim_s=0.3, output_dir=str(tmp_path))["files"][0]
    assert info["loop"] is True and info["duration_s"] == pytest.approx(6 - 0.6 - 1.0, abs=0.01)
    assert b"smpl" in read_chunks(info["path"])
    with pytest.raises(ToolError, match="too short"):
        server.make_loop(source, crossfade_s=3.0, trim_s=0.3, output_dir=str(tmp_path))


def test_export_and_loop_errors_are_clear(tmp_path):
    with pytest.raises(ToolError, match="No such sound file"):
        server.export_sound(str(tmp_path / "nope.wav"), output_dir=str(tmp_path))
    with pytest.raises(ToolError, match="sample_rate"):
        server.export_sound(str(tmp_path / "nope.wav"), sample_rate=5, output_dir=str(tmp_path))
    with pytest.raises(ToolError, match="loudness must be"):
        server.create_sound("wind", loudness="quiet", output_dir=str(tmp_path))
