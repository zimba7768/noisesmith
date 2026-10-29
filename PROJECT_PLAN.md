# NoiseSmith — Project Plan

> Type a prompt in Claude, get a sound effect file in your project.
> "an old creaky door" · "a very big dog barking" · "a small dog barking" · "wind, from a slight whoosh to a hurricane"

| | |
|---|---|
| **Repo** | `github.com/zimba7768/noisesmith` (name is free on GitHub + PyPI as of 2026-10-29) |
| **License** | MIT for the code. Sounds made by the built-in synthesizer are **CC0** (the user owns them, no strings) |
| **Works in** | Claude Code (plugin) and Claude Desktop (one-click extension). It is a standard MCP server, so Cursor and VS Code work too at no extra cost |
| **Language** | Python. It's the best language for audio work, the easiest to read, and matches claude.ai's sandbox if we add a web version later |
| **Status** | Planning |

---

## 1. Plugin or extension? Both, from one codebase

They're the same engine in two wrappers:

| Term | What it is | Who uses it |
|---|---|---|
| **MCP server** | The "engine room": a small program that gives Claude new tools (e.g. `create_sound`) | Everything below runs this |
| **Claude Code plugin** | A bundle with the MCP server, a `/sound` slash command and a skill that teaches Claude to be a sound designer | Developers using Claude Code |
| **Claude Desktop extension (.mcpb)** | A single file you double-click to install the MCP server into the Desktop app | People chatting in Claude Desktop |

We write the engine **once**, and the plugin and extension are thin wrappers around it.
Neither of these can reach the **claude.ai website**. That needs either a paid hosted server or a
claude.ai "skill" with reduced features. It's listed as a v2 idea in §9.

---

## 2. How it works

```
 You: "make a very big dog barking, 3 variations"
            │
            ▼
 ┌──────────────────────────┐   Claude reads the NoiseSmith skill, which teaches it
 │ Claude (the sound        │   to turn words into parameters:
 │ designer)                │   "very big" → size 0.9, pitch low, long resonance
 └────────────┬─────────────┘   "creaky + old" → friction high, irregular
              │ calls tool: create_sound(recipe="dog_bark", size=0.9, variations=3, ...)
              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ NoiseSmith MCP server                                   │
 │  Engine router: picks the best backend                  │
 │   ├─ Synth (built in, free, offline)   ← default        │
 │   ├─ Local AI (MOSS-SoundEffect, on your GPU) optional  │
 │   └─ Cloud AI (ElevenLabs, your own API key) optional   │
 │  Post-processing: loop · layer/mix · loudness · export  │
 └────────────┬────────────────────────────────────────────┘
              ▼
 ./sounds/dog_bark_big_01.wav  (+ _02, _03)
 ./sounds/dog_bark_big_01.json ← how it was made: prompt, seed, engine, license
```

**Main design decision:** Claude does the *understanding* and NoiseSmith does the *sound*.
Claude is good at turning "slight whoosh" or "hurricane" into numbers such as `intensity: 0.1`
or `intensity: 1.0`. The engine reliably turns those numbers into audio. This means:
- The same recipe covers the whole range from a breeze to a hurricane, or from a chihuahua to a mastiff.
- Results can be repeated exactly: the same parameters and **seed** always give the same file.
- Claude never runs arbitrary code on the user's machine. It only fills in a safe **sound spec** (JSON).

### Engine routing ("hybrid")
1. **Synth (default)** handles anything with a good recipe: wind, whooshes, impacts, creaks, rain, fire, thunder, UI sounds, sci-fi sounds, engines and room tone.
2. **Realistic requests** such as animals, voices or complex real-world foley go to an AI backend **if one is set up**.
3. If no AI backend is set up, NoiseSmith makes a synth approximation and tells the user plainly: *"This is a synthesized bark. For a realistic one, run `/noisesmith:setup`."*
4. The user can always force a choice: "use the synth" or "use ElevenLabs".

---

## 3. The sound engines

| Engine | Good at | Cost to user | Needs | Output license |
|---|---|---|---|---|
| **Synth** (numpy/scipy) | Wind, whoosh, impacts, rain, fire, UI and sci-fi sounds; creaks are fair. Weak at animals and voices | Free | Nothing extra | CC0 — fully owned |
| **MOSS-SoundEffect v2.0** (local AI) | Realistic foley and animals, 48 kHz, up to 30 s | Free | A GPU and a model download of several GB (only when the user asks) | Apache-2.0 model, no revenue limits |
| **Stable Audio Open Small** (local AI, optional) | Runs on a laptop CPU, up to about 11 s | Free | About 1 GB download; the user must accept a gated license | ⚠️ Free only for organisations under $1M/yr revenue. NoiseSmith must show this warning |
| **ElevenLabs Sound Effects** (cloud) | Best realism overall, including animals | About $0.12/min of audio | The user's own API key | ⚠️ Commercial use only on a **paid** ElevenLabs plan. The free plan is non-commercial. NoiseSmith must show this warning |

