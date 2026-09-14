"""PDF rendering and image preprocessing for the OCR pipeline.

Rendering uses PyMuPDF (``fitz``) to rasterize PDF pages into PNG byte
buffers. Preprocessing uses Pillow to grayscale and deskew those images
before they are handed to an OCR engine.
"""
from __future__ import annotations

import io
import statistics
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from common.models import PageImage


class PdfRenderError(Exception):
    """Raised when a PDF cannot be opened or rendered."""


def render_pdf_pages(pdf_path: str | Path, dpi: int = 200) -> list[PageImage]:
    """Render every page of ``pdf_path`` into a list of ``PageImage``.

    Each page is rasterized at ``dpi`` and encoded as PNG bytes via
    ``pix.tobytes("png")``.
    """
    pages: list[PageImage] = []
    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        with fitz.open(str(pdf_path)) as doc:
            for index, page in enumerate(doc):
                pix = page.get_pixmap(matrix=matrix)
                pages.append(
                    PageImage(
                        page_number=index + 1,
                        width=pix.width,
                        height=pix.height,
                        dpi=dpi,
                        data=pix.tobytes("png"),
                    )
                )
    except Exception as exc:  # noqa: BLE001 - normalize any PyMuPDF/IO error
        raise PdfRenderError(f"Failed to render PDF '{pdf_path}': {exc}") from exc

    if not pages:
        raise PdfRenderError(f"PDF '{pdf_path}' contains no pages")

    return pages


def _row_profile(image: Image.Image) -> list[int]:
    """Sum of pixel intensities per row - a cheap horizontal projection profile."""
    width, height = image.size
    pixels = image.load()
    profile = []
    for y in range(height):
        row_sum = 0
        for x in range(width):
            row_sum += pixels[x, y]
        profile.append(row_sum)
    return profile


def _profile_variance(profile: list[int]) -> float:
    if len(profile) < 2:
        return 0.0
    return statistics.pvariance(profile)


def _estimate_skew_angle(gray: Image.Image) -> float:
    """Estimate skew via a horizontal projection-profile search.

    The image is downscaled first so the search stays cheap. We rotate a
    thumbnail through a small set of candidate angles and pick the angle
    whose row-sum profile has the highest variance: well-aligned text lines
    produce sharp peaks/troughs in the profile, while a skewed page smears
    them out.
    """
    thumb = gray.copy()
    thumb.thumbnail((200, 200))
    if thumb.width == 0 or thumb.height == 0:
        return 0.0

    best_angle = 0.0
    best_variance = -1.0
    angle = -5.0
    while angle <= 5.0 + 1e-9:
        rotated = thumb.rotate(angle, expand=False, fillcolor=255)
        variance = _profile_variance(_row_profile(rotated))
        if variance > best_variance:
            best_variance = variance
            best_angle = angle
        angle += 0.5

    if best_variance <= 0.0:
        # Degenerate/blank image - no reliable skew signal, don't rotate.
        return 0.0
    return best_angle


def preprocess_page(page: PageImage) -> PageImage:
    """Grayscale and deskew a rendered page, returning a new ``PageImage``."""
    if not page.data:
        return page

    with Image.open(io.BytesIO(page.data)) as source:
        gray = source.convert("L")
        angle = _estimate_skew_angle(gray)
        deskewed = gray.rotate(angle, expand=True, fillcolor=255)

        buffer = io.BytesIO()
        deskewed.save(buffer, format="PNG")
        data = buffer.getvalue()

    return PageImage(
        page_number=page.page_number,
        width=deskewed.width,
        height=deskewed.height,
        dpi=page.dpi,
        data=data,
    )
