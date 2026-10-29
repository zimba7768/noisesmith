"""Prepare the recorded wind, rain and thunder used by the wind, rain and thunder recipes.

Each source recording (all CC0, from bigsoundbank.com; see src/noisesmith/assets/ambience/CREDITS.md)
becomes a small, consistent file: mono, 48 kHz, saved as compact OGG.
  * Wind and rain ("beds"): the calmest stretch of up to 40 seconds (the part with the fewest
    bumps, bird calls and sudden loud events), leveled to -23 LUFS so different recordings mix evenly,
    with the very sharpest spikes (single big raindrops) gently squashed to about 15 dB above that.
  * Thunder: the whole clip with silence trimmed, leveled to -1 dBFS peak (peaks are the point).

The original downloads are not in this repository. To re-run, download the MP3 files listed in
CREDITS.md from bigsoundbank.com (https://bigsoundbank.com/UPLOAD/mp3/<number>.mp3) into one folder
and run, from the repository root:

    uv run python scripts/prepare_ambience_assets.py <folder with the numbered .mp3 files>
"""

import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import signal

from noisesmith.dsp.loudness import soft_limit

TARGET_SR = 48000
BED_SECONDS = 40
OUT = Path(__file__).resolve().parent.parent / "src" / "noisesmith" / "assets" / "ambience"

# output id -> BigSoundBank sound number
BEDS = {
    "wind_light_grass": "0908",
    "wind_light_window": "0147",
    "wind_strong_trees_1": "1450",
    "wind_strong_trees_3": "1452",
    "wind_strong_leaves": "0154",
    "wind_strong_inside": "1714",
    "wind_whistle_chimney": "0155",
    "rain_soft_umbrella": "2679",
    "rain_hard_concrete": "1289",
    "rain_heavy_terrace": "1019",
}
THUNDER = {f"thunder_{n}": n for n in ("2718", "3115", "3181", "3113", "3114", "3116", "3179", "3180")}


def load_mono(path: Path) -> np.ndarray:
    data, rate = sf.read(str(path), always_2d=True, dtype="float64")
    mono = data.mean(axis=1)
    if rate != TARGET_SR:
        ratio = Fraction(TARGET_SR, rate).limit_denominator(1000)
        mono = signal.resample_poly(mono, ratio.numerator, ratio.denominator)
    return mono - np.mean(mono)


def calmest_window(x: np.ndarray, seconds: float) -> np.ndarray:
    """The stretch with the steadiest loudness: its loudest moment is closest to its typical level."""
    n = int(seconds * TARGET_SR)
    if len(x) <= n:
        return x
    frame = int(0.05 * TARGET_SR)
    rms = np.sqrt(np.mean(x[: len(x) // frame * frame].reshape(-1, frame) ** 2, axis=1))
    frames_per_window, best, best_start = int(seconds / 0.05), np.inf, 0
    for start in range(0, len(rms) - frames_per_window, int(1.0 / 0.05)):  # try a start every second
        window = rms[start : start + frames_per_window]
        score = window.max() / (np.median(window) + 1e-9)
        if score < best:
            best, best_start = score, start
    first = best_start * frame
    return x[first : first + n]


BED_LUFS = -23.0
BED_MAX_CREST_DB = 15.0  # loudest moments may sit at most this far above the average level


def prepare_bed(x: np.ndarray) -> np.ndarray:
    """The calmest stretch, leveled to -23 LUFS, with the sharpest spikes (single big raindrops,
    a gust slapping the microphone) gently squashed so that loudness, not one spike, sets the level."""
    x = calmest_window(x, BED_SECONDS)
    meter = pyloudnorm.Meter(TARGET_SR)
    for _ in range(4):  # squash spikes, then re-level, until both are right
        x = x * 10 ** ((BED_LUFS - meter.integrated_loudness(x)) / 20)
        x = soft_limit(x, BED_LUFS + BED_MAX_CREST_DB)
    return x


def prepare_thunder(x: np.ndarray) -> np.ndarray:
    loud = np.flatnonzero(np.abs(x) > 0.01 * np.max(np.abs(x)))
    pad = int(0.05 * TARGET_SR)
    x = x[max(loud[0] - pad, 0) : loud[-1] + pad]
    x = x / np.max(np.abs(x)) * 10 ** (-1 / 20)
    fade_in, fade_out = int(0.005 * TARGET_SR), int(0.1 * TARGET_SR)
    x[:fade_in] *= np.linspace(0, 1, fade_in)
    x[-fade_out:] *= np.linspace(1, 0, fade_out)
    return x


def save(path: Path, x: np.ndarray) -> None:
    data = x.astype("float32")
    with sf.SoundFile(str(path), mode="w", samplerate=TARGET_SR, channels=1, format="OGG", subtype="VORBIS", compression_level=0.6) as out:
        for start in range(0, len(data), 16384):  # small pieces: one big write crashes the OGG encoder
            out.write(data[start : start + 16384])


def main() -> None:
    sources = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, number in {**BEDS, **THUNDER}.items():
        x = load_mono(sources / f"{number}.mp3")
        x = prepare_bed(x) if name in BEDS else prepare_thunder(x)
        path = OUT / f"{name}.ogg"
        save(path, x)
        total += path.stat().st_size
        print(f"{name:22s} s{number}  {len(x)/TARGET_SR:5.1f}s  {path.stat().st_size/1000:6.0f} KB")
    print(f"total {total/1e6:.2f} MB")


if __name__ == "__main__":
    main()
