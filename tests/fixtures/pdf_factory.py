"""Test fixtures: generation of small, synthetic PDFs for pipeline tests.

These PDFs contain no real book content (avoids any copyright concern) and
are only used to exercise page rendering / OCR-pipeline plumbing with the
deterministic ``DummyOCREngine`` - no real OCR or network access involved.
"""
from __future__ import annotations

import io


def make_sample_pdf_bytes(num_pages: int = 2) -> bytes:
    """Build a tiny multi-page PDF in memory using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
    for page_number in range(1, num_pages + 1):
        pdf_canvas.drawString(100, 700, f"Synthetic test page {page_number}")
        pdf_canvas.showPage()
    pdf_canvas.save()
    return buffer.getvalue()
