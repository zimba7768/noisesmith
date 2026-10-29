"""The built-in synthesizer: free, offline, and the output is CC0 (yours with no conditions)."""

import numpy as np

from noisesmith.audio import SAMPLE_RATE
from noisesmith.recipes import Params, get_recipe

ENGINE_NAME = "synth"
OUTPUT_LICENSE = "CC0-1.0"  # public domain: use anywhere, including commercial projects
MIN_DURATION_S = 0.05
MAX_DURATION_S = 60.0


def generate(
    recipe_name: str,
    *,
    intensity: float,
    size: float,
    duration_s: float | None,
    style: str,
    seed: int,
) -> np.ndarray:
    """Make one sound. The same arguments and seed always give the same samples."""
    recipe = get_recipe(recipe_name)
    if not 0.0 <= intensity <= 1.0:
        raise ValueError("intensity must be between 0 and 1")
    if not 0.0 <= size <= 1.0:
        raise ValueError("size must be between 0 and 1")
    if duration_s is not None and not MIN_DURATION_S <= duration_s <= MAX_DURATION_S:
        raise ValueError(f"duration_s must be between {MIN_DURATION_S} and {MAX_DURATION_S} seconds")
    if style and style not in recipe.styles:
        raise ValueError(f"Unknown style {style!r} for {recipe.name}. Choose from: {', '.join(recipe.styles)}")

    params = Params(
        rng=np.random.default_rng(seed),
        sr=SAMPLE_RATE,
        duration_s=duration_s,
        intensity=intensity,
        size=size,
        style=style,
    )
    return recipe.render(params)
