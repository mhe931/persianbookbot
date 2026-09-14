---
applyTo: "src/converters/**"
---

# Document converters instructions

Scope: `src/converters/` — `txt.py`, `docx_writer.py`, `epub_writer.py`,
`fonts.py`. See `docs/ARCHITECTURE.md` for the full pipeline context and
`AGENTS.md` for repo-wide rules.

## Contract

- Every `write_*` function takes a `common.models.Book` and an output path
  and returns a `pathlib.Path` — keep this signature consistent for any new
  writer, and create parent directories (`output_path.parent.mkdir(parents=True, exist_ok=True)`)
  before writing, as the existing writers do.
- Iterate `book.pages` sorted by `page_number` (`sorted(book.pages, key=lambda p: p.page_number)`)
  — never assume input order.

## RTL correctness (critical)

- DOCX and EPUB must set **explicit RTL directionality**, not visually
  reshaped/reordered characters:
  - DOCX: use raw OXML elements (`w:bidi` on the paragraph, `w:rtl` +
    complex-script `w:rFonts` on the run, plus a document-level `w:bidi` in
    `sectPr`) — `python-docx` has no high-level bidi API, so this direct
    manipulation is required and must be preserved.
  - EPUB: set `EpubHtml(direction="rtl", ...)` per chapter so `ebooklib`
    itself emits `dir="rtl"` on the generated `<html>`/`<body>`. **Do not**
    embed a `dir="rtl"` attribute directly in the HTML fragment passed to
    `EpubHtml.content` — `ebooklib` re-parses and rebuilds the wrapper on
    serialization and will silently discard it.
  - Always pair RTL direction with `direction: rtl; text-align: right;`
    CSS for EPUB (see the `_RTL_CSS_TEMPLATE` in `epub_writer.py`).
- Keep text content in **logical (reading) order** in the `Book`/`PageText`
  passed in; do not call `ocr.rtl.shape_rtl()` (visual reordering) on text
  destined for DOCX/EPUB — that would double-reorder text these formats
  already bidi-render correctly themselves.

## Fonts

- Resolve the Persian font name via `converters.fonts.get_persian_font_name(font_name)`
  (which falls back to a sane default if `font_name`/`PERSIAN_FONT_NAME` is
  unset) — do not hardcode a font name in a writer.
- **Never bundle font binaries** in this repository; font licensing is the
  deployer's responsibility. Only reference font *names*.

## Adding a new output format

- Add a new `write_<format>(book, output_path, font_name=None) -> Path`
  function following the same signature/contract above.
- Wire it into `bot.jobs.JobManager.run_pipeline` (`output_paths[fmt] = ...`)
  and the Mini App's `_VALID_FORMATS` set in `src/bot/api.py` if it should
  be downloadable — see `.github/instructions/bot.instructions.md`.

## Tests

- New converter behavior must be verifiable by reading back the generated
  file (e.g. asserting on DOCX OXML attributes or EPUB chapter `direction`)
  without any network access or real fonts/credentials. Run
  `pytest tests/` (46 tests as of this writing) before committing.
