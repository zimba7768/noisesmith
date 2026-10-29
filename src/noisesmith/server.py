"""The NoiseSmith MCP server: the tools Claude can call to make sounds."""

import functools
import json
import secrets
from fractions import Fraction
from pathlib import Path

import numpy as np
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from scipy import signal

from noisesmith import audio, metadata, mixing, preview
from noisesmith.dsp import loop as looping
from noisesmith.dsp import loudness as loud
from noisesmith.dsp.levels import amp_to_db, db_to_amp, fade, measure, normalize_peak
from noisesmith.engines import synth
from noisesmith.recipes import RECIPES

mcp = MCPServer("noisesmith")

MAX_VARIATIONS = 20
LOOP_TRIM_S = 0.4  # cut from both ends of a looped sound to drop any fade-in and fade-out
DEFAULT_LOOP_S = 10.0
MIX_PEAK_DBFS = -1.0  # a mix is turned down (never up) if its layers add up louder than this


def friendly_errors(func):
    """Show Claude the real reason a request failed (e.g. "Unknown recipe...") instead of a
    generic "Error executing tool", so it can correct itself or explain to the user."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, OSError, RuntimeError) as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


# ---- shared steps ----------------------------------------------------------------------------


def _make_loop(samples: np.ndarray, crossfade_s: float, trim_s: float) -> np.ndarray:
    return looping.make_seamless(samples, audio.SAMPLE_RATE, crossfade_s, trim_s)


def _check_loop_args(duration: float, crossfade_s: float) -> None:
    if not 0.05 <= crossfade_s <= 10:
        raise ValueError("loop_crossfade_s must be between 0.05 and 10 seconds")
    if duration < 2 * crossfade_s:
        raise ValueError(f"A loop of {duration:g} s is too short for a {crossfade_s:g} s crossfade; use a longer duration or a shorter crossfade")


def _save(samples: np.ndarray, folder: Path, stem: str, *, fmt: str, loop: bool, target_lufs: float | None, record: dict) -> dict:
    """Apply the loudness target, write the file and its notes, and describe the result."""
    sr = record.get("sample_rate", audio.SAMPLE_RATE)
    extra = {}
    if target_lufs is not None:
        samples, extra = loud.match_loudness(samples, sr, target_lufs)
    path = audio.write_audio(audio.unique_path(folder, stem, f".{fmt}"), samples, sr, loop)
    levels = {**measure(samples), "lufs": round(loud.lufs(samples, sr), 1)}
    record = {**record, "format": fmt, "loop": loop, "duration_s": round(len(samples) / sr, 2), **levels, **extra}
    metadata.write_sidecar(path, record)
    return {"path": str(path), "format": fmt, "duration_s": record["duration_s"], "loop": loop, **levels, **extra}


def _seed(seed: int | None, spread: int = MAX_VARIATIONS) -> int:
    return seed if seed is not None else secrets.randbelow(2**31 - spread)


# ---- tools -----------------------------------------------------------------------------------


@mcp.tool()
def list_recipes() -> list[dict]:
    """List every sound recipe NoiseSmith can make, with what each setting means.

    Call this first if you are unsure which recipe fits, or what intensity and size mean.
    """
    return [
        {
            "recipe": r.name,
            "summary": r.summary,
            "intensity": r.intensity_meaning,
            "size": r.size_meaning,
            "styles": r.styles,
            "default_duration": r.default_duration,
        }
        for r in RECIPES.values()
    ]


@mcp.tool()
@friendly_errors
def create_sound(
    recipe: str,
    intensity: float = 0.5,
    size: float = 0.5,
    duration_s: float | None = None,
    style: str = "",
    variations: int = 1,
    seed: int | None = None,
    name: str | None = None,
    description: str = "",
    loop: bool = False,
    loop_crossfade_s: float = 1.0,
    format: str = "wav",
    loudness: str | float | None = None,
    output_dir: str | None = None,
) -> dict:
    """Create a sound effect and save it as an audio file (plus a small .json notes file).

    Choose the closest recipe (see list_recipes) and translate the user's words into numbers:
    `intensity` (0 to 1) is how strong or hard the sound is, `size` (0 to 1) is how big the
    source is, `style` picks a variant. For example "a slight breeze" is recipe wind with
    intensity 0.1, and "a hurricane" is wind with intensity 1.0. What intensity and size
    mean depends on the recipe.

    `variations` makes several different versions (1 to 20) so the user can pick one.
    `seed` repeats an earlier result exactly. `description` is the user's original request,
    saved in the notes file. Files go in ./sounds by default and never overwrite older ones.

    `loop=True` makes a seamless loop of `duration_s` seconds (default 10), good for ambience
    such as wind, rain or hums; it is the wrong choice for one-off hits. WAV loops also carry
    loop points that game engines use. `format` is wav (default), flac, ogg or mp3.
    `loudness` matches a loudness target: "game" (-16 LUFS), "web" (-14), "broadcast" (-23),
    or a number such as -18. Leave it out to keep the recipe's natural level.

    Returns the saved file paths and levels. The sounds are made by NoiseSmith's built-in
    engine (synthesis, plus reshaped CC0 recordings for the creaks) and are CC0: free to use
    anywhere, including commercial projects.
    """
    if not 1 <= variations <= MAX_VARIATIONS:
        raise ValueError(f"variations must be between 1 and {MAX_VARIATIONS}")
    fmt = audio.check_format(format)
    target = loud.parse_target(loudness)
    if loop:
        length = duration_s or DEFAULT_LOOP_S
        _check_loop_args(length, loop_crossfade_s)
        generate_s = length + 2 * LOOP_TRIM_S + loop_crossfade_s
    folder = audio.resolve_output_dir(output_dir)
    base_seed = _seed(seed)
    base_name = audio.safe_name(name or (f"{recipe}_{style}" if style else recipe))

    files = []
    for index in range(variations):
        this_seed = base_seed + index
        samples, notes = synth.generate_full(
            recipe, intensity=intensity, size=size, duration_s=generate_s if loop else duration_s, style=style, seed=this_seed
        )
        if loop:
            samples = _make_loop(samples, loop_crossfade_s, LOOP_TRIM_S)
        stem = f"{base_name}_{index + 1:02d}" if variations > 1 else base_name
        record = {
            "engine": synth.ENGINE_NAME,
            "output_license": synth.OUTPUT_LICENSE,
            "description": description,
            "recipe": recipe,
            "settings": {"intensity": intensity, "size": size, "duration_s": duration_s, "style": style},
            "seed": this_seed,
            "sample_rate": audio.SAMPLE_RATE,
            **notes,  # e.g. which recorded clips were used
        }
        if loop:
            record["loop_crossfade_s"] = loop_crossfade_s
        files.append({"seed": this_seed, **_save(samples, folder, stem, fmt=fmt, loop=loop, target_lufs=target, record=record)})

    return {"recipe": recipe, "engine": synth.ENGINE_NAME, "license": synth.OUTPUT_LICENSE, "files": files}


@mcp.tool()
@friendly_errors
def mix_sounds(
    layers: list[dict],
    duration_s: float,
    name: str | None = None,
    description: str = "",
    seed: int | None = None,
    loop: bool = False,
    loop_crossfade_s: float = 1.0,
    format: str = "wav",
    loudness: str | float | None = None,
    output_dir: str | None = None,
) -> dict:
    """Layer several sounds into one scene, such as a storm, a busy street or a haunted room.

    `layers` is a list of dictionaries. Each has exactly ONE source:
      {"recipe": "wind", "intensity": 1.0, "style": "howling"}   a NoiseSmith recipe
      {"file": "sounds/thunder.wav"}                             an audio file (wav, flac, ogg, mp3)
      {"generator": {"type": "noise", "color": "brown", "duration_s": 3, ...}}   a custom sound
    A recipe layer also takes that recipe's intensity, size, style, duration_s and seed.
    Every layer can set: gain_db (volume in decibels, 0 default, -6 half as loud), start_s,
    length_s, fade_in_s, fade_out_s, speed (below 1 lower and slower), and repeat_every_s with
    repeat_jitter (0 to 1, uneven spacing), repeat_count and speed_jitter to repeat the sound
    through the scene. Example, a storm:
      [{"recipe": "wind", "intensity": 0.9, "style": "gusty", "duration_s": 20, "gain_db": -3},
       {"recipe": "rain", "intensity": 0.8, "duration_s": 20, "gain_db": -6},
       {"recipe": "impact", "style": "stone", "size": 1.0, "intensity": 0.6, "gain_db": -12,
        "start_s": 4, "repeat_every_s": 9, "repeat_jitter": 0.6}]
    A custom generator is {"type": "noise" or "tone", "duration_s", "color" (white/pink/brown),
    "wave" (sine/triangle/square/saw), "freq_hz" (a number or {"from": hz, "to": hz}),
    "filters" (a list of lowpass/highpass/bandpass with freq_hz and q) and "envelope"
    (attack_s, hold_s, decay_s, release_s)}. Generators are for machinery, sci-fi and similar
    sounds, not animals or voices.

    `duration_s` is the length of the whole scene (up to 120 s). Wind and rain layers that
    have no duration_s of their own run for the whole scene, and a layer whose duration_s
    equals the scene's is extended to cover a loop's join, so layers never run out early.
    `loop`, `loop_crossfade_s`,
    `format` and `loudness` work as in create_sound. If the layers add up too loud, the mix is
    turned down to stay clear of clipping. Scenes made only from recipes and generators are
    CC0; a file layer carries whatever license that file has.
    """
    fmt = audio.check_format(format)
    target = loud.parse_target(loudness)
    if loop:
        _check_loop_args(duration_s, loop_crossfade_s)
    render_s = duration_s + 2 * LOOP_TRIM_S + loop_crossfade_s if loop else duration_s
    base_seed = _seed(seed, 1)
    samples, notes = mixing.render_mix(layers, render_s, base_seed, requested_s=duration_s if loop else None)
    if loop:
        samples = _make_loop(samples, loop_crossfade_s, LOOP_TRIM_S)
    samples = fade(samples, 0.005, 0.01, audio.SAMPLE_RATE) if not loop else samples
    peak_db = amp_to_db(np.max(np.abs(samples)))
    if peak_db > MIX_PEAK_DBFS:  # only ever turned down
        samples = normalize_peak(samples, MIX_PEAK_DBFS)
        notes["turned_down_db"] = round(peak_db - MIX_PEAK_DBFS, 1)

    uses_files = any(isinstance(layer, dict) and "file" in layer for layer in layers)
    record = {
        "engine": "mix",
        "output_license": "depends on the licenses of the sound files used" if uses_files else synth.OUTPUT_LICENSE,
        "description": description,
        "seed": base_seed,
        "sample_rate": audio.SAMPLE_RATE,
        "mix_duration_s": duration_s,
        "layers": json.loads(json.dumps(layers)),
        **notes,
    }
    if loop:
        record["loop_crossfade_s"] = loop_crossfade_s
    folder = audio.resolve_output_dir(output_dir)
    stem = audio.safe_name(name or "mix")
    info = _save(samples, folder, stem, fmt=fmt, loop=loop, target_lufs=target, record=record)
    return {"engine": "mix", "license": record["output_license"], "seed": base_seed, "layers": notes["layers"], "files": [info]}


@mcp.tool()
@friendly_errors
def export_sound(
    path: str,
    format: str = "wav",
    loudness: str | float | None = None,
    sample_rate: int | None = None,
    trim_silence: bool = False,
    fade_in_s: float = 0.0,
    fade_out_s: float = 0.0,
    name: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Convert a sound file to another format, level or length, saving a new file.

    `path` is any wav, flac, ogg or mp3 file. `format` is wav, flac, ogg or mp3.
    `loudness` is "game" (-16 LUFS), "web" (-14), "broadcast" (-23) or a number of LUFS;
    peaks are kept 1 dB below full scale, so a very peaky sound may come out quieter than the
    target (the result says so). `sample_rate` resamples (for example 44100). `trim_silence`
    removes silence at both ends, and the fades are in seconds. The original file is untouched.
    """
    fmt = audio.check_format(format)
    target = loud.parse_target(loudness)
    source = Path(path).expanduser()
    if not 0 <= fade_in_s <= 60 or not 0 <= fade_out_s <= 60:
        raise ValueError("fade_in_s and fade_out_s must be between 0 and 60 seconds")
    rate = sample_rate or audio.SAMPLE_RATE
    if not 8000 <= rate <= 192000:
        raise ValueError("sample_rate must be between 8000 and 192000")

    samples = audio.read_audio(source)
    if trim_silence:
        loudish = np.flatnonzero(np.abs(samples) > 0.01 * np.max(np.abs(samples)))
        if len(loudish):
            pad = int(0.01 * audio.SAMPLE_RATE)
            samples = samples[max(loudish[0] - pad, 0) : loudish[-1] + pad]
    if fade_in_s or fade_out_s:
        samples = fade(samples, fade_in_s, fade_out_s, audio.SAMPLE_RATE)
    if rate != audio.SAMPLE_RATE:
        ratio = Fraction(rate, audio.SAMPLE_RATE).limit_denominator(1000)
        samples = signal.resample_poly(samples, ratio.numerator, ratio.denominator)

    source_notes = source.with_suffix(".json")
    license_note = "unknown (inherited from the source file)"
    if source_notes.is_file():
        try:
            license_note = json.loads(source_notes.read_text(encoding="utf-8")).get("output_license", license_note)
        except (OSError, ValueError):
            pass
    record = {
        "engine": "export",
        "output_license": license_note,
        "source_file": str(source),
        "sample_rate": rate,
        "settings": {"trim_silence": trim_silence, "fade_in_s": fade_in_s, "fade_out_s": fade_out_s},
    }
    folder = audio.resolve_output_dir(output_dir)
    info = _save(samples, folder, audio.safe_name(name or source.stem), fmt=fmt, loop=False, target_lufs=target, record=record)
    return {"engine": "export", "license": license_note, "files": [info]}


