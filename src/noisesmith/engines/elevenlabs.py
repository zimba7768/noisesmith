"""The ElevenLabs sound-effects backend (optional, paid by the user's own account).

NoiseSmith never ships a key. The user supplies their own (see keys.py), so every sound is billed to
their ElevenLabs account and their plan decides how the result may be used.
Terms: https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform
"""

import json
import time
import urllib.error
import urllib.request

ENGINE_NAME = "elevenlabs"
BASE_URL = "https://api.elevenlabs.io"
SOUND_URL = BASE_URL + "/v1/sound-generation?output_format=mp3_44100_128"
SUBSCRIPTION_URL = BASE_URL + "/v1/user/subscription"
TERMS_URL = "https://elevenlabs.io/docs/help-center/legal/can-i-publish-the-content-i-generate-on-the-platform"
KEYS_URL = "https://elevenlabs.io/app/api/api-keys"

MIN_DURATION_S, MAX_DURATION_S = 0.5, 30.0
MAX_PROMPT_CHARS = 450
# The first real test cost 40 credits for a 4 second sound (10 a second). ElevenLabs' own pages say
# anything from 200 credits per sound to 40 a second, so estimates are deliberately generous.
ESTIMATE_CREDITS_PER_SECOND = 20
ESTIMATE_AUTOMATIC_LENGTH_CREDITS = 200
RETRY_DELAYS_S = (1.0, 2.0, 4.0)  # when the service is busy


class ServiceError(RuntimeError):
    """Something went wrong talking to ElevenLabs. The message is safe to show: it never contains a key."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


_sleep = time.sleep  # replaced in tests


def _send(url: str, key: str, body: dict | None = None, timeout: float = 120) -> bytes:
    """One request to ElevenLabs. Turns every failure into a ServiceError with a plain explanation."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read(4000).decode("utf-8", errors="replace")
        status, message = "", raw[:200]
        try:
            detail = json.loads(raw).get("detail", "")
            if isinstance(detail, dict):
                status, message = detail.get("status", ""), detail.get("message", message)
            elif isinstance(detail, str):
                message = detail
        except (ValueError, AttributeError):
            pass
        code = exc.code
        if code == 401:
            raise ServiceError("ElevenLabs rejected the API key. It may be mistyped, deleted or restricted; check the saved key.") from None
        if code == 429 and (status in ("too_many_concurrent_requests", "system_busy") or "concurrent" in message.lower()):
            raise ServiceError("ElevenLabs is busy (too many sounds at once).", retryable=True) from None
        if code == 429 or "quota" in status.lower():
            raise ServiceError("You are out of ElevenLabs credits for now (or the key's own credit limit was reached).") from None
        if code in (402, 403):
            raise ServiceError(f"ElevenLabs refused this: the plan or the key's permissions do not allow it. {message}".strip()) from None
        if code == 422:
            raise ServiceError(f"ElevenLabs rejected the request: {message}") from None
        raise ServiceError(f"ElevenLabs returned an error (HTTP {code}). {message}".strip(), retryable=code >= 500) from None
    except urllib.error.URLError:
        raise ServiceError("Could not reach ElevenLabs. Check the internet connection and try again.") from None
    except TimeoutError:
        raise ServiceError("ElevenLabs took too long to answer.", retryable=True) from None


def estimate_credits(duration_s: float | None) -> int:
    """A generous guess of the credits one sound will use, for showing before spending anything."""
    if duration_s is None:
        return ESTIMATE_AUTOMATIC_LENGTH_CREDITS
    return max(40, round(duration_s * ESTIMATE_CREDITS_PER_SECOND))


def account(key: str) -> dict | None:
    """The user's plan and credit balance, or None if the key may not read it (that is not an error)."""
    try:
        data = json.loads(_send(SUBSCRIPTION_URL, key, timeout=30))
        used, limit = data.get("character_count"), data.get("character_limit")
        return {
            "plan": data.get("tier") or "unknown",
            "credits_used": used,
            "credits_limit": limit,
            "credits_remaining": None if used is None or limit is None else limit - used,
        }
    except (ServiceError, ValueError, AttributeError):
        return None


def generate(key: str, prompt: str, duration_s: float | None, prompt_influence: float, loop: bool) -> bytes:
    """Ask ElevenLabs for one sound; returns MP3 bytes. Retries a few times if the service is busy."""
    body = {"text": prompt, "prompt_influence": prompt_influence, "loop": loop}
    if duration_s is not None:
        body["duration_seconds"] = duration_s
    for attempt in range(len(RETRY_DELAYS_S) + 1):
        try:
            return _send(SOUND_URL, key, body)
        except ServiceError as exc:
            if not exc.retryable or attempt == len(RETRY_DELAYS_S):
                raise
            _sleep(RETRY_DELAYS_S[attempt])
    raise AssertionError("unreachable")


def license_for(plan: str | None) -> tuple[str, str]:
    """(short label, plain explanation) of how a sound made on this plan may be used."""
    if plan in (None, "unknown"):
        return (
            "elevenlabs: depends on your plan",
            f"Could not tell which ElevenLabs plan this is. The free plan is NON-COMMERCIAL and needs credit to ElevenLabs; paid plans include a commercial license. Check {TERMS_URL}",
        )
    if plan == "free":
        return (
            "elevenlabs-free-plan: NON-COMMERCIAL, attribution required",
            f"Made on the ElevenLabs FREE plan: NON-COMMERCIAL use only, and it needs a credit to ElevenLabs. A paid plan includes a commercial license. See {TERMS_URL}",
        )
    return (
        f"elevenlabs-{plan}-plan: commercial use allowed under ElevenLabs' terms",
        f"Made on the ElevenLabs {plan.upper()} plan, which includes a commercial license under ElevenLabs' terms (not legal advice; check them: {TERMS_URL}).",
    )
