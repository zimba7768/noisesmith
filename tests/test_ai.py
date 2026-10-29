"""The optional ElevenLabs backend, tested against a FAKE service: no internet, no credits spent."""

import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from mcp.server.mcpserver.exceptions import ToolError

from noisesmith import audio, keys, mixing, server
from noisesmith.audio import SAMPLE_RATE as SR
from noisesmith.engines import elevenlabs

KEY = "sk_" + "a1b2c3d4" * 6  # a made-up key for tests: 51 characters, like a real one


def make_mp3(seconds=2.0, pitch=300.0):
    t = np.arange(int(44100 * seconds)) / 44100
    wave = 0.3 * np.sin(2 * np.pi * pitch * t * (1 + 0.5 * t)) * np.exp(-t / 2)
    buffer = io.BytesIO()
    sf.write(buffer, wave, 44100, format="MP3", subtype="MPEG_LAYER_III")
    return buffer.getvalue()


class FakeService:
    """Stands in for ElevenLabs: answers sound requests and account questions."""

    def __init__(self, plan="starter", used=240, limit=31036):
        self.plan, self.used, self.limit = plan, used, limit
        self.sound_calls = []  # (request body, key) for every sound request
        self.failures = []  # errors to raise on the next sound requests
        self.garbage = False

    def __call__(self, url, key, body=None, timeout=120):
        if url == elevenlabs.SUBSCRIPTION_URL:
            return json.dumps({"tier": self.plan, "character_count": self.used, "character_limit": self.limit}).encode()
        assert url == elevenlabs.SOUND_URL
        self.sound_calls.append((body, key))
        if self.failures:
            raise self.failures.pop(0)
        if self.garbage:
            return b"this is not audio"
        seconds = body.get("duration_seconds", 3.0)
        self.used += round(10 * seconds)
        return make_mp3(seconds, pitch=200 + 100 * len(self.sound_calls))


@pytest.fixture
def service(monkeypatch, tmp_path):
    fake = FakeService()
    monkeypatch.setattr(elevenlabs, "_send", fake)
    monkeypatch.setattr(elevenlabs, "_sleep", lambda seconds: None)
    monkeypatch.setattr(keys, "key_dir", lambda: tmp_path / "home" / ".noisesmith")
    monkeypatch.setenv("ELEVENLABS_API_KEY", KEY)
    return fake


def notes_of(path):
    return json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))


# ---- keys -------------------------------------------------------------------------------------


def test_the_key_comes_from_the_environment_or_a_private_file(monkeypatch, tmp_path):
    folder = tmp_path / "keys"
    monkeypatch.setattr(keys, "key_dir", lambda: folder)
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert keys.find_key("elevenlabs") is None
    folder.mkdir()
    (folder / "elevenlabs.key").write_text(f"  {KEY}\r\n", encoding="utf-8")  # stray spaces and a line break are fine
    assert keys.find_key("elevenlabs") == (KEY, f"the file {folder / 'elevenlabs.key'}")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_" + "z" * 40)  # the environment variable wins
    assert keys.find_key("elevenlabs")[0] == "sk_" + "z" * 40


def test_an_unfilled_setting_is_treated_as_no_key(monkeypatch, tmp_path):
    monkeypatch.setattr(keys, "key_dir", lambda: tmp_path)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "${user_config.elevenlabs_api_key}")
    assert keys.find_key("elevenlabs") is None
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    assert keys.find_key("elevenlabs") is None


def test_a_badly_formed_key_is_refused_without_repeating_it(monkeypatch, tmp_path):
    monkeypatch.setattr(keys, "key_dir", lambda: tmp_path)
    for bad in ("sk_has some spaces inside the key text", "short", "x" * 300):
        monkeypatch.setenv("ELEVENLABS_API_KEY", bad)
        with pytest.raises(ValueError, match="does not look like an API key") as error:
            keys.find_key("elevenlabs")
        assert bad not in str(error.value)


# ---- costs and licenses -----------------------------------------------------------------------


def test_cost_estimates_are_generous_and_never_tiny():
    assert elevenlabs.estimate_credits(None) == 200
    assert elevenlabs.estimate_credits(4.0) == 80  # the real test cost 40: the estimate is twice that
    assert elevenlabs.estimate_credits(0.5) == 40


def test_the_license_follows_the_plan():
    assert "NON-COMMERCIAL" in elevenlabs.license_for("free")[1]
    assert "commercial license" in elevenlabs.license_for("starter")[1]
    assert "free plan is NON-COMMERCIAL" in elevenlabs.license_for(None)[1]


# ---- making sounds ----------------------------------------------------------------------------


