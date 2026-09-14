"""Document generation converters (TXT, DOCX, EPUB) for assembled Persian books.

Each converter takes a :class:`common.models.Book` and writes it to a
specific output format while preserving logical (non-reshaped) text order
and marking right-to-left directionality using the target format's own
bidi/markup facilities.
"""
