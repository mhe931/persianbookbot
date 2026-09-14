"""EPUB converter for assembled books, with right-to-left (Persian) support."""
from __future__ import annotations

import html
from pathlib import Path

from ebooklib import epub

from common.models import Book
from converters.fonts import get_persian_font_name

_RTL_CSS_TEMPLATE = """\
body {{ direction: rtl; text-align: right; font-family: "{font}", serif; }}
h1, h2, p {{ direction: rtl; text-align: right; }}
"""


def _page_html(text: str) -> str:
    # Note: ebooklib re-parses ``EpubHtml.content`` and rebuilds the
    # <html>/<body> wrapper from its own template when serializing, so a
    # ``dir="rtl"`` attribute embedded directly in this fragment would be
    # silently discarded. RTL direction is instead applied by setting
    # ``EpubHtml(direction="rtl")`` below, which makes ebooklib itself set
    # ``dir`` on both the generated <html> and <body> elements.
    paragraphs = "</p><p>".join(html.escape(part) for part in text.split("\n\n"))
    return f"<body><p>{paragraphs}</p></body>"


def write_epub(book: Book, output_path: str | Path, font_name: str | None = None) -> Path:
    """Render ``book`` to a right-to-left EPUB file at ``output_path``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    persian_font = get_persian_font_name(font_name)

    epub_book = epub.EpubBook()
    epub_book.set_identifier(f"persianbookbot-{abs(hash(book.title)) if book.title else 'untitled'}")
    epub_book.set_title(book.title or "Untitled")
    epub_book.set_language(book.language or "fa")
    epub_book.add_author(book.author or "Unknown")
    if book.title:
        epub_book.add_metadata("DC", "description", f"Generated ebook: {book.title}")

    try:
        epub_book.set_direction("rtl")
    except AttributeError:
        pass

    css_item = epub.EpubItem(
        uid="style_rtl",
        file_name="style/rtl.css",
        media_type="text/css",
        content=_RTL_CSS_TEMPLATE.format(font=persian_font),
    )
    epub_book.add_item(css_item)

    chapters = []
    for page in sorted(book.pages, key=lambda p: p.page_number):
        chapter = epub.EpubHtml(
            title=f"Page {page.page_number}",
            file_name=f"page_{page.page_number}.xhtml",
            lang="fa",
            direction="rtl",
        )
        chapter.content = _page_html(page.text)
        chapter.add_link(href="style/rtl.css", rel="stylesheet", type="text/css")
        epub_book.add_item(chapter)
        chapters.append(chapter)

    epub_book.toc = tuple(chapters)
    epub_book.add_item(epub.EpubNcx())
    epub_book.add_item(epub.EpubNav())
    epub_book.spine = ["nav"] + chapters

    epub.write_epub(str(output_path), epub_book, {})
    return output_path
