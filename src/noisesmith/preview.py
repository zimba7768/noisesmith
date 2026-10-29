"""Play a sound file through the computer's speakers (Claude itself can't hear)."""

import shutil
import subprocess
import sys
from pathlib import Path


def play(path: Path) -> str:
    """Start playing a WAV file without waiting for it to finish. Returns a short status."""
    if not path.is_file():
        raise FileNotFoundError(f"No such sound file: {path}")
    if sys.platform == "win32":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return "Playing on the default audio device."
    players = (["afplay"] if sys.platform == "darwin" else ["paplay", "aplay", "ffplay"])
    for name in players:
        exe = shutil.which(name)
        if exe:
            args = [exe, "-nodisp", "-autoexit", str(path)] if name == "ffplay" else [exe, str(path)]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Playing with {name}."
    raise RuntimeError("No audio player found. Open the file in any audio app instead.")