**Excluded on purpose:** AudioGen, AudioLDM 2, Tango 2, TangoFlux, Sony Woosh and MMAudio. Their
licenses only allow non-commercial use, which conflicts with "use in any project".

**Every file's `.json` sidecar records which engine made it and the license that applies.**

---

## 4. Features in v1

| Feature | What the user types | What happens |
|---|---|---|
| **Intensity and size** | "slight whoosh" → "hurricane"; "small dog" vs "big dog" | Continuous `intensity` and `size` controls (0–1) on every recipe |
| **Variations** | "give me 5 variations" | Different seeds produce 5 natural-sounding versions; useful in games so sounds don't repeat |
| **Seamless loops** | "a loopable wind ambience, 20 seconds" | A crossfade loop with no click at the seam; loop points are saved in the WAV |
| **Layering and mixing** | "a storm: hurricane wind + heavy rain + distant thunder every few seconds" | The mix tool sets each layer's volume, start time, fades and repeats |
| **Game/video export** | "export as OGG for Godot" / "MP3 for my video" | WAV, OGG, MP3 or FLAC; loudness presets (Game −16 LUFS, Web −14, Broadcast −23); peak safety |
| **Preview** | "play it" | Plays the file on the computer's speakers (Claude itself can't hear) |
| **Recipe catalog** | "what sounds can you make?" | Lists recipes and their parameters |
| **Custom sound design** | Anything without a recipe | Claude builds a layered sound spec from building blocks (noise, oscillators, filters, envelopes, resonators) |

### MCP tools (what Claude can call)
| Tool | Purpose |
|---|---|
| `create_sound` | Main entry. Takes recipe or spec, intensity, size, duration, variations, seed, loop, format, engine |
| `design_sound` | Custom layered synthesis from a JSON sound spec |
| `mix_sounds` | Layer existing files or specs with gain, offset, fades and repeats |
| `make_loop` | Turn any sound into a seamless loop |
| `export_sound` | Convert format, normalise loudness, trim |
| `preview_sound` | Play through the speakers |
| `list_recipes` | Show the catalog and each recipe's parameters |
| `engine_status` / `setup_engine` | Show which AI backends are ready, and guide setup (key entry, model download with consent) |

### Starter recipe library (v1 target: ~20)
- **Weather and nature:** wind (breeze → hurricane), rain (drizzle → downpour), thunder (distant → close crack), fire (candle → bonfire), water (drip, stream, splash)
- **Movement:** whoosh/swoosh (subtle → sword swing → jet fly-by)
- **Objects:** door creak, door slam/knock, impact (wood/metal/glass/stone × small → huge), footsteps (surface × weight), explosion (pop → massive)
- **Machines:** engine/motor hum, sci-fi laser, power-up/down, alarm/beep
- **UI and game:** click, blip, coin, jump, hit, error, success
- **Ambience:** room tone, cave, city hum
- **Creatures (synth approximations, AI recommended):** dog bark (size-aware), growl, bird chirp

---

## 5. Repository layout

```
noisesmith/
├─ README.md                  ← what it is, install in 2 steps, audio examples
├─ LICENSE                    ← MIT
├─ PROJECT_PLAN.md            ← this file
├─ CONTRIBUTING.md            ← "how to add a recipe" (written for beginners)
├─ pyproject.toml             ← Python package definition (installed via uv)
├─ src/noisesmith/
│  ├─ dsp/                    ← building blocks: noise, oscillators, filters, envelopes, resonators
│  ├─ recipes/                ← one file per sound family (wind.py, door.py, dog.py …)
│  ├─ spec.py                 ← the JSON "sound spec" format and validator
│  ├─ engines/                ← synth.py, moss.py, stable_audio.py, elevenlabs.py, router.py
│  ├─ post/                   ← loop.py, mix.py, loudness.py, export.py
│  ├─ metadata.py             ← writes the .json sidecar
│  └─ server.py               ← MCP server (FastMCP), the tools listed in §4
├─ plugin/                    ← Claude Code plugin
│  ├─ .claude-plugin/plugin.json
│  ├─ .mcp.json               ← starts the server with `uvx noisesmith`
│  ├─ commands/sound.md       ← /noisesmith:sound <prompt>
│  ├─ commands/setup.md       ← /noisesmith:setup (AI backends)
│  └─ skills/sound-designer/SKILL.md  ← teaches Claude prompt → parameters
├─ .claude-plugin/marketplace.json   ← lets people `plugin marketplace add zimba7768/noisesmith`
├─ mcpb/manifest.json         ← Claude Desktop extension definition
├─ examples/                  ← demo prompts + resulting audio for the README
├─ tests/
└─ .github/workflows/         ← automatic tests on Windows/Mac/Linux + release builds
```

