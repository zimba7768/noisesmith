# NoiseSmith

Describe a sound in plain words inside Claude, and get an audio file saved in your project.

> "an old creaky door" · "a very big dog barking" · "a small dog barking" · "wind, from a slight whoosh to a hurricane"

**Status: early development (Phase 0).** Right now the only tool is a test beep. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for where this is going.

Free and open source (MIT). Sounds made by the built-in synthesizer are yours to use anywhere, including commercial projects.

## Try the Phase 0 prototype

You need [uv](https://docs.astral.sh/uv/) installed. Then install the Claude Code plugin:

```bash
claude plugin install noisesmith --marketplace zimba7768/noisesmith
```

Ask Claude: *"make a beep sound"*. It saves `sounds/beep.wav` in your project folder.

Prefer a plain MCP server (works in Cursor, VS Code and others too)?

```bash
claude mcp add noisesmith -- uvx --from git+https://github.com/zimba7768/noisesmith noisesmith
```

## Development

```bash
uv sync
uv run pytest
```
