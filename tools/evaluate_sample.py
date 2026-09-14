#!/usr/bin/env python
"""Offline-safe local sample-evaluation CLI for the Persian OCR pipeline.

Runs the existing ``ocr.pipeline.process_pdf`` orchestrator and
``converters`` writers against a single local PDF file and reports
runtime/page/character/output metrics. This tool intentionally reuses the
same engine factory (``ocr.engine.get_ocr_engine``), pipeline
(``ocr.pipeline.process_pdf``), and converters (``converters.*``) used by
the bot/API - it does not reimplement any OCR, rendering, or document
generation logic.

Usage
-----

Fully offline, zero-credential smoke test (default engine)::

    python tools/evaluate_sample.py path/to/book.pdf

Real backends (each requires its own optional dependency/credential - see
``docs/PROJECT_STATUS.md``)::

    python tools/evaluate_sample.py path/to/book.pdf --engine tesseract
    python tools/evaluate_sample.py path/to/book.pdf --engine paddle --paddle-lang fa
    python tools/evaluate_sample.py path/to/book.pdf --engine vision_llm \\
        --vision-llm-provider gemini --vision-llm-api-key "$env:VISION_LLM_API_KEY"

Exit codes
----------

``0``
    Success - metrics printed (human-readable by default, or ``--json``).
``1``
    Usage error: missing/non-PDF input file, unknown format, or bad
    argument combination. No network/dependency access is attempted.
``2``
    OCR engine unavailable: a required optional dependency
    (``pytesseract``, ``paddleocr``, ``httpx``) is not installed, or a
    required credential (``VISION_LLM_API_KEY``) is missing/invalid, or the
    engine was rate-limited after exhausting retries.
``3``
    Pipeline failure at runtime: the PDF could not be rendered, OCR
    recognition failed for a reason other than rate limiting, or writing
    an output format failed.

Never requires network access or credentials with the default
``--engine dummy`` (``DummyOCREngine`` - see ``src/ocr/engine.py``).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# This script lives in tools/ (outside the installed `src` package layout),
# so make `src/` importable the same way pytest's `pythonpath = ["src"]`
# (pyproject.toml) does, without requiring an editable install.
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from common.models import Book  # noqa: E402

from converters.docx_writer import write_docx  # noqa: E402
from converters.epub_writer import write_epub  # noqa: E402
from converters.txt import write_txt  # noqa: E402

from ocr.engine import OCRError, RateLimitError, get_ocr_engine  # noqa: E402
from ocr.pipeline import process_pdf  # noqa: E402
from ocr.preprocessing import PdfRenderError  # noqa: E402

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_ENGINE_UNAVAILABLE = 2
EXIT_PIPELINE_FAILURE = 3

ENGINE_CHOICES = ("dummy", "tesseract", "paddle", "vision_llm")
FORMAT_CHOICES = ("txt", "docx", "epub")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluate_sample.py",
        description=(
            "Run the Persian OCR pipeline against a single local PDF and report "
            "runtime/page/character/output metrics. Fully offline with the "
            "default --engine dummy; other engines may require optional "
            "dependencies or credentials (see docs/PROJECT_STATUS.md)."
        ),
    )
    parser.add_argument("pdf_path", type=Path, help="Path to a local PDF file to evaluate.")
    parser.add_argument(
        "--engine",
        choices=ENGINE_CHOICES,
        default="dummy",
        help="OCR engine to use (default: %(default)s, fully offline/deterministic).",
    )
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (default: %(default)s).")
    parser.add_argument(
        "--formats",
        default="txt,docx,epub",
        help="Comma-separated output formats to generate (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write generated output files into "
            "(default: ./data/eval/<pdf-stem>/)."
        ),
    )
    parser.add_argument("--title", default=None, help="Book title override (default: PDF filename stem).")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max OCR rate-limit retries before giving up (default: %(default)s).",
    )
    parser.add_argument(
        "--backoff-seconds",
        type=float,
        default=1.0,
        help="Initial retry backoff in seconds, doubled per attempt (default: %(default)s).",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON metrics only.")

    # Optional per-engine overrides, applied as environment variables so
    # ocr.engine.get_ocr_engine() - the single source of truth for engine
    # construction - picks them up unchanged rather than duplicating its logic.
    parser.add_argument("--paddle-lang", default=None, help="PaddleOCR language code (OCR_ENGINE=paddle).")
    parser.add_argument("--paddle-use-gpu", action="store_true", help="Enable GPU for PaddleOCR.")
    parser.add_argument(
        "--vision-llm-provider", default=None, choices=("gemini", "claude"), help="Vision-LLM provider."
    )
    parser.add_argument(
        "--vision-llm-api-key",
        default=None,
        help="Vision-LLM API key (falls back to the VISION_LLM_API_KEY env var; never logged/printed).",
    )
    parser.add_argument("--vision-llm-model", default=None, help="Vision-LLM model name override.")
    return parser


def _apply_engine_env_overrides(args: argparse.Namespace) -> None:
    """Translate CLI engine options into the env vars ``get_ocr_engine``
    already reads, instead of duplicating its construction logic here.
    """
    if args.paddle_lang:
        os.environ["PADDLE_LANG"] = args.paddle_lang
    if args.paddle_use_gpu:
        os.environ["PADDLE_USE_GPU"] = "true"
    if args.vision_llm_provider:
        os.environ["VISION_LLM_PROVIDER"] = args.vision_llm_provider
    if args.vision_llm_api_key:
        os.environ["VISION_LLM_API_KEY"] = args.vision_llm_api_key
    if args.vision_llm_model:
        os.environ["VISION_LLM_MODEL"] = args.vision_llm_model


def _validate_pdf_path(pdf_path: Path) -> str | None:
    if not pdf_path.exists():
        return f"PDF file not found: {pdf_path}"
    if not pdf_path.is_file():
        return f"Not a file: {pdf_path}"
    if pdf_path.suffix.lower() != ".pdf":
        return f"Not a .pdf file (got suffix '{pdf_path.suffix}'): {pdf_path}"
    return None


def run(args: argparse.Namespace) -> tuple[int, dict]:
    """Execute the evaluation. Returns ``(exit_code, metrics_or_error_dict)``."""
    problem = _validate_pdf_path(args.pdf_path)
    if problem:
        return EXIT_USAGE, {"error": problem}

    requested_formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    unknown = sorted(set(requested_formats) - set(FORMAT_CHOICES))
    if unknown:
        return EXIT_USAGE, {
            "error": f"Unknown format(s): {', '.join(unknown)} (choices: {', '.join(FORMAT_CHOICES)})"
        }
    if not requested_formats:
        return EXIT_USAGE, {"error": "No output formats requested."}

    _apply_engine_env_overrides(args)

    try:
        engine = get_ocr_engine(args.engine)
    except OCRError as exc:
        return EXIT_ENGINE_UNAVAILABLE, {
            "error": f"OCR engine '{args.engine}' unavailable: {exc}",
            "engine": args.engine,
        }
    except ValueError as exc:
        return EXIT_USAGE, {"error": str(exc)}

    started = time.perf_counter()
    try:
        book: Book = asyncio.run(
            process_pdf(
                args.pdf_path,
                engine=engine,
                dpi=args.dpi,
                title=args.title,
                max_retries=args.max_retries,
                backoff_seconds=args.backoff_seconds,
            )
        )
    except PdfRenderError as exc:
        return EXIT_PIPELINE_FAILURE, {"error": f"Failed to render PDF: {exc}"}
    except RateLimitError as exc:
        return EXIT_ENGINE_UNAVAILABLE, {
            "error": f"OCR engine rate-limited after {args.max_retries} retries: {exc}",
            "engine": args.engine,
        }
    except OCRError as exc:
        return EXIT_PIPELINE_FAILURE, {"error": f"OCR recognition failed: {exc}", "engine": args.engine}
    runtime_seconds = time.perf_counter() - started

    output_dir = args.output_dir or (Path("data") / "eval" / args.pdf_path.stem)
    output_paths: dict[str, str] = {}
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if "txt" in requested_formats:
            output_paths["txt"] = str(write_txt(book, output_dir / "book.txt"))
        if "docx" in requested_formats:
            output_paths["docx"] = str(write_docx(book, output_dir / "book.docx"))
        if "epub" in requested_formats:
            output_paths["epub"] = str(write_epub(book, output_dir / "book.epub"))
    except Exception as exc:  # noqa: BLE001 - surface any converter failure as a clean CLI error
        return EXIT_PIPELINE_FAILURE, {"error": f"Failed to write output format(s): {exc}"}

    output_sizes: dict[str, int] = {}
    for fmt, path_str in output_paths.items():
        try:
            output_sizes[fmt] = Path(path_str).stat().st_size
        except OSError:
            continue

    total_chars = sum(len(p.text) for p in book.pages)
    metrics = {
        "pdf_path": str(args.pdf_path),
        "engine": args.engine,
        "dpi": args.dpi,
        "runtime_seconds": round(runtime_seconds, 3),
        "page_count": len(book.pages),
        "pages_per_second": round(len(book.pages) / runtime_seconds, 3) if runtime_seconds > 0 else None,
        "total_characters": total_chars,
        "average_characters_per_page": round(total_chars / len(book.pages), 1) if book.pages else 0,
        "average_confidence": round(book.average_confidence, 4),
        "output_dir": str(output_dir),
        "output_paths": output_paths,
        "output_sizes": output_sizes,
    }
    return EXIT_OK, metrics


def _print_human_report(metrics: dict) -> None:
    print("Persian Book Bot - sample evaluation")
    print("=" * 40)
    print(f"PDF file:            {metrics['pdf_path']}")
    print(f"OCR engine:          {metrics['engine']}")
    print(f"Render DPI:          {metrics['dpi']}")
    print(f"Runtime:             {metrics['runtime_seconds']}s")
    print(f"Pages processed:     {metrics['page_count']}")
    if metrics["pages_per_second"] is not None:
        print(f"Pages/sec:           {metrics['pages_per_second']}")
    print(f"Total characters:    {metrics['total_characters']}")
    print(f"Avg chars/page:      {metrics['average_characters_per_page']}")
    print(f"Avg OCR confidence:  {metrics['average_confidence']}")
    print(f"Output directory:    {metrics['output_dir']}")
    for fmt, path in metrics["output_paths"].items():
        size = metrics["output_sizes"].get(fmt)
        size_str = f"{size} bytes" if size is not None else "unknown size"
        print(f"  - {fmt.upper():<5} {path} ({size_str})")


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    exit_code, metrics = run(args)

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    elif exit_code == EXIT_OK:
        _print_human_report(metrics)
    else:
        print(f"error: {metrics.get('error', 'unknown error')}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
