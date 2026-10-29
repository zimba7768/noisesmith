"""The built-in engine: free, offline, and the output is CC0 (yours with no conditions).

Most recipes synthesize their sound from scratch. A few (the creaks) reshape recorded CC0
sounds that ship with NoiseSmith; the notes file saved with each sound says which.
"""

import numpy as np

from noisesmith.audio import SAMPLE_RATE
from noisesmith.recipes import Params, get_recipe

ENGINE_NAME = "builtin"
OUTPUT_LICENSE = "CC0-1.0"  # public domain: use anywhere, including commercial projects
MIN_DURATION_S = 0.05
MAX_DURATION_S = 60.0


def generate(recipe_name: str, **settings) -> np.ndarray:
    """Make one sound. The same arguments and seed always give the same samples."""
    return generate_full(recipe_name, **settings)[0]


def generate_full(
    recipe_name: str,
    *,
    intensity: float,
    size: float,
    duration_s: float | None,
    style: str,
    seed: int,
) -> tuple[np.ndarray, dict]:
    """Like generate, but also returns facts about how it was made (for the notes file)."""
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
    samples = recipe.render(params)
    return samples, params.notes
