"""The NoiseSmith MCP server: the tools Claude can call to make sounds."""

import functools
import secrets
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from noisesmith import audio, metadata, preview
from noisesmith.dsp.levels import measure
from noisesmith.engines import synth
from noisesmith.recipes import RECIPES

mcp = MCPServer("noisesmith")

MAX_VARIATIONS = 20


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
    output_dir: str | None = None,
) -> dict:
    """Create a sound effect and save it as a WAV file (plus a small .json notes file).

    Choose the closest recipe (see list_recipes) and translate the user's words into numbers:
    `intensity` (0 to 1) is how strong or hard the sound is, `size` (0 to 1) is how big the
    source is, `style` picks a variant. For example "a slight breeze" is recipe wind with
    intensity 0.1, and "a hurricane" is wind with intensity 1.0. What intensity and size
    mean depends on the recipe.

    `variations` makes several different versions (1 to 20) so the user can pick one.
    `seed` repeats an earlier result exactly. `description` is the user's original request,
    saved in the notes file. Files go in ./sounds by default and never overwrite older ones.
    Returns the saved file paths and levels. The sounds are made by NoiseSmith's built-in
    engine (synthesis, plus reshaped CC0 recordings for the creaks) and are CC0: free to use
    anywhere, including commercial projects.
    """
    if not 1 <= variations <= MAX_VARIATIONS:
        raise ValueError(f"variations must be between 1 and {MAX_VARIATIONS}")
    folder = audio.resolve_output_dir(output_dir)
    base_seed = seed if seed is not None else secrets.randbelow(2**31 - MAX_VARIATIONS)
    base_name = audio.safe_name(name or (f"{recipe}_{style}" if style else recipe))

    files = []
    for index in range(variations):
        this_seed = base_seed + index
        samples, notes = synth.generate_full(
            recipe, intensity=intensity, size=size, duration_s=duration_s, style=style, seed=this_seed
        )
        stem = f"{base_name}_{index + 1:02d}" if variations > 1 else base_name
        path = audio.write_wav(audio.unique_path(folder, stem), samples)
        record = {
            "engine": synth.ENGINE_NAME,
            "output_license": synth.OUTPUT_LICENSE,
            "description": description,
            "recipe": recipe,
            "settings": {"intensity": intensity, "size": size, "duration_s": duration_s, "style": style},
            "seed": this_seed,
            "sample_rate": audio.SAMPLE_RATE,
            "duration_s": round(len(samples) / audio.SAMPLE_RATE, 2),
            **measure(samples),
            **notes,  # e.g. which recorded clips were used
        }
        metadata.write_sidecar(path, record)
        files.append({"path": str(path), "seed": this_seed, "duration_s": record["duration_s"], **measure(samples)})

    return {"recipe": recipe, "engine": synth.ENGINE_NAME, "license": synth.OUTPUT_LICENSE, "files": files}


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