### How people install it (target experience)
**Claude Code**
```bash
claude plugin marketplace add zimba7768/noisesmith
```
```bash
claude plugin install noisesmith@noisesmith
```
**Claude Desktop:** download `noisesmith.mcpb` from GitHub Releases and double-click it.
**Cursor / VS Code / others:** add `uvx noisesmith` as an MCP server (snippet in README).

AI backends stay **off until the user turns them on**, so the default install is small and fast,
with no torch and no big downloads.

---

## 6. Build phases

Each phase ends with something you can try. Claude does the coding and you review and listen.

### Phase 0 — Groundwork
- [x] Create the GitHub repo `zimba7768/noisesmith`, MIT license, README stub, `.gitignore`
- [x] Python project skeleton with `uv`; "hello world" MCP server with one tool that writes a beep WAV
- [x] **Spike A:** the plugin validates, and its `uvx` command runs from GitHub on Windows. *Still to check by hand: a full chat in Claude Code.*
- [x] **Spike B:** the `.mcpb` builds, validates and runs. *Still to check by hand: installing it in Claude Desktop.*
- [x] **Spike C:** researched (no downloads). MOSS-SoundEffect v2.0 is documented for CUDA only, so it can't be tested on your AMD card yet. See [docs/phase0-spike-results.md](docs/phase0-spike-results.md). ElevenLabs comparison deferred to Phase 4.
- ✅ **Done when:** typing "make a beep" in Claude Code produces `sounds/beep.wav` — **confirmed 2026-10-29** (plugin loaded in Claude Code, file created and plays). *Claude Desktop install still to check by hand.*

### Phase 1 — MVP: synth engine + plugin
- [x] DSP building blocks: noise (white/pink/brown), filters (including a swept resonant band-pass), curves, levels, modal resonators
- [x] First 6 recipes: **wind, whoosh, door creak, impact, rain, UI blip**, each with `intensity` and `size` (some ignore one of them; each recipe says what they mean)
- [x] `create_sound`, `list_recipes`, `preview_sound`; WAV output to `./sounds/`; `.json` sidecar; errors Claude can read and act on
- [x] `/noisesmith:sound` skill: teaches Claude the word → parameter mapping, and to say so honestly when a sound isn't supported yet
- [x] Automated tests (91): clean output, the same seed repeats, and intensity and size move loudness, brightness and pitch in the right direction
- ✅ **Done when:** "wind, from slight whoosh to hurricane" yields 5 convincing files across the range — *the files are made and measured, but **"convincing" needs your ears***. Listen to the files in `sounds/` and tell us what to improve; recipe tuning is expected after the first listen

### Phase 2 — Power features
- [x] Variations (`variations: N`, auto seeds). *Done in Phase 1*
- [x] Seamless loops: `loop: true` on `create_sound` and `mix_sounds`, `make_loop` for existing files, loop points saved inside WAV files (`smpl` chunk), seam-smoothness tests
- [x] Layering: `mix_sounds` places recipes, audio files and custom generators on a timeline with gain, start, repeats, jitter, fades and speed. `design_sound` was folded into it as the `generator` layer type (noise or tone, filters, envelope)
- [x] Export: WAV, FLAC, OGG, MP3 (`format`), `export_sound` (convert, resample, trim, fade), LUFS loudness presets (game -16, web -14, broadcast -23, or any number) with a peak ceiling of -1 dB
- ✅ **Done when:** "a 30-second loopable storm: hurricane wind + heavy rain + distant thunder, OGG for a game" works in one prompt. *Works as of v0.4.0 with real wind, rain and thunder recordings, verified through the real MCP protocol. **Confirmed by ear by the project owner (2026-10-29): the storm made through the plugin, "gusty wind and heavy rain, 30-second loop, OGG for a game", "sounds perfect".***

