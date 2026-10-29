"""The small notes file saved next to every sound, recording how it was made."""

import json
from datetime import datetime, timezone
from pathlib import Path

from noisesmith import __version__


def write_sidecar(audio_path: Path, info: dict) -> Path:
    """Save `<sound>.json` beside the audio file. It lets anyone re-create the exact sound."""
    path = audio_path.with_suffix(".json")
    record = {
        "noisesmith_version": __version__,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": audio_path.name,
        **info,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path
