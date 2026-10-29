"""Layering: place several sounds on a timeline, each with its own volume, start and repeats.

A mix is a list of layers. A layer is a dictionary with exactly ONE source:

    {"recipe": "wind", "intensity": 1.0}                       a NoiseSmith recipe
    {"file": "sounds/thunder.wav"}                             an existing audio file
    {"generator": {"type": "noise", "color": "brown", ...}}    a custom sound (see generators.py)

and any of these placement settings:

    gain_db         volume change in decibels (default 0; -6 is half as loud, 6 is twice)
    start_s         when the first copy begins (default 0)
    length_s        use only this much of the sound
    fade_in_s, fade_out_s
    repeat_every_s  play again and again at this interval until the mix ends
    repeat_jitter   0..1: how unevenly the repeats are spaced (0.5 = up to a quarter interval early or late)
    repeat_count    stop after this many copies
    speed           playback speed: below 1 is lower and slower, above 1 higher and quicker
    speed_jitter    0..0.5: vary the speed of each repeat a little

A recipe layer also takes that recipe's own settings: intensity, size, style, duration_s, seed.
Each repeat of a recipe layer is made again with a new seed, so repeats are never identical.
"""

from pathlib import Path

import numpy as np

from noisesmith import audio, generators, samples
from noisesmith.dsp.levels import db_to_amp, fade
from noisesmith.engines import synth

SOURCE_KEYS = ("recipe", "file", "generator")
RECIPE_KEYS = {"intensity", "size", "style", "duration_s", "seed"}
PLACEMENT_KEYS = {
    "gain_db", "start_s", "length_s", "fade_in_s", "fade_out_s",
    "repeat_every_s", "repeat_jitter", "repeat_count", "speed", "speed_jitter",
}
MAX_LAYERS = 16
MAX_COPIES = 400  # across the whole mix
MAX_DURATION_S = 120.0


def _number(layer: dict, key: str, default, low: float, high: float):
    value = layer.get(key, default)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number, not {value!r}") from None
    if not low <= number <= high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return number


def render_mix(layers: list, duration_s: float, seed: int, sr: int = audio.SAMPLE_RATE):
    """Mix the layers into one sound of `duration_s` seconds. Returns (audio, notes)."""
    if not isinstance(layers, list) or not layers:
        raise ValueError("layers must be a non-empty list of layer dictionaries")
    if len(layers) > MAX_LAYERS:
        raise ValueError(f"A mix can have at most {MAX_LAYERS} layers")
    if not 0.1 <= duration_s <= MAX_DURATION_S:
        raise ValueError(f"duration_s must be between 0.1 and {MAX_DURATION_S} seconds")

    out = np.zeros(int(duration_s * sr))
    summary, copies = [], [0]
    for index, layer in enumerate(layers, start=1):
        try:
            summary.append(_add_layer(out, layer, index, seed, sr, copies))
        except (ValueError, TypeError, FileNotFoundError) as exc:
            raise ValueError(f"layer {index}: {exc}") from exc
    if np.max(np.abs(out)) < 1e-6:
        raise ValueError("The mix is silent. Check that each layer starts before the mix ends.")
    return out, {"layers": summary}


def _add_layer(out: np.ndarray, layer: dict, index: int, seed: int, sr: int, copies: list) -> dict:
    if not isinstance(layer, dict):
        raise ValueError("each layer must be a dictionary")
    sources = [key for key in SOURCE_KEYS if key in layer]
    if len(sources) != 1:
        raise ValueError(f"give exactly one source: {', '.join(SOURCE_KEYS)}")
    kind = sources[0]
    allowed = set(SOURCE_KEYS) | PLACEMENT_KEYS | (RECIPE_KEYS if kind == "recipe" else set())
    unknown = sorted(set(layer) - allowed)
    if unknown:
        raise ValueError(f"unknown setting(s) {', '.join(unknown)} for a {kind} layer. Allowed: {', '.join(sorted(allowed))}")

    gain = db_to_amp(_number(layer, "gain_db", 0.0, -60.0, 24.0))
    start = _number(layer, "start_s", 0.0, 0.0, MAX_DURATION_S)
    length = _number(layer, "length_s", None, 0.01, MAX_DURATION_S)
    fade_in = _number(layer, "fade_in_s", 0.0, 0.0, 60.0)
    fade_out = _number(layer, "fade_out_s", 0.0, 0.0, 60.0)
    every = _number(layer, "repeat_every_s", None, 0.05, MAX_DURATION_S)
    jitter = _number(layer, "repeat_jitter", 0.0, 0.0, 1.0)
    count = _number(layer, "repeat_count", None, 1, MAX_COPIES)
    speed = _number(layer, "speed", 1.0, 0.25, 4.0)
    speed_jitter = _number(layer, "speed_jitter", 0.0, 0.0, 0.5)
    rng = np.random.default_rng(seed + 7919 * index)
    base_seed = int(layer.get("seed", seed + 1000 * index))

    cached = None  # files and generators are loaded or built once, then reused for every repeat
    if kind == "file":
        cached = audio.read_audio(_expand(layer["file"]), sr)
    elif kind == "generator":
        cached = generators.render(layer["generator"], rng, sr)

    notes_recordings, placed, k = set(), 0, 0
    while True:
        at = start + (k * every if every else 0.0) + (rng.uniform(-0.5, 0.5) * jitter * every if every and k else 0.0)
        if at >= len(out) / sr or (count is not None and k >= count):
            break
        copies[0] += 1
        if copies[0] > MAX_COPIES:
            raise ValueError(f"the mix would need more than {MAX_COPIES} copies of sounds; use a longer repeat_every_s")

        if kind == "recipe":
            piece, notes = synth.generate_full(
                layer["recipe"],
                intensity=_number(layer, "intensity", 0.5, 0.0, 1.0),
                size=_number(layer, "size", 0.5, 0.0, 1.0),
                duration_s=_number(layer, "duration_s", None, synth.MIN_DURATION_S, synth.MAX_DURATION_S),
                style=layer.get("style", ""),
                seed=base_seed + k,
            )
            notes_recordings.update(notes.get("recordings", []))
        else:
            piece = cached
        this_speed = speed * (1 + speed_jitter * rng.uniform(-1, 1))
        if abs(this_speed - 1.0) > 1e-3:
            piece = samples.varispeed(piece, this_speed)
        if length is not None:
            piece = piece[: int(length * sr)]
        if fade_in or fade_out:
            piece = fade(piece, fade_in, fade_out, sr)

        pos = int(at * sr)
        end = min(len(out), pos + len(piece))
        out[pos:end] += piece[: end - pos] * gain
        placed += 1
        k += 1
        if not every:
            break

    summary = {"layer": index, "source": kind, "copies": placed}
    if kind == "recipe":
        summary["recipe"] = layer["recipe"]
        if notes_recordings:
            summary["recordings"] = sorted(notes_recordings)
    elif kind == "file":
        summary["file"] = str(layer["file"])
    else:
        summary["generator"] = layer["generator"].get("type") if isinstance(layer["generator"], dict) else None
    return summary


def _expand(path) -> Path:
    if not isinstance(path, str) or not path:
        raise ValueError("file must be a path to a sound file")
    return Path(path).expanduser()
