# Phase 0 spike results (2026-10-29)

## Spike A: Claude Code plugin — works, one check left

- `claude plugin validate --strict ./plugin` passes. The only warning is a missing icon, which we add before v1.0.
- The marketplace file (`.claude-plugin/marketplace.json`, plugin `source: "./plugin"`) validates.
- The exact command in `plugin/.mcp.json` (`uvx --from git+https://github.com/zimba7768/noisesmith noisesmith`) was run on Windows against the public repo. A real MCP client listed the tool and `make_beep` wrote a valid WAV. First run builds the package (a few seconds); later runs use uv's cache.
- **Not yet verified:** a full chat in Claude Code (`claude plugin install ...`, then asking for a beep). A nested `claude -p` run from inside the development session couldn't authenticate, so this needs a manual check in a normal terminal. See "Manual checks" below.

## Spike B: Claude Desktop extension (.mcpb) — builds and runs, install not yet tested

- `uv run python scripts/build_mcpb.py` validates the manifest with Anthropic's official packer (`@anthropic-ai/mcpb`, pinned) and produces `dist/noisesmith-0.0.1.mcpb` (4.7 kB).
- The bundle was unpacked into an empty folder and its `mcp_config` command (`uv run --directory <bundle> noisesmith`) was run with the sounds-folder setting passed as `NOISESMITH_OUTPUT_DIR`. The tool listed and wrote a WAV into that folder.
- Findings: the validator requires `mcp_config.command` whenever `mcp_config` exists, so the bundle runs `uv` explicitly. **That means `uv` must be installed on the user's PATH.** Whether Claude Desktop supplies its own `uv` for `server.type: "uv"` is not documented; test it (see below).
- **Not yet verified:** double-click install inside Claude Desktop.

## Spike C: local AI model on the AMD RX 7900 XT — not feasible yet; design change needed

What the MOSS-SoundEffect-v2.0 docs say (no model was downloaded):

- 1.3B-parameter DiT, 48 kHz, up to 30 s, Hugging Face `OpenMOSS-Team/MOSS-SoundEffect-v2.0`.
- Documented for **CUDA only** (`cu128` wheels, `device="cuda"`, `torch.compile` with Triton CUDA graphs). ROCm, Apple (MPS) and CPU are not mentioned.
- Needs its **own environment**: Python 3.12, `torch==2.9`, `transformers==4.57`, `numpy==1.26`. The page says it is incompatible with the MOSS-TTS environment.
- VRAM needs, generation time, download size, and **the v2.0 model's license are not stated on that page** (the repo says the MOSS-TTS family is Apache-2.0). Check the Hugging Face model card before we promise "Apache-2.0".
- AMD's PyTorch-on-Windows wheels exist (ROCm 7.2, Python 3.12, special wheels from repo.radeon.com). The RX 7900 XTX is listed as supported; the plain 7900 XT is not clearly listed. Sources disagree.

Consequences for the plan:

1. **The local AI backend runs as a separate worker process in its own managed virtual environment** (Python 3.12, its own torch), created by `setup_engine` after the user agrees. It must never be a dependency of the main `noisesmith` package. That keeps the default install small and avoids version clashes with `mcp` and `numpy`.
2. Local AI is documented as **NVIDIA-first** at launch. AMD, Apple and CPU are "experimental until tested".
3. For development on this AMD machine, the cloud backend (ElevenLabs) is the practical way to hear realistic animal sounds. A ROCm experiment is optional and needs the owner's go-ahead because of the multi-GB downloads.
4. Stable Audio Open Small stays the CPU-friendly backup candidate.

## Other decisions made in Phase 0

- Used `mcp` 2.x (`from mcp.server.mcpserver import MCPServer`). The older `FastMCP` import no longer exists in 2.x.
- `server.py` uses an absolute import (`from noisesmith import audio`) so it works both as an installed command and as a script, which the Desktop host may use.

## Manual checks still needed (someone with a normal terminal and Claude Desktop)

1. In Claude Code: `claude plugin install noisesmith --marketplace zimba7768/noisesmith`, then ask "make a beep sound" and confirm `sounds/beep.wav` appears.
2. In Claude Desktop: install `dist/noisesmith-0.0.1.mcpb` (Settings, Extensions, Advanced settings, Install Extension) on a machine with and without `uv` installed, and note what happens.
