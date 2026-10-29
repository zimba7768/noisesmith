"""Creaking floorboards, stairs and old wood: real recorded creaks (CC0), reshaped."""

import numpy as np

from noisesmith import samples
from noisesmith.recipes._creaks import compose
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    return compose(p, samples.FLOOR, long_style=p.style == "long", default_s=6.0 if p.style == "long" else 1.8)


RECIPE = Recipe(
    name="floor_creak",
    summary="Creaking floorboards, stairs or old wood, made from real recorded creaks (CC0) that are reshaped.",
    intensity_meaning=(
        "How worn and loud. 0.1 = soft, dull creak; 0.5 = clear creaking boards; "
        "1.0 = bright and loud, with a deeper second creak layered underneath."
    ),
    size_meaning="Size and weight. 0 = small and light (a stool, a drawer), 1 = big and heavy (a barn floor, a ship's timber).",
    styles={
        "creak": "A creak or two, like stepping on a board (default).",
        "long": "A long run of creaking, like someone slowly crossing an old floor.",
    },
    default_duration="about 2 to 4 seconds for creak (longer for bigger); about 6 to 8 seconds for long",
    render=render,
)