### Phase 3 — Recipe library
- [ ] Expand to ~20 recipes (§4), including size-aware synth dog bark/growl and footsteps
- [ ] A "listening test" page in `examples/`: every recipe at low, mid and high settings
- ✅ **Done when:** each recipe is approved by ear (you're the judge)

### Phase 4 — AI backends (the "realistic" upgrade)
*Research is in [docs/phase4-research.md](docs/phase4-research.md). Lesson from the creaks and the weather: **test before building.** Each backend gets a small listening spike first, and only what sounds good gets built.*
- [ ] **Spike 1, ElevenLabs:** about six animal prompts (big dog, small dog, lion, songbird, cat, wolf) using the owner's own key, kept short to limit cost. Measure whether "big" and "small" really change the pitch, and let the owner listen
- [ ] **Spike 2, local MOSS-SoundEffect** through the `openmoss` C++ port (Vulkan, built for AMD cards), after the owner approves the exact downloads (about 6 GB)
- [ ] Engine router + `engine_status` / `setup_engine`, with the free synthesizer as the fallback when an AI backend fails or is not set up
- [ ] **ElevenLabs** backend (default cloud): key from an environment variable or a key file in the user's home folder, never in the project; a cost estimate before each call and a per-call cap; the commercial-use warning for free-plan users; `prompt_influence` and duration settings
- [ ] **Local MOSS** backend: runs as a **separate server process** (the `openmoss` binary and GGUF models in a managed folder), not as a Python dependency, so it cannot clash with the main package. `setup_engine` downloads it **only after the user agrees**, with checksums. NVIDIA, AMD (Vulkan) and CPU paths
- [ ] Optional: **Stability AI Stable Audio 3** (cloud, about $0.08) and **Stable Audio 3 Small-SFX** (local) with the $1M revenue warning. Never MMAudio or any non-commercial model
- [ ] The license recorded in every notes file; AI output can still be looped, mixed and exported
- ✅ **Done when:** "a very big dog barking" vs "a small dog barking" sound clearly and realistically different on at least one AI backend, confirmed by the owner's ears

### Phase 5 — Claude Desktop extension + releases
- [ ] `mcpb/manifest.json` with settings for the output folder, default format, ElevenLabs key (stored securely) and enabling local AI
- [ ] GitHub Actions: run tests on every change; on a version tag, build `.mcpb`, publish to PyPI and create a GitHub Release
- ✅ **Done when:** a fresh Windows PC and a fresh Mac can install from the README alone

### Phase 6 — Launch v1.0
- [ ] README with short audio demos, a GIF of the prompt → sound flow, and FAQ (licensing!)
- [ ] CONTRIBUTING "add your own recipe in 15 minutes" guide + issue templates (bug, recipe request)
- [ ] Submit to MCP server directories and share
- ✅ **Done when:** v1.0.0 is tagged and installable by anyone

---

## 7. Quality and testing
- **Automatic tests** (run on every change, on Windows/Mac/Linux): files are valid; no silence, clipping or DC offset; loops have no seam click; loudness is within ±1 LU of target; same seed means the same output
- **Prompt tests:** a fixed list of ~30 prompts (creaky door, big vs small dog, breeze vs hurricane …), each checked to confirm Claude picks sensible recipes and parameters
- **Ear tests:** before each release you listen to the `examples/` set. Some things only a human can judge

---

## 8. Risks and how we handle them

| # | Risk | Plan |
|---|---|---|
| R1 | Synth animals and voices won't sound real | Be honest in the output message; route them to AI when available; set expectations in the README |
| R2 | **Your GPU is AMD (RX 7900 XT); MOSS-SoundEffect v2.0 is documented for CUDA only** | Spike C confirmed this. Use ElevenLabs for realistic sounds while developing on this PC. A PyTorch-ROCm experiment (Python 3.12, AMD wheels, multi-GB) is optional and needs your go-ahead. Test the local backend on an NVIDIA machine or a cloud GPU before release |
| R3 | MOSS-SoundEffect quality and v2.0 license are not verified | Listen-test it in Phase 4 before we endorse it; read the Hugging Face model card for the license; Stable Audio Open Small is the backup |
| R4 | Users must have `uv` installed for the Claude Code plugin | README one-liner to install uv; the plugin detects a missing uv and explains the fix. The Desktop `.mcpb` handles this itself (Spike B confirms) |
| R5 | License confusion for AI-made sounds | Each sidecar records its license; warnings for the ElevenLabs free plan and the Stable Audio $1M cap; FAQ section |
| R6 | API prices and terms change | Never hard-code prices; link to provider pages; status tool shows the current setup |
| R7 | API keys leaking into GitHub | Keys are stored in the OS keychain / Desktop secure settings, never in project files; `.gitignore` + secret scanning in CI |
| R8 | Name confusion: "noisesmith" is also a GitHub username (an unrelated developer) | Low risk; the repo lives at `zimba7768/noisesmith` and the PyPI name is free. Reserve the PyPI name early |

---

## 9. Later (v2+ ideas)
- **claude.ai web version** as an uploadable *skill* (synth only, since numpy/scipy are in claude.ai's sandbox). No server costs
- fal.ai backend (one key, many models, often cheaper)
- A gallery page to browse, audition and re-generate your project's sounds
- "Sound packs": generate a whole consistent set (e.g. all UI sounds for a game) in one prompt
- Game-engine helpers (Godot/Unity/Unreal import presets, sprite sheets of short sounds)

---

## 10. Decisions log
| Date | Decision |
|---|---|
| 2026-10-29 | Name: **NoiseSmith**. License: **MIT** (code), **CC0** (synth output) |
| 2026-10-29 | Targets: **Claude Code plugin + Claude Desktop extension** (MCP server underneath, so other tools also work) |
| 2026-10-29 | Engine: **Hybrid**. Free synth by default; **both** local AI and cloud AI in v1 |
| 2026-10-29 | v1 features: variations, seamless loops, layering/mixing, game/video export |
| 2026-10-29 | Language: Python. The maintainer is new to coding, so the code must be simple and heavily documented |
| 2026-10-29 | **Lesson: some sounds are not worth synthesizing, and metrics are not ears.** The door creak failed six times as pure synthesis (siren, human voice, synth beeper, tape being peeled, a scraped log), even after its spectrum, slip rate and timing were matched to a real recording. Decision: build creaks from real CC0 recordings that are reshaped (door_creak, floor_creak), with credits. Test candidates by letting the owner listen before building. Expect the same for other hard organic sounds (animals, voices, footsteps) |
| 2026-10-29 | Phase 1 built (v0.1.0): synth engine, 6 recipes, 3 tools, skill. Added `scipy` as a dependency. The beep test tool was replaced by the `ui_blip` recipe |
| 2026-10-29 | v0.4.0: wind and rain rebuilt from real CC0 recordings (BigSoundBank, Joseph Sardin) because the synthesized versions "sounded computer generated"; new `thunder` recipe from 8 recordings. 18 clips, 4.7 MB as compact OGG, credited. Beds are levelled by loudness (LUFS) instead of by peak, since single raindrop spikes made peak-based levelling quiet; the stored beds have their sharpest spikes gently squashed. Real wind is a hiss at the gentle end and a deep rumble at the storm end, so "brighter with strength" was wrong and has been removed. The old synthesized wind and rain are gone |
| 2026-10-29 | v0.3.1: fixed a mixer bug found while making the first storm for real. A looped scene is rendered a little longer than asked (room for the crossfade), so layers exactly as long as the scene ran out early and every loop began 9 dB quiet with a 20 dB dip at its end. Wind and rain now fill the whole scene by default and a scene-length layer is stretched to cover the join; regression tests added. The first two demo storms made with v0.3.0 had this flaw |
| 2026-10-29 | v0.3.0 (Phase 2): loops, mixing, formats, loudness. New dependencies: `soundfile` (FLAC/OGG/MP3 read and write) and `pyloudnorm` (the standard BS.1770 loudness meter, used instead of writing our own). A real crash was found by testing through the MCP protocol and fixed: writing a long sound to OGG in one call overflowed the stack and killed the server, so audio is now handed to the encoder in small chunks (regression test added) |
| 2026-10-29 | v0.2.0: creaks rebuilt from 11 CC0 recordings (1.6 MB, credited); new `floor_creak` recipe; engine id is now `builtin` because not every recipe is pure synthesis |
| 2026-10-29 | Phase 0 built: public repo created, `mcp` 2.x server with a beep tool, Claude Code plugin + marketplace, Desktop `.mcpb` build script. Local AI will run as a separate worker environment (see spike results) |

### Research sources (summary)
- Claude Code plugins: https://code.claude.com/docs/en/plugins/publish.md · Desktop extensions: https://claude.com/docs/connectors/building/mcpb.md · https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
- MOSS-SoundEffect: https://github.com/OpenMOSS/MOSS-TTS · Stable Audio Open: https://huggingface.co/stabilityai/stable-audio-open-1.0 · https://stability.ai/license
- ElevenLabs pricing and rights: https://elevenlabs.io/pricing/api · https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform
- Prior art to learn from: https://github.com/Tuntii/make-sfx (MIT, procedural) · https://glama.ai/mcp/servers/JimCline/sfx-gen-mcp
