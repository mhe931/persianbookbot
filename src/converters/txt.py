"""Plain-text (.txt) converter for assembled books."""
from __future__ import annotations

from pathlib import Path

from common.models import Book


def write_txt(
    book: Book,
    output_path: str | Path,
    page_separator: str = "\n\n\u2014\u2014\u2014\n\n",
) -> Path:
    """Write ``book`` as a UTF-8 (no BOM) plain-text file.

    The output consists of an optional title header line followed by each
    page's text (in ``page_number`` order) joined by ``page_separator``.
    Parent directories of ``output_path`` are created if missing.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []
    if book.title:
        parts.append(book.title)
        parts.append(page_separator)

    page_texts = [page.text for page in sorted(book.pages, key=lambda p: p.page_number)]
    parts.append(page_separator.join(page_texts))

    content = "".join(parts)
    output_path.write_text(content, encoding="utf-8", newline="\n")
    return output_path
