# NoiseSmith

Describe a sound in plain words inside Claude, and get an audio file saved in your project.

> "an old creaky door" · "wind, from a slight breeze to a hurricane" · "a heavy iron gate slamming" · "light drizzle"

**Status: early development (Phase 1).** NoiseSmith can make wind, whooshes, door creaks, impacts, rain and game blips today. Animal sounds (a barking dog) are planned for a later AI-powered upgrade. See [PROJECT_PLAN.md](PROJECT_PLAN.md).

Free and open source (MIT). Sounds made by the built-in synthesizer are **CC0**: use them anywhere, including commercial projects, no credit needed.

## What it can make

| Recipe | Examples | Settings |
|---|---|---|
| `wind` | breeze, gale, hurricane (steady, gusty or howling) | strength |
| `whoosh` | swish, sword swing, passing car, jet fly-by | power, object size |
| `door_creak` | cupboard, old door, heavy gate | how creaky, door size |
| `impact` | wood knock, metal clang, glass clink, stone thud, boom | how hard, object size |
| `rain` | drizzle to downpour | strength |
| `ui_blip` | beep, click, coin, jump, error, success, power-up, laser | harshness, pitch |

Ask for several versions at once ("give me 5 variations") and pick your favourite. Every sound also gets a small `.json` file recording exactly how it was made, so it can be re-created.

## Install

You need [uv](https://docs.astral.sh/uv/) installed. Then, for Claude Code:

```bash
claude plugin install noisesmith --marketplace zimba7768/noisesmith
```

Now just ask Claude: *"make the sound of a strong wind howling"* or *"3 variations of a small wooden door creaking"*. Files are saved in a `sounds` folder in your project.

Prefer a plain MCP server (works in Cursor, VS Code and others too)?

```bash
claude mcp add noisesmith -- uvx --from git+https://github.com/zimba7768/noisesmith noisesmith
```

A one-click Claude Desktop extension (`.mcpb`) can be built with `uv run python scripts/build_mcpb.py`; downloads will be attached to releases later.

## Development

```bash
uv sync
uv run pytest
```

Adding a new sound recipe is meant to be approachable: copy a file in `src/noisesmith/recipes/`, change the sound, and list it in `recipes/__init__.py`.
