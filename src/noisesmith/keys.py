"""Where NoiseSmith finds the API keys that you give it.

A key is looked for in two places, in this order:
  1. an environment variable (for ElevenLabs: ELEVENLABS_API_KEY);
  2. a private file in your home folder (for ElevenLabs: ~/.noisesmith/elevenlabs.key).
The file should hold only the key. NoiseSmith never saves, prints, logs or sends a key anywhere
except to the service it belongs to, and never writes it into a sound's notes file.
"""

import os
from pathlib import Path

PROVIDERS = {"elevenlabs": ("ELEVENLABS_API_KEY", "elevenlabs.key")}


def key_dir() -> Path:
    """The private folder for key files (outside any project, so it cannot be committed by accident)."""
    return Path.home() / ".noisesmith"


def find_key(provider: str):
    """Return (key, where_it_came_from), or None if no key is set up. Raises if a key looks wrong."""
    env_name, file_name = PROVIDERS[provider]
    candidates = [(f"the {env_name} environment variable", os.environ.get(env_name, ""))]
    path = key_dir() / file_name
    try:
        candidates.append((f"the file {path}", path.read_text(encoding="utf-8")))
    except OSError:
        pass
    for source, raw in candidates:
        value = raw.strip()
        if not value or "${" in value:  # empty, or a setting the app never filled in
            continue
        if any(ch.isspace() for ch in value) or not 20 <= len(value) <= 200:
            raise ValueError(
                f"The key found in {source} does not look like an API key (it has spaces or line breaks, "
                "or is the wrong length). Save only the key itself, with nothing else."
            )
        return value, source
    return None


def setup_help(provider: str) -> str:
    env_name, file_name = PROVIDERS[provider]
    path = key_dir() / file_name
    return (
        "To set up ElevenLabs: create an API key at https://elevenlabs.io/app/api/api-keys "
        "(it helps to give the key a credit limit), then save ONLY the key in the file "
        f"{path} (in Windows PowerShell: notepad \"$HOME\\.noisesmith\\{file_name}\"), or set the "
        f"{env_name} environment variable. Do not paste the key into a chat."
    )