@mcp.tool()
@friendly_errors
def make_loop(
    path: str,
    crossfade_s: float = 1.0,
    trim_s: float = 0.0,
    format: str | None = None,
    loudness: str | float | None = None,
    name: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Turn an existing sound file into a seamless loop, saving a new file.

    The last `crossfade_s` seconds are blended into the start so it repeats with no click.
    Use `trim_s` to cut that many seconds off both ends first (to drop a fade-in or fade-out).
    The result is shorter than the original by the crossfade plus the trims, and the sound
    should be at least three times the crossfade long. Works best on ambience such as wind,
    rain or hums. `format` defaults to the source file's format; WAV loops carry loop points.
    """
    source = Path(path).expanduser()
    fmt = audio.check_format(format or source.suffix)
    target = loud.parse_target(loudness)
    if trim_s < 0:
        raise ValueError("trim_s cannot be negative")
    samples = _make_loop(audio.read_audio(source), crossfade_s, trim_s)

    source_notes = source.with_suffix(".json")
    license_note = "unknown (inherited from the source file)"
    if source_notes.is_file():
        try:
            license_note = json.loads(source_notes.read_text(encoding="utf-8")).get("output_license", license_note)
        except (OSError, ValueError):
            pass
    record = {
        "engine": "loop",
        "output_license": license_note,
        "source_file": str(source),
        "sample_rate": audio.SAMPLE_RATE,
        "loop_crossfade_s": crossfade_s,
        "settings": {"crossfade_s": crossfade_s, "trim_s": trim_s},
    }
    folder = audio.resolve_output_dir(output_dir)
    info = _save(samples, folder, audio.safe_name(name or f"{source.stem}_loop"), fmt=fmt, loop=True, target_lufs=target, record=record)
    return {"engine": "loop", "license": license_note, "files": [info]}


@mcp.tool()
@friendly_errors
def preview_sound(path: str) -> str:
    """Play a saved sound through the computer's speakers so the user can hear it."""
    return preview.play(Path(path).expanduser())


def main() -> None:
    """Start the server (Claude launches this and talks to it over stdin/stdout)."""
    mcp.run()


if __name__ == "__main__":
    main()
