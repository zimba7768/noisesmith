"""The shared shape of a recipe: what goes in, what comes out, and how it describes itself."""

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Params:
    """Everything a recipe needs to make one sound."""

    rng: np.random.Generator  # the only source of randomness, so a seed repeats exactly
    sr: int  # samples per second
    duration_s: float | None  # None means "choose a sensible length"
    intensity: float  # 0..1, meaning depends on the recipe
    size: float  # 0..1, meaning depends on the recipe
    style: str  # one of the recipe's styles, or "" for the default
    notes: dict = field(default_factory=dict)  # a recipe can record facts here (e.g. which recordings it used)


@dataclass(frozen=True)
class Recipe:
    """A recipe plus the plain-language description Claude reads to choose settings."""

    name: str
    summary: str
    intensity_meaning: str
    size_meaning: str
    styles: dict[str, str]  # style name -> what it sounds like. The first one is the default
    default_duration: str  # human-readable, shown in list_recipes
    render: Callable[[Params], np.ndarray]  # returns mono samples, peak at or below 0 dBFS
