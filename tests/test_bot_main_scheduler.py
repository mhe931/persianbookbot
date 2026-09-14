"""Tests for ``bot.main.periodic_cleanup_worker`` and the related
``Settings.cleanup_interval_seconds`` configuration.

All tests use a fake/mocked ``JobManager`` and short/zero intervals so the
suite stays fast, offline, and credential-free - no real Telegram token,
network access, or Docker/container runtime is ever required.
"""
from __future__ import annotations

import asyncio

import pytest

from bot.config import Settings, get_settings, reset_settings_cache
from bot.main import periodic_cleanup_worker


class _FakeJobManager:
    """Records ``cleanup_stale_jobs()`` calls without touching real jobs/files."""

    def __init__(self, *, fail_times: int = 0) -> None:
        self.call_count = 0
        self._fail_times = fail_times

    async def cleanup_stale_jobs(self):
        self.call_count += 1
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("simulated cleanup failure")
        return None


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_cleanup_interval_seconds_defaults_to_one_hour(monkeypatch):
    monkeypatch.delenv("CLEANUP_INTERVAL_SECONDS", raising=False)
    reset_settings_cache()

    settings = get_settings()

    assert settings.cleanup_interval_seconds == 60 * 60
    reset_settings_cache()


def test_cleanup_interval_seconds_reads_from_environment(monkeypatch):
    monkeypatch.setenv("CLEANUP_INTERVAL_SECONDS", "300")
    reset_settings_cache()

    settings = get_settings()

    assert settings.cleanup_interval_seconds == 300
    reset_settings_cache()


async def test_periodic_cleanup_worker_disabled_when_interval_non_positive():
    manager = _FakeJobManager()
    settings = _settings(cleanup_interval_seconds=0)

    # Should return immediately without ever invoking cleanup, and without
    # needing to be cancelled.
    await asyncio.wait_for(periodic_cleanup_worker(manager, settings), timeout=1.0)

    assert manager.call_count == 0


async def test_periodic_cleanup_worker_runs_cleanup_on_each_tick():
    manager = _FakeJobManager()
    settings = _settings(cleanup_interval_seconds=0.01)
    stop_event = asyncio.Event()

    task = asyncio.ensure_future(
        periodic_cleanup_worker(manager, settings, stop_event=stop_event)
    )
    try:
        # Give the worker a few ticks to run cleanup at least twice.
        for _ in range(50):
            if manager.call_count >= 2:
                break
            await asyncio.sleep(0.02)
        assert manager.call_count >= 2
    finally:
        stop_event.set()
        await asyncio.wait_for(task, timeout=1.0)


async def test_periodic_cleanup_worker_stops_via_stop_event():
    manager = _FakeJobManager()
    settings = _settings(cleanup_interval_seconds=0.01)
    stop_event = asyncio.Event()

    task = asyncio.ensure_future(
        periodic_cleanup_worker(manager, settings, stop_event=stop_event)
    )
    await asyncio.sleep(0.03)
    stop_event.set()

    # The task should complete cleanly (no exception) once stop_event fires.
    await asyncio.wait_for(task, timeout=1.0)
    assert task.done()
    assert task.exception() is None


async def test_periodic_cleanup_worker_can_be_cancelled():
    manager = _FakeJobManager()
    settings = _settings(cleanup_interval_seconds=100)

    task = asyncio.ensure_future(periodic_cleanup_worker(manager, settings))
    await asyncio.sleep(0.01)  # let it enter the wait.

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert task.cancelled()


async def test_periodic_cleanup_worker_survives_cleanup_errors():
    manager = _FakeJobManager(fail_times=2)
    settings = _settings(cleanup_interval_seconds=0.01)
    stop_event = asyncio.Event()

    task = asyncio.ensure_future(
        periodic_cleanup_worker(manager, settings, stop_event=stop_event)
    )
    try:
        for _ in range(50):
            if manager.call_count >= 3:
                break
            await asyncio.sleep(0.02)
        # Two failures followed by at least one successful sweep - the
        # worker must keep running rather than dying on the first error.
        assert manager.call_count >= 3
    finally:
        stop_event.set()
        await asyncio.wait_for(task, timeout=1.0)
