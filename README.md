# NoiseSmith

Describe a sound in plain words inside Claude, and get an audio file saved in your project.

> "an old creaky door" · "wind, from a slight breeze to a hurricane" · "a heavy iron gate slamming" · "light drizzle"

**Status: early development (Phase 1).** NoiseSmith can make wind, whooshes, door and floor creaks, impacts, rain and game blips today, and loop, layer and export them. Animal sounds (a barking dog) are planned for a later AI-powered upgrade. See [PROJECT_PLAN.md](PROJECT_PLAN.md).

Free and open source (MIT). Everything the built-in engine makes is **CC0**: use it anywhere, including commercial projects, no credit needed. Some sounds are synthesized from scratch (whooshes, impacts, game blips). The natural ones are made from real recordings that are reshaped, because synthesizing them never sounded natural: the creaks (see [credits](src/noisesmith/assets/creaks/CREDITS.md)) and the wind, rain and thunder, recorded by Joseph Sardin (see [credits](src/noisesmith/assets/ambience/CREDITS.md)). All are CC0.

## What it can make

| Recipe | Examples | Settings |
|---|---|---|
| `wind` | breeze, gale, hurricane (steady, gusty or howling) | strength |
| `thunder` | distant rumble to a close crack | how close, storm size |
| `whoosh` | swish, sword swing, passing car, jet fly-by | power, object size |
| `door_creak` | cupboard, old door, heavy gate, long horror-movie creak | how worn, door size |
| `floor_creak` | creaking floorboards, stairs, old wood | how worn, size |
| `impact` | wood knock, metal clang, glass clink, stone thud, boom | how hard, object size |
| `rain` | drizzle to downpour | strength |
| `ui_blip` | beep, click, coin, jump, error, success, power-up, laser | harshness, pitch |

Ask for several versions at once ("give me 5 variations") and pick your favourite. Every sound also gets a small `.json` file recording exactly how it was made, so it can be re-created.

## Loops, scenes and files

- **Seamless loops:** "a 20 second loop of strong wind". WAV loops carry loop points that game engines read.
- **Scenes:** "a storm with gusty wind, heavy rain and a distant boom every 8 seconds" layers several sounds with their own volume, timing and repeats. You can also add custom noise or tone generators for machinery and sci-fi sounds.
- **Formats and loudness:** save as WAV, FLAC, OGG or MP3, and match a loudness target: `game` (-16 LUFS), `web` (-14), `broadcast` (-23), or any number.
- **Existing files:** convert, trim, resample or loop any WAV, FLAC, OGG or MP3 file.

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
