"""DOCX converter for assembled books, with right-to-left (Persian) support.

python-docx has no high-level API for bidi/complex-script formatting, so
this module manipulates the underlying WordprocessingML (OXML) elements
directly to mark paragraphs/runs as RTL and to set the complex-script font.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from common.models import Book
from converters.fonts import get_persian_font_name


def _set_paragraph_rtl(paragraph) -> None:
    """Mark a paragraph as bidi/RTL and right-align it."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = paragraph.paragraph_format.element.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)


def _set_run_rtl(run, font_name: str) -> None:
    """Mark a run as complex-script/RTL and set its complex-script font."""
    run.font.complex_script = True
    run.font.name = font_name

    rPr = run._element.get_or_add_rPr()
    rtl = OxmlElement("w:rtl")
    rPr.append(rtl)

    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:cs"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)


def _set_document_default_rtl(document, font_name: str) -> None:
    """Set the default (Normal style) font and document-level RTL section."""
    normal_style = document.styles["Normal"]
    normal_style.font.name = font_name
    style_rPr = normal_style.element.get_or_add_rPr()
    rFonts = style_rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        style_rPr.append(rFonts)
    rFonts.set(qn("w:cs"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)

    sectPr = document.sections[0]._sectPr
    bidi = OxmlElement("w:bidi")
    sectPr.append(bidi)


def write_docx(book: Book, output_path: str | Path, font_name: str | None = None) -> Path:
    """Render ``book`` to a right-to-left DOCX file at ``output_path``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    persian_font = get_persian_font_name(font_name)

    document = Document()
    _set_document_default_rtl(document, persian_font)

    core_properties = document.core_properties
    if book.title:
        core_properties.title = book.title
    if book.author:
        core_properties.author = book.author

    if book.title:
        heading = document.add_heading(book.title, level=1)
        for paragraph in [heading]:
            _set_paragraph_rtl(paragraph)
            for run in paragraph.runs:
                _set_run_rtl(run, persian_font)

    pages = sorted(book.pages, key=lambda p: p.page_number)
    for index, page in enumerate(pages):
        paragraph = document.add_paragraph()
        _set_paragraph_rtl(paragraph)
        run = paragraph.add_run(page.text)
        _set_run_rtl(run, persian_font)

        if index < len(pages) - 1:
            page_break_run = paragraph.add_run()
            page_break_run.add_break(WD_BREAK.PAGE)

    document.save(str(output_path))
    return output_path