def test_a_sound_is_made_saved_and_described(service, tmp_path):
    result = server.create_ai_sound("A small dog barking, high-pitched yappy barks, outdoors", duration_s=4, description="a small dog", output_dir=str(tmp_path))
    (info,) = result["files"]
    assert Path(info["path"]).name == "a_small_dog_barking_high-pitched_yappy.wav"
    assert abs(len(audio.read_audio(Path(info["path"]))) - 4 * SR) < 2000
    body, key = service.sound_calls[0]
    assert body == {"text": "A small dog barking, high-pitched yappy barks, outdoors", "prompt_influence": 0.5, "loop": False, "duration_seconds": 4}
    assert key == KEY
    assert result["plan"] == "starter" and result["credits_used"] == 40 and result["estimated_credits"] == 80
    notes = notes_of(info["path"])
    assert notes["engine"] == "elevenlabs" and notes["ai_generated"] is True and notes["repeatable"] is False
    assert notes["prompt"] == "A small dog barking, high-pitched yappy barks, outdoors" and notes["description"] == "a small dog"
    assert "commercial" in notes["output_license"]


def test_a_usage_counter_that_has_not_updated_yet_is_not_reported_as_zero(service, tmp_path):
    original = service.__call__

    class Lagging(FakeService):
        def __call__(self, url, key, body=None, timeout=120):
            result = original(url, key, body, timeout)
            if url == elevenlabs.SOUND_URL:
                self.used = 240  # ElevenLabs has not counted the sound yet
            return result

    service.__class__ = Lagging
    result = server.create_ai_sound("A cat meowing", duration_s=2, output_dir=str(tmp_path))
    assert result["credits_used"] is None and "usage counter" in result["credits_note"]


def test_a_loud_sound_is_given_headroom_instead_of_clipping(service, tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "decode_bytes", lambda content: np.sin(np.arange(SR) * 0.05) * 1.04)  # a decoded MP3 that overshoots
    info = server.create_ai_sound("A loud bark", duration_s=2, output_dir=str(tmp_path))["files"][0]
    assert info["peak_dbfs"] <= -0.9


def test_the_key_never_appears_in_any_output(service, tmp_path):
    result = server.create_ai_sound("A cat meowing", duration_s=2, output_dir=str(tmp_path))
    assert KEY not in json.dumps(result)
    for file in tmp_path.iterdir():
        assert KEY.encode() not in file.read_bytes()
    assert KEY not in json.dumps(server.ai_status())


def test_a_free_plan_gets_the_noncommercial_warning(service, tmp_path):
    service.plan = "free"
    result = server.create_ai_sound("A lion roaring", duration_s=2, output_dir=str(tmp_path))
    assert "NON-COMMERCIAL" in result["license"]
    assert "NON-COMMERCIAL" in notes_of(result["files"][0]["path"])["output_license"]


def test_variations_are_separate_requests_and_files(service, tmp_path):
    result = server.create_ai_sound("A wolf howling", duration_s=2, variations=3, name="wolf", output_dir=str(tmp_path))
    assert [Path(f["path"]).name for f in result["files"]] == ["wolf_01.wav", "wolf_02.wav", "wolf_03.wav"]
    assert len(service.sound_calls) == 3
    assert len({Path(f["path"]).read_bytes() for f in result["files"]}) == 3


def test_estimate_only_spends_nothing(service, tmp_path):
    result = server.create_ai_sound("A bird singing", duration_s=10, variations=2, estimate_only=True, output_dir=str(tmp_path))
    assert result["made_nothing"] is True and result["estimated_credits"] == 400 and result["credits_remaining"] == 31036 - 240
    assert service.sound_calls == [] and list(tmp_path.iterdir()) == []


def test_big_requests_need_the_user_to_agree_first(service, tmp_path):
    with pytest.raises(ToolError, match="confirm_cost=true"):
        server.create_ai_sound("A storm of birds", duration_s=30, variations=2, output_dir=str(tmp_path))
    assert service.sound_calls == []
    server.create_ai_sound("A storm of birds", duration_s=30, variations=2, confirm_cost=True, output_dir=str(tmp_path))
    assert len(service.sound_calls) == 2


def test_it_refuses_when_the_account_has_too_few_credits(service, tmp_path):
    service.used = service.limit - 50
    with pytest.raises(ToolError, match="only 50 are left"):
        server.create_ai_sound("A dog barking", duration_s=4, output_dir=str(tmp_path))
    assert service.sound_calls == []


def test_loops_formats_and_loudness_work_like_the_other_tools(service, tmp_path):
    info = server.create_ai_sound("A hum", duration_s=3, loop=True, format="ogg", loudness="game", output_dir=str(tmp_path))["files"][0]
    assert service.sound_calls[0][0]["loop"] is True
    assert info["path"].endswith(".ogg") and info["loop"] is True and info["lufs"] == pytest.approx(-16.0, abs=0.5)
    wav = server.create_ai_sound("A hum", duration_s=3, loop=True, output_dir=str(tmp_path))["files"][0]["path"]
    assert b"smpl" in Path(wav).read_bytes()[:200]  # loop points for game engines


def test_an_ai_sound_can_be_layered_in_a_mix(service, tmp_path):
    path = server.create_ai_sound("A dog barking", duration_s=2, output_dir=str(tmp_path))["files"][0]["path"]
    result = server.mix_sounds([{"file": path}, {"recipe": "rain", "intensity": 0.5}], duration_s=4, seed=1, output_dir=str(tmp_path))
    assert "depends on the licenses" in result["license"]


