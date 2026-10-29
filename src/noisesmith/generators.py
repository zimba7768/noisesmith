"""Custom sounds built from simple parts: noise or a tone, filters, and a volume envelope.

This is for sounds no ready-made recipe covers: machinery, sci-fi effects, alarms, hums.
A generator is described by a small dictionary (a "spec"), for example a laser zap:

    {"type": "tone", "wave": "saw", "freq_hz": {"from": 2400, "to": 200}, "duration_s": 0.3,
     "envelope": {"attack_s": 0.002, "decay_s": 0.1}}

Fields (all but `type` are optional):
    type          "noise" or "tone"
    duration_s    length in seconds (default 1)
    color         noise only: "white" (bright hiss), "pink" (natural), "brown" (deep rumble)
    wave          tone only: "sine", "triangle", "square" or "saw"
    freq_hz       tone only: a pitch, or {"from": hz, "to": hz} for a glide
    vibrato_hz    tone only: wobble speed (0 = none), with vibrato_depth as a fraction (0.02 = 2%)
    filters       a list of {"type": "lowpass" | "highpass" | "bandpass", "freq_hz": hz, "q": n}.
                  Only a bandpass may sweep: "freq_hz": {"from": hz, "to": hz}. q: about 0.7 is wide
                  and airy, 10 or more is a narrow whistle.
    envelope      {"attack_s": seconds to fade in, "hold_s": seconds at full level,
                   "decay_s": time for the sound to die away (about 37% left after this long),
                   "release_s": seconds to fade out at the end}

Every generated sound is levelled to a peak of -6 dBFS; use a layer's gain_db to change that.
"""

import numpy as np

from noisesmith.dsp import oscillators
from noisesmith.dsp.filters import bandpass, highpass, lowpass, resonator, swept_bandpass
from noisesmith.dsp.levels import db_to_amp
from noisesmith.dsp.noise import brown, pink, white

SPEC_KEYS = {"type", "duration_s", "color", "wave", "freq_hz", "vibrato_hz", "vibrato_depth", "filters", "envelope"}
FILTER_KEYS = {"type", "freq_hz", "q", "order"}
ENVELOPE_KEYS = {"attack_s", "hold_s", "decay_s", "release_s"}
NOISE_COLORS = {"white": lambda n, rng, sr: white(n, rng), "pink": lambda n, rng, sr: pink(n, rng), "brown": brown}
MAX_DURATION_S = 60.0


def _check_keys(spec: dict, allowed: set, where: str) -> None:
    unknown = sorted(set(spec) - allowed)
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {', '.join(unknown)}. Allowed: {', '.join(sorted(allowed))}")


def _number(value, name: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, not {value!r}") from None
    if not low <= number <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return number


def _frequency(value, n: int, name: str, allow_glide: bool = True) -> np.ndarray:
    """A per-sample frequency curve from a single pitch or a {"from", "to"} glide."""
    if isinstance(value, dict):
        if not allow_glide:
            raise ValueError(f"{name} cannot glide here; give a single number")
        _check_keys(value, {"from", "to"}, name)
        start, end = _number(value.get("from"), f"{name}.from", 20, 20000), _number(value.get("to"), f"{name}.to", 20, 20000)
        return start * (end / start) ** np.linspace(0.0, 1.0, n)
    return np.full(n, _number(value, name, 20, 20000))


def _envelope(spec: dict | None, n: int, sr: int) -> np.ndarray:
    spec = spec or {}
    _check_keys(spec, ENVELOPE_KEYS, "envelope")
    attack = _number(spec.get("attack_s", 0.005), "envelope.attack_s", 0, 30)
    hold = _number(spec.get("hold_s", 0.0), "envelope.hold_s", 0, 60)
    decay = spec.get("decay_s")
    release = _number(spec.get("release_s", 0.02), "envelope.release_s", 0, 30)
    t = np.arange(n) / sr
    env = np.minimum(1.0, t / max(attack, 1e-4))
    if decay is not None:
        after = np.maximum(t - attack - hold, 0.0)
        env = env * np.exp(-after / max(_number(decay, "envelope.decay_s", 0.001, 60), 1e-4))
    return env * np.minimum(1.0, (n / sr - t) / max(release, 1e-4))


def _apply_filter(x: np.ndarray, spec: dict, index: int, sr: int) -> np.ndarray:
    where = f"filters[{index}]"
    _check_keys(spec, FILTER_KEYS, where)
    kind = spec.get("type")
    if kind not in ("lowpass", "highpass", "bandpass"):
        raise ValueError(f"{where}: type must be lowpass, highpass or bandpass")
    if "freq_hz" not in spec:
        raise ValueError(f"{where}: freq_hz is required")
    order = int(_number(spec.get("order", 2), f"{where}.order", 1, 6))
    if kind == "bandpass":
        q = _number(spec.get("q", 1.0), f"{where}.q", 0.2, 60)
        freq = _frequency(spec["freq_hz"], len(x), f"{where}.freq_hz")
        if np.ptp(freq) < 1e-9:
            return resonator(x, float(freq[0]), q, sr)
        return swept_bandpass(x, freq, q, sr)
    freq = float(_frequency(spec["freq_hz"], 1, f"{where}.freq_hz", allow_glide=False)[0])
    return (lowpass if kind == "lowpass" else highpass)(x, freq, sr, order=order)


def render(spec: dict, rng: np.random.Generator, sr: int, default_duration_s: float = 1.0) -> np.ndarray:
    """Make one custom sound from a spec (see the module description)."""
    if not isinstance(spec, dict):
        raise ValueError("a generator must be a dictionary like {\"type\": \"noise\", \"color\": \"pink\"}")
    _check_keys(spec, SPEC_KEYS, "generator")
    kind = spec.get("type")
    if kind not in ("noise", "tone"):
        raise ValueError("generator.type must be 'noise' or 'tone'")
    duration = _number(spec.get("duration_s", default_duration_s), "generator.duration_s", 0.01, MAX_DURATION_S)
    n = int(duration * sr)

    if kind == "noise":
        color = spec.get("color", "white")
        if color not in NOISE_COLORS:
            raise ValueError(f"generator.color must be one of {', '.join(NOISE_COLORS)}")
        x = NOISE_COLORS[color](n, rng, sr)
    else:
        freq = _frequency(spec.get("freq_hz", 440.0), n, "generator.freq_hz")
        vibrato = _number(spec.get("vibrato_hz", 0.0), "generator.vibrato_hz", 0, 100)
        if vibrato:
            depth = _number(spec.get("vibrato_depth", 0.02), "generator.vibrato_depth", 0, 0.5)
            freq = freq * (1 + depth * np.sin(2 * np.pi * vibrato * np.arange(n) / sr))
        x = oscillators.wave(freq, spec.get("wave", "sine"), sr)

    filters = spec.get("filters", [])
    if not isinstance(filters, list):
        raise ValueError("generator.filters must be a list")
    for index, filter_spec in enumerate(filters):
        x = _apply_filter(x, filter_spec, index, sr)

    x = x * _envelope(spec.get("envelope"), n, sr)
    peak = np.max(np.abs(x))
    return x if peak == 0 else x / peak * db_to_amp(-6.0)
