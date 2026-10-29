import json
import tomllib
import wave
from pathlib import Path

import pytest

from mcp.server.mcpserver.exceptions import ToolError

from noisesmith import __version__, audio, server

ROOT = Path(__file__).resolve().parent.parent


def test_list_recipes_describes_every_recipe():
    recipes = {r["recipe"]: r for r in server.list_recipes()}
    assert set(recipes) == {"wind", "whoosh", "door_creak", "floor_creak", "thunder", "impact", "rain", "ui_blip"}
    for r in recipes.values():
        assert r["summary"] and r["intensity"] and r["size"] and r["styles"]


def test_create_sound_writes_wav_and_notes(tmp_path):
    result = server.create_sound(
        "wind", intensity=0.1, duration_s=1, seed=5, description="a slight breeze", output_dir=str(tmp_path)
    )
    (info,) = result["files"]
    wav = Path(info["path"])
    assert wav.name == "wind.wav"
    with wave.open(str(wav), "rb") as f:
        assert f.getframerate() == audio.SAMPLE_RATE
        assert f.getnframes() == audio.SAMPLE_RATE
    notes = json.loads(wav.with_suffix(".json").read_text(encoding="utf-8"))
    assert notes["recipe"] == "wind" and notes["seed"] == 5
    assert notes["description"] == "a slight breeze"
    assert notes["engine"] == "builtin" and notes["output_license"] == "CC0-1.0"
    assert notes["settings"]["intensity"] == 0.1


def test_variations_are_different_files_with_different_seeds(tmp_path):
    result = server.create_sound("rain", duration_s=1, variations=3, seed=10, output_dir=str(tmp_path))
    paths = [Path(f["path"]) for f in result["files"]]
    assert [p.name for p in paths] == ["rain_01.wav", "rain_02.wav", "rain_03.wav"]
    assert [f["seed"] for f in result["files"]] == [10, 11, 12]
    assert len({p.read_bytes() for p in paths}) == 3


def test_same_seed_gives_identical_file_and_old_files_are_kept(tmp_path):
    a = server.create_sound("impact", style="metal", seed=3, duration_s=1, output_dir=str(tmp_path))["files"][0]["path"]
    b = server.create_sound("impact", style="metal", seed=3, duration_s=1, output_dir=str(tmp_path))["files"][0]["path"]
    assert a != b and Path(a).read_bytes() == Path(b).read_bytes()


def test_name_is_made_safe(tmp_path):
    path = server.create_sound("ui_blip", style="coin", name="../../bad name", output_dir=str(tmp_path))["files"][0]["path"]
    assert Path(path).parent == tmp_path and Path(path).name == "bad_name.wav"


def test_bad_requests_raise_clear_errors(tmp_path):
    with pytest.raises(ToolError, match="Unknown recipe.*wind, whoosh"):
        server.create_sound("dog_bark", output_dir=str(tmp_path))
    with pytest.raises(ToolError, match="variations"):
        server.create_sound("wind", variations=0, output_dir=str(tmp_path))
    with pytest.raises(ToolError, match="variations"):
        server.create_sound("wind", variations=99, output_dir=str(tmp_path))


def test_versions_agree_everywhere():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    plugin = json.loads((ROOT / "plugin" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    extension = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))["version"]
    assert __version__ == pyproject == plugin == extension


def test_notes_for_a_creak_say_which_recordings_were_used(tmp_path):
    info = server.create_sound("door_creak", duration_s=2, seed=4, output_dir=str(tmp_path))["files"][0]
    notes = json.loads(Path(info["path"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert notes["recordings"] and notes["output_license"] == "CC0-1.0"
