"""Tests for ``tools/evaluate_sample.py``: the offline-safe local PDF
sample-evaluation CLI. Invoked as a subprocess (its own ``sys.executable``)
so these tests exercise the exact same entry point a user runs, without
requiring the package to be installed. Only ``--engine dummy`` is exercised
end-to-end (fully offline); the other engines are only checked for clean,
actionable failure when their optional dependency/credential is absent -
never for real recognition, so no network/credentials are ever required.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parents[1] / "tools" / "evaluate_sample.py"


def _run_cli(args: list[str], cwd: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Never let a locally configured real OCR credential leak into the
    # "missing credential" test cases below.
    for key in ("VISION_LLM_API_KEY", "PADDLE_LANG", "PADDLE_USE_GPU", "VISION_LLM_PROVIDER", "VISION_LLM_MODEL"):
        env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_dummy_engine_reports_metrics_and_writes_outputs(tmp_path, sample_pdf_path):
    output_dir = tmp_path / "out"
    result = _run_cli(
        [str(sample_pdf_path), "--engine", "dummy", "--output-dir", str(output_dir), "--json"],
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    # PyMuPDF may print an unrelated stdout deprecation notice before the
    # JSON payload in some versions; extract from the first '{' so an
    # incidental library warning can't break JSON parsing.
    json_start = result.stdout.index("{")
    metrics = json.loads(result.stdout[json_start:])
    assert metrics["engine"] == "dummy"
    assert metrics["page_count"] == 2
    assert metrics["total_characters"] > 0
    assert metrics["runtime_seconds"] >= 0
    assert set(metrics["output_paths"]) == {"txt", "docx", "epub"}
    for fmt, path_str in metrics["output_paths"].items():
        path = Path(path_str)
        assert path.exists()
        assert metrics["output_sizes"][fmt] == path.stat().st_size
        assert path.stat().st_size > 0


def test_dummy_engine_human_readable_report(tmp_path, sample_pdf_path):
    output_dir = tmp_path / "out"
    result = _run_cli(
        [str(sample_pdf_path), "--engine", "dummy", "--output-dir", str(output_dir)],
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert "sample evaluation" in result.stdout.lower()
    assert "Pages processed:     2" in result.stdout


def test_dummy_engine_csv_report(tmp_path, sample_pdf_path):
    import csv
    import io

    output_dir = tmp_path / "out"
    result = _run_cli(
        [str(sample_pdf_path), "--engine", "dummy", "--output-dir", str(output_dir), "--csv"],
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    # PyMuPDF may print an unrelated stdout deprecation notice before the
    # CSV payload in some versions (see the analogous --json test above);
    # slice from the header row so an incidental library warning can't
    # break CSV parsing.
    csv_start = result.stdout.index("pdf_path")
    rows = list(csv.DictReader(io.StringIO(result.stdout[csv_start:])))
    assert len(rows) == 1
    row = rows[0]
    assert row["engine"] == "dummy"
    assert int(row["page_count"]) == 2
    assert float(row["runtime_seconds"]) >= 0
    assert int(row["total_characters"]) > 0
    for fmt in ("txt", "docx", "epub"):
        path = Path(row[f"{fmt}_path"])
        assert path.exists()
        assert int(row[f"{fmt}_size_bytes"]) == path.stat().st_size


def test_csv_report_leaves_unrequested_format_columns_blank(tmp_path, sample_pdf_path):
    import csv
    import io

    output_dir = tmp_path / "out"
    result = _run_cli(
        [
            str(sample_pdf_path),
            "--engine",
            "dummy",
            "--output-dir",
            str(output_dir),
            "--formats",
            "txt",
            "--csv",
        ],
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    csv_start = result.stdout.index("pdf_path")
    rows = list(csv.DictReader(io.StringIO(result.stdout[csv_start:])))
    row = rows[0]
    assert row["txt_path"]
    assert row["docx_path"] == ""
    assert row["epub_path"] == ""
    assert row["docx_size_bytes"] == ""
    assert row["epub_size_bytes"] == ""


def test_json_and_csv_together_is_a_usage_error(tmp_path, sample_pdf_path):
    result = _run_cli(
        [str(sample_pdf_path), "--engine", "dummy", "--output-dir", str(tmp_path / "out"), "--json", "--csv"],
        cwd=tmp_path,
    )

    assert result.returncode == 1
    assert "mutually exclusive" in result.stderr.lower()


def test_csv_engine_unavailable_reports_error_on_stderr_not_stdout(tmp_path, sample_pdf_path):
    """When the engine is unavailable, the error must still go to stderr
    with a clear, actionable message, and no CSV payload must be printed
    to stdout - exactly like the JSON/human-readable modes. (An unrelated
    PyMuPDF import-time deprecation notice may still land on stdout in
    some library versions, so this checks for the *absence* of CSV output
    rather than requiring stdout to be completely empty.)
    """
    result = _run_cli([str(sample_pdf_path), "--engine", "tesseract", "--csv"], cwd=tmp_path)

    assert result.returncode == 2
    assert "pdf_path" not in result.stdout
    assert "pytesseract" in result.stderr.lower() or "tesseract" in result.stderr.lower()


def test_missing_pdf_file_exits_nonzero_with_actionable_message(tmp_path):
    missing = tmp_path / "does-not-exist.pdf"
    result = _run_cli([str(missing)], cwd=tmp_path)

    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_non_pdf_file_exits_nonzero(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a pdf")
    result = _run_cli([str(text_file)], cwd=tmp_path)

    assert result.returncode == 1
    assert ".pdf" in result.stderr.lower()


def test_unknown_format_exits_nonzero(tmp_path, sample_pdf_path):
    result = _run_cli([str(sample_pdf_path), "--formats", "pdf,bogus"], cwd=tmp_path)

    assert result.returncode == 1
    assert "unknown format" in result.stderr.lower()


def test_tesseract_engine_missing_dependency_exits_nonzero(tmp_path, sample_pdf_path):
    """pytesseract is not installed in the offline test environment, so this
    must fail cleanly (no crash/traceback) rather than requiring the
    dependency to be present.
    """
    result = _run_cli([str(sample_pdf_path), "--engine", "tesseract"], cwd=tmp_path)

    assert result.returncode == 2
    assert "pytesseract" in result.stderr.lower() or "tesseract" in result.stderr.lower()


def test_paddle_engine_missing_dependency_exits_nonzero(tmp_path, sample_pdf_path):
    result = _run_cli([str(sample_pdf_path), "--engine", "paddle"], cwd=tmp_path)

    assert result.returncode == 2
    assert "paddleocr" in result.stderr.lower()


def test_vision_llm_engine_missing_api_key_exits_nonzero(tmp_path, sample_pdf_path):
    result = _run_cli([str(sample_pdf_path), "--engine", "vision_llm"], cwd=tmp_path)

    assert result.returncode == 2
    assert "vision_llm_api_key" in result.stderr.lower()


def test_help_exits_zero():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--help"], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0
    assert "engine" in result.stdout.lower()
