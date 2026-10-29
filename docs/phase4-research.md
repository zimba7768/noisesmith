# Phase 4 research: AI sound backends (2026-10-29)

Nothing was downloaded, installed or signed up for during this research. Items marked **unverified**
came from a single source or were not confirmed. Prices and terms change: always link to the
official pages, never hard-code a price.

## Cloud

### ElevenLabs Sound Effects (recommended default)
- `POST https://api.elevenlabs.io/v1/sound-generation`, header `xi-api-key`. Body: `text`, `duration_seconds`
  (0.5 to 30; automatic if unset), `prompt_influence` (0 to 1, default 0.3), `loop` (bool), `model_id`.
  Query `output_format`, default `mp3_44100_128`; 44.1 kHz WAV/PCM needs a Pro plan or above.
  Official Python SDK: `elevenlabs`. Docs: https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
- **Price, sources disagree:** 40 credits per second when a duration is set, or 200 credits per generation
  without one. The free plan is 10,000 credits a month. Budget roughly $0.06 to $0.12 per sound and
  verify at runtime. https://elevenlabs.io/pricing and https://elevenlabs.io/pricing/api
- **Licence of the output:** the free plan "does not include a commercial license and cannot be used for
  any commercial purpose", and needs attribution; paid plans include a commercial license.
  https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform
- **An open-source tool using the user's own key:** no explicit permission or ban found. Their API terms say
  keys may be used "only in environments you control" and must not be shared outside the organisation.
  A local tool using the end user's own key, shipping none of ours, fits this. Never bundle a key.
  https://elevenlabs.io/elevenapi-terms
- Rate limits are about concurrency (2 parallel requests on free), so retry on HTTP 429.
- **Animals:** nothing in the official docs about animal sounds, size, age or distance. Whether
  "big dog" versus "small dog" is respected is **untested**. That is what the first spike checks.

### Alternatives
- **Stability AI Stable Audio 3 API:** about $0.08 per generation (a price cut on 2026-10-23 was reported
  by a third party; **unverified**), 1 to 380 s, mp3 or wav, outputs owned by the user, and a small free
  credit grant. Animal quality **unverified**. https://docs.stability.ai/pricing
- **fal.ai** is a possible one-key gateway to both. **MMAudio is excluded**: its weights are CC-BY-NC.
- **Replicate / Hugging Face:** no first-party sound-effect model; licences depend on each model.
- No provider with a free tier that clearly allows commercial use of the output was confirmed.

## Local

### MOSS-SoundEffect v2.0 (recommended local model)
- Weights **Apache-2.0**, ungated, about 11.2 GB for the official PyTorch release. 1.3B-parameter model,
  48 kHz, up to 30 s. Official support is **CUDA only** (torch 2.9, Python 3.12, `torch.compile` with Triton).
  https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0
- **Better path for AMD and Windows: `pwilkin/openmoss`**, a C++/GGML port, Apache-2.0, with prebuilt Windows
  zips (Vulkan 15.9 MB, ROCm 43 MB, CUDA 650 MB; release v0.3.0). The ROCm and CUDA builds are "best-effort".
  Models: `ilintar/moss-soundeffect-gguf`, about 4.07 GB backbone plus 1.67 GB sidecar (do **not** quantize
  the backbone). It has a command-line tool and an HTTP server (`POST /sfx`). The only timing found is
  about 90 s for 3 s of audio on an AMD Radeon 8060S over Vulkan; a 7900 XT is guessed at 30 to 60 s
  (**unverified**). Young project: one request at a time. https://github.com/pwilkin/openmoss
- **Animal quality: no independent evaluation found.** A listening test is needed.

### Stable Audio 3 Small-SFX
- Open weights, **gated** (needs a Hugging Face login and accepting terms), Stability AI Community
  License (free for organisations under $1M a year in revenue; Gemma terms for the text encoder).
  About 2.3 GB plus a 1.2 GB encoder. `sa3.cpp` GGUF runs on CPU, CUDA and Vulkan (374 MB to 1.08 GB);
  Windows build **unverified**. Fast (seconds). Animal quality **unverified**. A good optional second backend.

### Excluded
AudioGen, AudioLDM 2, Tango, MMAudio and Sony Woosh weights are non-commercial. MiDashengLM-Gen is
permissive but outputs only 16 kHz and is a poor fit.

## What NoiseSmith must tell users, on every AI sound
1. Cloud sounds cost money on the user's own account: show an estimate before each call, support a per-call cap.
2. ElevenLabs free-plan output is non-commercial and needs attribution; paid plans include a commercial licence.
3. Stable Audio models carry the $1M revenue cap. Never use non-commercial models.
4. Keys come from an environment variable or a key file outside the repository, and are never logged.
5. Realism of animals is not guaranteed: preview before use.
6. The licence that applies to each file is written in its notes file.