# ---- mistakes ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "settings,message",
    [
        ({"prompt": ""}, "prompt cannot be empty"),
        ({"prompt": "x" * 451}, "too long"),
        ({"prompt": "dog", "variations": 0}, "variations must be between"),
        ({"prompt": "dog", "variations": 5}, "variations must be between"),
        ({"prompt": "dog", "duration_s": 0.1}, "duration_s must be between"),
        ({"prompt": "dog", "duration_s": 60}, "duration_s must be between"),
        ({"prompt": "dog", "prompt_influence": 2}, "prompt_influence"),
        ({"prompt": "dog", "format": "aac"}, "Unknown format"),
        ({"prompt": "dog", "loudness": "loud"}, "loudness must be"),
    ],
)
def test_mistakes_are_explained_before_anything_is_spent(service, tmp_path, settings, message):
    with pytest.raises(ToolError, match=message):
        server.create_ai_sound(output_dir=str(tmp_path), **settings)
    assert service.sound_calls == []


def test_without_a_key_it_explains_how_to_set_one_up(monkeypatch, tmp_path):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setattr(keys, "key_dir", lambda: tmp_path / "nokeys")
    with pytest.raises(ToolError, match="not set up yet.*api-keys.*elevenlabs.key"):
        server.create_ai_sound("A dog barking", output_dir=str(tmp_path))
    status = server.ai_status()["elevenlabs"]
    assert status["configured"] is False and "api-keys" in status["setup"]


def test_status_shows_the_plan_and_credits_but_not_the_key(service):
    status = server.ai_status()["elevenlabs"]
    assert status["configured"] is True and status["plan"] == "starter"
    assert status["credits_remaining"] == 31036 - 240 and "commercial license" in status["license"]
    assert "environment variable" in status["key_found_in"]


# ---- when the service misbehaves --------------------------------------------------------------


def test_a_busy_service_is_retried_then_succeeds(service, tmp_path):
    service.failures = [elevenlabs.ServiceError("busy", retryable=True)] * 2
    server.create_ai_sound("A dog barking", duration_s=2, output_dir=str(tmp_path))
    assert len(service.sound_calls) == 3  # two busy answers, then the sound


def test_a_service_that_stays_busy_gives_up_with_a_clear_message(service, tmp_path):
    service.failures = [elevenlabs.ServiceError("ElevenLabs is busy (too many sounds at once).", retryable=True)] * 10
    with pytest.raises(ToolError, match="busy"):
        server.create_ai_sound("A dog barking", duration_s=2, output_dir=str(tmp_path))
    assert len(service.sound_calls) == 4  # the first try plus three retries


def test_other_failures_are_not_retried(service, tmp_path):
    service.failures = [elevenlabs.ServiceError("You are out of ElevenLabs credits for now.")]
    with pytest.raises(ToolError, match="out of ElevenLabs credits"):
        server.create_ai_sound("A dog barking", duration_s=2, output_dir=str(tmp_path))
    assert len(service.sound_calls) == 1


def test_audio_that_is_not_audio_is_reported(service, tmp_path):
    service.garbage = True
    with pytest.raises(ToolError, match="not valid audio"):
        server.create_ai_sound("A dog barking", duration_s=2, output_dir=str(tmp_path))


# ---- how real error responses are understood --------------------------------------------------


def http_error(monkeypatch, code, body):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, code, "error", {}, io.BytesIO(json.dumps(body).encode()))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)


@pytest.mark.parametrize(
    "code,body,message,retryable",
    [
        (401, {"detail": {"status": "invalid_api_key", "message": "Invalid API key"}}, "rejected the API key", False),
        (429, {"detail": {"status": "too_many_concurrent_requests", "message": "Too many"}}, "busy", True),
        (429, {"detail": {"status": "system_busy", "message": "Busy"}}, "busy", True),
        (429, {"detail": {"status": "quota_exceeded", "message": "No credits"}}, "out of ElevenLabs credits", False),
        (403, {"detail": {"status": "missing_permissions", "message": "needs sound_generation"}}, "permissions", False),
        (422, {"detail": {"status": "invalid", "message": "text is too long"}}, "text is too long", False),
        (500, {"detail": "server trouble"}, "HTTP 500", True),
    ],
)
def test_real_error_responses_become_plain_explanations(monkeypatch, code, body, message, retryable):
    http_error(monkeypatch, code, body)
    with pytest.raises(elevenlabs.ServiceError, match=message) as error:
        elevenlabs._send(elevenlabs.SOUND_URL, KEY, {"text": "dog"})
    assert error.value.retryable is retryable
    assert KEY not in str(error.value)


def test_a_missing_connection_is_explained(monkeypatch):
    def offline(request, timeout=None):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", offline)
    with pytest.raises(elevenlabs.ServiceError, match="Could not reach ElevenLabs"):
        elevenlabs._send(elevenlabs.SOUND_URL, KEY, {"text": "dog"})


def test_account_information_is_optional(monkeypatch):
    def fail(url, key, body=None, timeout=30):
        raise elevenlabs.ServiceError("no")

    monkeypatch.setattr(elevenlabs, "_send", fail)
    assert elevenlabs.account(KEY) is None
