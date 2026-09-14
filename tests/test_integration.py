"""End-to-end integration test: a synthetic scanned-PDF-like file goes
through the full JobManager pipeline (OCR -> RTL assembly -> TXT/DOCX/EPUB)
using only the deterministic offline ``DummyOCREngine`` - no network,
credentials, or real OCR service required.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from ebooklib import epub

from bot.config import Settings
from bot.jobs import JobManager
from common.models import JobStatus


async def test_full_pipeline_pdf_to_txt_docx_epub(tmp_path, sample_pdf_path):
    settings = Settings(
        output_dir=str(tmp_path / "output"),
        upload_dir=str(tmp_path / "uploads"),
        ocr_engine="dummy",
    )
    manager = JobManager(settings=settings)
    job = await manager.create_job(source_filename="sample.pdf")

    await manager.run_pipeline(job.job_id, sample_pdf_path)

    assert job.status == JobStatus.DONE
    assert job.error is None

    txt_path = Path(job.output_paths["txt"])
    docx_path = Path(job.output_paths["docx"])
    epub_path = Path(job.output_paths["epub"])

    assert txt_path.exists() and txt_path.stat().st_size > 0
    assert docx_path.exists() and docx_path.stat().st_size > 0
    assert epub_path.exists() and epub_path.stat().st_size > 0

    txt_content = txt_path.read_text(encoding="utf-8")
    assert "متن نمونه صفحه 1" in txt_content
    assert "متن نمونه صفحه 2" in txt_content

    document = Document(str(docx_path))
    docx_text = "\n".join(p.text for p in document.paragraphs)
    assert "متن نمونه صفحه 1" in docx_text

    epub_book = epub.read_epub(str(epub_path))
    assert epub_book is not None
