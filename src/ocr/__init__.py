"""OCR subsystem: PDF rendering, preprocessing, text recognition, RTL shaping.

This package converts a source PDF into a fully OCR'd, structured ``Book``
(see ``common.models``) by orchestrating page rendering (PyMuPDF), image
preprocessing (Pillow-based deskew/grayscale), pluggable OCR engines, and
Persian/Arabic RTL text handling.
"""
