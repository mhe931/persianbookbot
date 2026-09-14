"""Tests for the Telegram webhook route (``bot.api.telegram_webhook``) and
``bot.main``'s webhook-vs-polling mode selection.

All tests use an ASGI transport (in-process, no real network) and either a
mocked ``telegram.ext.Application`` (secret validation / dispatch tests) or
no application at all (the 503 "not active" and mode-selection tests) - no
real Telegram token, network access, or webhook registration call is ever
made.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from bot import api, config
from bot.config import Settings

SAMPLE_UPDATE = {
    "update_id": 123456789,
    "message": {
        "message_id": 1,
        "date": 1700000000,
        "chat": {"id": 42, "type": "private"},
        "text": "/start",
    },
}


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch):
    """Give every test a hermetic webhook secret and reset the shared
    ``app.state.telegram_application`` so tests can't leak state into
    each other via the module-level FastAPI ``app`` singleton.
    """
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-value")
    config.reset_settings_cache()
    api.app.state.telegram_application = None
    yield
    api.app.state.telegram_application = None
    config.reset_settings_cache()


async def _post_webhook(headers: dict | None = None, json: dict | None = None):
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            api.TELEGRAM_WEBHOOK_PATH, headers=headers or {}, json=json if json is not None else SAMPLE_UPDATE
        )


async def test_webhook_rejects_missing_secret_header_with_401():
    resp = await _post_webhook(headers={})
    assert resp.status_code == 401


async def test_webhook_rejects_wrong_secret_with_403():
    resp = await _post_webhook(headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-value"})
    assert resp.status_code == 403


async def test_webhook_rejects_when_secret_not_configured(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    config.reset_settings_cache()

    # Even a header that would otherwise "match" an empty configured secret
    # must be rejected - an unconfigured secret means the route fails
    # closed, never open.
    resp = await _post_webhook(headers={"X-Telegram-Bot-Api-Secret-Token": ""})
    assert resp.status_code in (401, 403)


async def test_webhook_returns_503_when_no_application_wired():
    resp = await _post_webhook(headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret-value"})
    assert resp.status_code == 503


async def test_webhook_dispatches_valid_update_through_application():
    from telegram import Bot

    # A real (but token-less-network) Bot object is required here because
    # Update.de_json needs a genuine telegram.Bot to build nested Message/
    # Chat objects correctly - a bare MagicMock breaks that parsing. No
    # network call happens merely by constructing Bot(token=...).
    fake_bot = Bot(token="123:FAKE-TEST-TOKEN")
    fake_application = MagicMock()
    fake_application.bot = fake_bot
    fake_application.process_update = AsyncMock()
    api.app.state.telegram_application = fake_application

    resp = await _post_webhook(headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret-value"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    fake_application.process_update.assert_awaited_once()
    # The dispatched object must be a real telegram.Update built from the
    # posted payload, not the raw dict.
    from telegram import Update

    dispatched = fake_application.process_update.await_args.args[0]
    assert isinstance(dispatched, Update)
    assert dispatched.update_id == SAMPLE_UPDATE["update_id"]


async def test_webhook_rejects_malformed_update_payload_with_400():
    from telegram import Bot

    fake_application = MagicMock()
    fake_application.bot = Bot(token="123:FAKE-TEST-TOKEN")
    fake_application.process_update = AsyncMock()
    api.app.state.telegram_application = fake_application

    resp = await _post_webhook(
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret-value"}, json={}
    )

    # An empty/garbage payload cannot parse into telegram.Update.de_json's
    # required fields - must not be silently dispatched.
    assert resp.status_code in (400, 422)
    fake_application.process_update.assert_not_called()


async def test_webhook_never_exposes_configured_secret_in_response():
    resp = await _post_webhook(headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-value"})
    assert "test-secret-value" not in resp.text


def test_settings_expose_webhook_secret_and_default_none(monkeypatch):
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    config.reset_settings_cache()

    settings = config.get_settings()
    assert settings.webhook_secret is None
    assert settings.webhook_url is None


def test_settings_read_webhook_secret_from_environment(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "abc123")
    monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com")
    config.reset_settings_cache()

    settings = config.get_settings()
    assert settings.webhook_secret == "abc123"
    assert settings.webhook_url == "https://bot.example.com"


def test_env_example_documents_webhook_secret_without_a_value():
    from pathlib import Path

    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    assert "WEBHOOK_SECRET=" in content
    for line in content.splitlines():
        if line.startswith("WEBHOOK_SECRET="):
            assert line.strip() == "WEBHOOK_SECRET="


def test_main_selects_polling_when_webhook_url_unset(monkeypatch, tmp_path):
    """``bot.main.main()`` must call the polling-mode helper (not webhook
    mode) whenever ``WEBHOOK_URL`` is unset, even with a bot token
    configured - polling stays the default per the goal's requirements.
    """
    import bot.main as bot_main

    monkeypatch.setenv("BOT_TOKEN", "123:FAKE-TEST-TOKEN")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    config.reset_settings_cache()

    polling_called = MagicMock()
    webhook_called = MagicMock()
    monkeypatch.setattr(bot_main, "_run_polling_mode", polling_called)
    monkeypatch.setattr(bot_main, "_run_webhook_mode", webhook_called)
    monkeypatch.setattr(bot_main, "_run_api_only_mode", MagicMock())

    bot_main.main()

    polling_called.assert_called_once()
    webhook_called.assert_not_called()


def test_main_selects_webhook_mode_when_webhook_url_set(monkeypatch, tmp_path):
    import bot.main as bot_main

    monkeypatch.setenv("BOT_TOKEN", "123:FAKE-TEST-TOKEN")
    monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret-value")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    config.reset_settings_cache()

    polling_called = MagicMock()
    webhook_called = MagicMock()
    monkeypatch.setattr(bot_main, "_run_polling_mode", polling_called)
    monkeypatch.setattr(bot_main, "_run_webhook_mode", webhook_called)
    monkeypatch.setattr(bot_main, "_run_api_only_mode", MagicMock())

    bot_main.main()

    webhook_called.assert_called_once()
    polling_called.assert_not_called()


def test_main_selects_api_only_mode_without_bot_token(monkeypatch, tmp_path):
    import bot.main as bot_main

    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("WEBHOOK_URL", "https://bot.example.com")
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    config.reset_settings_cache()

    polling_called = MagicMock()
    webhook_called = MagicMock()
    api_only_called = MagicMock()
    monkeypatch.setattr(bot_main, "_run_polling_mode", polling_called)
    monkeypatch.setattr(bot_main, "_run_webhook_mode", webhook_called)
    monkeypatch.setattr(bot_main, "_run_api_only_mode", api_only_called)

    bot_main.main()

    api_only_called.assert_called_once()
    polling_called.assert_not_called()
    webhook_called.assert_not_called()
