"""A small listening test of ElevenLabs sound effects on animal prompts.

Purpose: find out, before building anything, whether the AI makes realistic animal sounds and
whether "big" and "small" actually change the sound. Nothing here is part of the NoiseSmith package.

The key is read from the ELEVENLABS_API_KEY environment variable or from the file
~/.noisesmith/elevenlabs.key (a plain text file holding only the key). It is never printed or saved.

    uv run python scripts/spike_elevenlabs.py          # dry run: lists what would be made and the cost
    uv run python scripts/spike_elevenlabs.py --yes    # really generates (this spends credits)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

ENDPOINT = "https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128"
SUBSCRIPTION = "https://api.elevenlabs.io/v1/user/subscription"
KEY_FILE = Path.home() / ".noisesmith" / "elevenlabs.key"
OUT = Path(__file__).resolve().parent.parent / "sounds" / "ai_spike"
DURATION_S = 4.0
PROMPT_INFLUENCE = 0.5
CREDITS_PER_SECOND = 40  # from ElevenLabs' help pages; the dry run and the real usage may differ

PROMPTS = {
    "big_dog": "A very big, large dog barking, deep loud booming bark, outdoors",
    "small_dog": "A small dog barking, high-pitched yappy barks, outdoors",
    "lion_roar": "A lion roaring",
    "songbird": "A songbird singing in a forest at dawn",
    "cat_meow": "A cat meowing",
    "wolf_howl": "A wolf howling at night",
}


def load_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and KEY_FILE.is_file():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        sys.exit(f"No ElevenLabs key found. Set ELEVENLABS_API_KEY, or put the key alone in {KEY_FILE}")
    return key


def call(url: str, key: str, body: dict | None = None) -> bytes:
    request = urllib.request.Request(
        url, data=None if body is None else json.dumps(body).encode(), headers={"xi-api-key": key, "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:  # explain the common failures without echoing anything sensitive
        reasons = {401: "the key was rejected", 402: "payment or plan problem", 422: "the request was rejected as invalid", 429: "too many requests at once or out of credits"}
        sys.exit(f"ElevenLabs returned HTTP {exc.code}: {reasons.get(exc.code, 'unexpected error')}. {exc.read().decode(errors='replace')[:200]}")


def credits_used(key: str):
    """Credits used so far this period, or None if the key is not allowed to read it."""
    try:
        data = json.loads(call(SUBSCRIPTION, key))
        return data.get("character_count"), data.get("character_limit")
    except SystemExit:
        return None, None


def describe(path: Path) -> str:
    """Rough facts about a sound: loudness, brightness, and the pitch of its loudest moments."""
    x, sr = sf.read(str(path), always_2d=True)
    x = x.mean(axis=1)
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / sr)
    centroid = np.sum(freqs * power) / np.sum(power)
    frame = int(0.04 * sr)
    energy = np.array([np.sum(x[i : i + frame] ** 2) for i in range(0, len(x) - frame, frame)])
    pitches = []
    for i in np.flatnonzero(energy > 0.5 * energy.max()):
        seg = x[i * frame : i * frame + frame] - np.mean(x[i * frame : i * frame + frame])
        ac = np.correlate(seg, seg, "full")[len(seg) - 1 :]
        lo, hi = int(sr / 1000), int(sr / 60)
        pitches.append(sr / (lo + np.argmax(ac[lo:hi])))
    pitch = f"{np.median(pitches):.0f} Hz" if pitches else "n/a"
    return f"{len(x)/sr:.1f}s  brightness {centroid:.0f} Hz  pitch of the loudest moments ~{pitch}"


def main() -> None:
    really = "--yes" in sys.argv
    estimate = len(PROMPTS) * DURATION_S * CREDITS_PER_SECOND
    print(f"{len(PROMPTS)} prompts, {DURATION_S:g} s each, about {estimate:.0f} credits in total (ElevenLabs' free plan has 10,000 a month).")
    for name, text in PROMPTS.items():
        print(f"  {name:10s} {text}")
    if not really:
        print("\nDry run: nothing was sent. Re-run with --yes to generate.")
        return

    key = load_key()
    OUT.mkdir(parents=True, exist_ok=True)
    before = credits_used(key)
    for name, text in PROMPTS.items():
        audio = call(ENDPOINT, key, {"text": text, "duration_seconds": DURATION_S, "prompt_influence": PROMPT_INFLUENCE})
        path = OUT / f"{name}.mp3"
        path.write_bytes(audio)
        print(f"  made {path.name:14s} {describe(path)}")
    after = credits_used(key)
    if before[0] is not None and after[0] is not None:
        print(f"\nCredits used by this test: {after[0] - before[0]} (period total {after[0]} of {after[1]}).")
    else:
        print("\n(Could not read the credit balance with this key; check usage on the ElevenLabs website.)")


if __name__ == "__main__":
    main()
