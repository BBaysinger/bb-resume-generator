# BB Resume Generator

Static tooling to turn a Markdown resume into HTML, DOCX, and PDF deliverables. Pandoc handles Markdown -> HTML/DOCX, WeasyPrint exports the PDF, and a small Python script normalizes DOCX bullet indentation for consistent spacing.

## Requirements

- Node.js 18+ (to run the npm scripts)
- Python 3.10+ with `pip`
- [Pandoc](https://pandoc.org/) available on your PATH
- [WeasyPrint](https://weasyprint.org/) CLI for PDF export

## Setup

```bash
# install JS dependencies (none yet, but keeps npm scripts happy)
npm install

# create Python virtualenv for helper scripts
python3 -m venv .venv
source .venv/bin/activate
pip install weasyprint python-docx lxml
```

If Pandoc or WeasyPrint are installed via Homebrew, make sure their binaries are available globally (e.g., `brew install pandoc weasyprint`).

## Usage

1. Create/update a Markdown resume inside `input/`.
2. Run one of the npm scripts, passing the Markdown file path:
   - `npm run build:html -- --input "input/resume.md"`
   - `npm run export:docx -- --input "input/resume.md"`
   - `npm run export:pdf -- --input "input/resume.md"`

Outputs land in `output/`. By default the output filename is derived from the Markdown filename (spaces become underscores). You can override output paths with `--html`, `--pdf`, or `--docx`.

### Convert everything in `input/`

- `npm run convert:all`

Optional flags:

- `npm run convert:all -- --formats pdf,docx,html`
- `npm run convert:all -- --continueOnError`

## Repo structure

- `input/` – source Markdown resumes.
- `templates/` – starter Markdown templates (not auto-converted).
- `converter/resume.css` – on-screen styling for the HTML export.
- `converter/pdf-print.css` – print-specific overrides for WeasyPrint.
- `converter/scripts/normalize_docx_lists.py` – fixes Word bullet indentation.
- `output/` – generated artifacts; safe to delete/regenerate.

## Preventing “invisible” diff noise in `input/`

Copy/paste from Word / Google Docs can introduce invisible or lookalike Unicode characters (notably the non-breaking hyphen `U+2011`) that render like a normal `-` but cause noisy diffs in version control.

This project includes a normalizer plus an optional pre-commit hook in the nested `input/` git repo:

- Manual normalization:
  - `npm run normalize:md` (writes fixes into `input/`)
  - `npm run normalize:md:check` (fails if fixes would be applied)
- One-time hook setup (recommended if you commit inside `input/`):
  - `npm run setup:input-hooks`

The hook auto-normalizes staged `*.md` files before commit and re-stages them.
