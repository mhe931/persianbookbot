"""Tests for the FastAPI Mini App backend (``bot.api``): upload/status/
download flow, oversized/non-PDF rejection, and 404 handling. Uses an ASGI
transport (in-process, mocked file transfer) - no real network calls.
"""
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from bot import api, config


@pytest.fixture(autouse=True)
def isolate_settings(tmp_path, monkeypatch):
    """Point the API at a scratch output/upload dir for every test."""
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("OCR_ENGINE", "dummy")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "20")
    config.reset_settings_cache()
    yield
    config.reset_settings_cache()


async def _wait_for_terminal_status(client: AsyncClient, job_id: str, timeout: float = 10.0) -> dict:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        resp = await client.get(f"/api/status/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("done", "failed", "rate_limited"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError(f"job {job_id} did not reach a terminal status in time")


async def test_upload_status_download_flow(sample_pdf_bytes):
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        upload_resp = await client.post("/api/upload", files=files)

        assert upload_resp.status_code == 200
        job_id = upload_resp.json()["job_id"]
        assert job_id

        data = await _wait_for_terminal_status(client, job_id)
        assert data["status"] == "done", data

        for fmt in ("txt", "docx", "epub"):
            download_resp = await client.get(f"/api/download/{job_id}/{fmt}")
            assert download_resp.status_code == 200
            assert len(download_resp.content) > 0


async def test_get_config_reports_max_size_and_formats(monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "20")
    config.reset_settings_cache()

    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_file_size_mb"] == 20
        assert set(data["formats"]) == {"txt", "docx", "epub"}


async def test_status_includes_output_sizes_when_done(sample_pdf_bytes):
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        upload_resp = await client.post("/api/upload", files=files)
        job_id = upload_resp.json()["job_id"]

        data = await _wait_for_terminal_status(client, job_id)
        assert data["status"] == "done", data
        assert set(data["output_sizes"]) == {"txt", "docx", "epub"}
        for size in data["output_sizes"].values():
            assert size > 0


async def test_upload_rejects_non_pdf_content():
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("notes.txt", b"plain text content", "text/plain")}
        resp = await client.post("/api/upload", files=files)
        assert resp.status_code == 400


async def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "0")
    config.reset_settings_cache()

    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("sample.pdf", b"%PDF-1.4 fake content" * 100, "application/pdf")}
        resp = await client.post("/api/upload", files=files)
        assert resp.status_code == 413


async def test_static_frontend_serves_index_and_app_js():
    """Mini App static assets (web/index.html, web/app.js) are served from
    the catch-all mount registered after the /api/... routes in bot.api.
    """
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        index_resp = await client.get("/")
        assert index_resp.status_code == 200
        assert "text/html" in index_resp.headers["content-type"]
        assert "مبدل کتاب فارسی" in index_resp.text

        app_js_resp = await client.get("/app.js")
        assert app_js_resp.status_code == 200
        assert "javascript" in app_js_resp.headers["content-type"]

        style_resp = await client.get("/style.css")
        assert style_resp.status_code == 200
        assert "css" in style_resp.headers["content-type"]


async def test_status_unknown_job_returns_404():
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/status/does-not-exist")
        assert resp.status_code == 404


async def test_download_unknown_format_returns_404():
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/download/some-job/pdf")
        assert resp.status_code == 404


async def test_download_before_job_done_returns_404(sample_pdf_bytes):
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("sample.pdf", sample_pdf_bytes, "application/pdf")}
        upload_resp = await client.post("/api/upload", files=files)
        job_id = upload_resp.json()["job_id"]

        # Immediately try to download before the background pipeline (which
        # has not been awaited/yielded to yet) can have completed.
        download_resp = await client.get(f"/api/download/{job_id}/txt")
        assert download_resp.status_code == 404


async def test_health_endpoint_reports_ok_and_uptime():
    transport = ASGITransport(app=api.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["uptime_seconds"] >= 0
        # Must never leak configuration/secrets on a liveness probe.
        assert "bot_token" not in data
        assert set(data.keys()) == {"status", "uptime_seconds"}
