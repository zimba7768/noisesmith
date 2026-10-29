"""A door creaking: real recorded creaks (CC0), reshaped. See recipes/_creaks.py."""

import numpy as np

from noisesmith import samples
from noisesmith.recipes._creaks import compose
from noisesmith.recipes.base import Params, Recipe


def render(p: Params) -> np.ndarray:
    if p.style == "horror":
        return compose(p, samples.DOOR_LONG, long_style=True, default_s=6.0)
    return compose(p, samples.DOOR_LONG + samples.DOOR_SHORT, long_style=False, default_s=1.8)


RECIPE = Recipe(
    name="door_creak",
    summary="A door creaking open or shut, made from real recorded creaks (CC0) that are reshaped.",
    intensity_meaning=(
        "How creaky and worn. 0.1 = softer, duller, a single creak; 0.5 = a clear creaky door; "
        "1.0 = bright, loud, with a deeper second creak layered underneath."
    ),
    size_meaning="Size and weight of the door. 0 = small, higher and quicker (a cupboard); 1 = huge, deep and slow (a heavy gate).",
    styles={
        "creak": "One or a few creaks, like a door opened or closed in steps (default).",
        "horror": "A long, slow, drawn-out creak built from several recordings, deeper and slower. Use for spooky, haunted, horror doors.",
    },
    default_duration="about 2 to 7 seconds for creak (longer for bigger doors); about 6 to 8 seconds for horror",
    render=render,
)
