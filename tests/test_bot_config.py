"""Tests for environment-driven configuration loading (``bot.config``)."""
from __future__ import annotations

from bot.config import Settings, get_settings, reset_settings_cache


def test_settings_default_bot_token_is_none_and_safe(monkeypatch):
    # Ensure no ambient BOT_TOKEN leaks in from the real environment.
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    reset_settings_cache()

    settings = get_settings()

    assert settings.bot_token is None
    assert settings.api_port == 8000
    assert settings.ocr_engine == "dummy"
    assert settings.max_file_size_mb == 20

    reset_settings_cache()


def test_get_settings_is_cached(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    reset_settings_cache()

    first = get_settings()
    second = get_settings()

    assert first is second
    reset_settings_cache()


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:FAKE-TEST-TOKEN")
    monkeypatch.setenv("API_PORT", "9001")
    monkeypatch.setenv("OCR_ENGINE", "tesseract")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "5")
    reset_settings_cache()

    settings = get_settings()

    assert settings.bot_token == "123:FAKE-TEST-TOKEN"
    assert settings.api_port == 9001
    assert settings.ocr_engine == "tesseract"
    assert settings.max_file_size_mb == 5

    reset_settings_cache()


def test_settings_can_be_constructed_directly_without_env():
    settings = Settings(output_dir="/tmp/out", upload_dir="/tmp/up")
    assert settings.bot_token is None
    assert settings.output_dir == "/tmp/out"


def test_env_example_has_no_hardcoded_secrets():
    from pathlib import Path

    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    assert "BOT_TOKEN=" in content
    # The token line itself must be an empty placeholder, not a real value.
    for line in content.splitlines():
        if line.startswith("BOT_TOKEN="):
            assert line.strip() == "BOT_TOKEN="
