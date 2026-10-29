"""Regression: scenes must not go quiet where a layer ran out before the scene did.

A looped scene is rendered slightly longer than asked, to leave room for the crossfade at the
join. Layers exactly as long as the scene used to run out early, so every loop began (and the
crossfade blended in) a stretch of near silence: an audible 12 dB pulse once per loop.
"""

import numpy as np
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from noisesmith import audio, mixing, server
from noisesmith.audio import SAMPLE_RATE as SR

STORM = [
    {"recipe": "wind", "intensity": 0.9, "style": "gusty", "duration_s": 8, "gain_db": -3},
    {"recipe": "rain", "intensity": 0.75, "duration_s": 8, "gain_db": -6},
]


def half_second_levels_db(x):
    """Loudness of each half second, in dB relative to the median half second."""
    w = SR // 2
    rms = np.array([np.sqrt(np.mean(x[i : i + w] ** 2)) for i in range(0, len(x) - w + 1, w)])
    return 20 * np.log10(rms / np.median(rms))


def test_a_looped_scene_with_layers_as_long_as_the_scene_has_no_dip(tmp_path):
    info = server.mix_sounds(STORM, duration_s=8, loop=True, loop_crossfade_s=1.0, seed=3, output_dir=str(tmp_path))["files"][0]
    levels = half_second_levels_db(audio.read_audio(info["path"]))
    assert levels.min() > -4.0, f"a quiet patch of {levels.min():.1f} dB at half-second {levels.argmin()}"
    assert abs(levels[0] - levels[-1]) < 4.0  # the two sides of the join match


def test_the_same_holds_for_a_custom_generator_layer(tmp_path):
    layers = [{"generator": {"type": "noise", "color": "pink", "duration_s": 8}}]
    info = server.mix_sounds(layers, duration_s=8, loop=True, loop_crossfade_s=1.0, seed=3, output_dir=str(tmp_path))["files"][0]
    assert half_second_levels_db(audio.read_audio(info["path"])).min() > -4.0


def test_wind_and_rain_fill_the_whole_scene_when_no_length_is_given():
    x, _ = mixing.render_mix([{"recipe": "wind", "intensity": 0.5}, {"recipe": "rain", "intensity": 0.5}], 15.0, seed=1)
    levels = half_second_levels_db(x)[:-1]  # the very last half second holds the fade-out
    assert levels.min() > -6.0


def test_a_layer_given_a_shorter_length_is_left_alone():
    x, _ = mixing.render_mix([{"recipe": "wind", "intensity": 0.5, "duration_s": 3}], 10.0, seed=1)
    assert np.max(np.abs(x[int(3.5 * SR) :])) == 0


def test_a_repeating_layer_is_not_stretched():
    x, notes = mixing.render_mix([{"recipe": "impact", "style": "wood", "duration_s": 0.5, "repeat_every_s": 4.0}], 10.0, seed=1, requested_s=10.0)
    assert notes["layers"][0]["copies"] == 3
    assert np.max(np.abs(x[int(1.0 * SR) : int(3.9 * SR)])) == 0  # silence between the hits


def test_a_scene_longer_than_one_sound_can_hold_says_what_to_do(tmp_path):
    with pytest.raises(ToolError, match="repeat_every_s"):
        server.mix_sounds([{"recipe": "wind"}], duration_s=100, output_dir=str(tmp_path))
