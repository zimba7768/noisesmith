"""The recipe catalog. To add a recipe: write a module with a RECIPE, then list it below."""

from noisesmith.recipes import door_creak, floor_creak, impact, rain, thunder, ui_blip, whoosh, wind
from noisesmith.recipes.base import Params, Recipe

RECIPES: dict[str, Recipe] = {
    module.RECIPE.name: module.RECIPE
    for module in (wind, whoosh, door_creak, floor_creak, thunder, impact, rain, ui_blip)
}

__all__ = ["RECIPES", "Params", "Recipe", "get_recipe"]


def get_recipe(name: str) -> Recipe:
    try:
        return RECIPES[name]
    except KeyError:
        raise ValueError(f"Unknown recipe {name!r}. Available recipes: {', '.join(RECIPES)}") from None
