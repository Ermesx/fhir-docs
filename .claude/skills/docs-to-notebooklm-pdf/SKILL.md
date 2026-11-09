---
name: docs-to-notebooklm-pdf
description: Convert a source documentation set (a zipped website, a folder of HTML pages, Markdown/MkDocs/GitBook docs, an offline spec download) into a small set of lean, text-only PDFs that fit NotebookLM's source limits (max 50 sources, max 200 MB and max 500,000 words per source), ordered by the docs' table of contents, with bookmarks and a verification report. Use this whenever the user wants to load documentation, a specification, a manual or a downloaded website into NotebookLM (or a similar AI notebook / RAG tool with per-source limits), asks to "turn this documentation into PDFs", "split the docs into files for NotebookLM", "prepare sources for a notebook", or mentions hitting NotebookLM's file, size or word limits — even if they do not name NotebookLM explicitly but want docs packed into a limited number of PDFs for AI reading.
---

# Documentation → lean PDFs for NotebookLM

The goal is a set of PDFs that NotebookLM can ingest in full and answer from accurately. That
shapes every choice below: text matters, looks do not; nothing may be silently dropped; each file
must stay under the limits; and answers should be traceable back to the original page.

## NotebookLM limits (as known in late 2026; ask the user if they have a different plan)

| Limit | Value | How the skill handles it |
|---|---|---|
| Sources per notebook | 50 (free; paid tiers allow more) | `--max-files 50` in plan/verify |
| Size per source | 200 MB | text-only PDFs are ~1–2 MB per 300k words, so this is rarely binding |
| Words per source | 500,000 | **the binding limit** for big docs; plan caps extracted words at 300k because PDF extraction counts 5–25% more words (table separators, wrapped code); verify checks the real count |

If the user names other limits (another tool, a paid plan), pass them as flags; the logic is the same.

## Workflow

Make a task list: inspect → extract → plan → render → verify → deliver.

### 1. Inspect the source and the machine

- Find the input: a `.zip` or a folder. Large downloads are often on the user's computer; when a
  shell on that computer is available, **work there** (no upload of hundreds of MB, files stay local)
  and write results into the source's own folder in the repo (e.g. `official-docs/fhir-r4/` or `vendor-docs/<vendor>-<version>/`), next to the original input.
- Check Python 3 with `beautifulsoup4`, `lxml`, `reportlab`, `pypdf` (`pip install` if missing),
  and free disk space (unzipped HTML can be 5–10× the zip). No font files are needed: PDFs use the built-in Helvetica/Courier fonts, and rare non-Latin-1 symbols (arrows, ≥, ✓) are mapped to ASCII. Docs are assumed to be English.
- Copy `scripts/` into a working directory outside the user's folder (temporary files should not
  clutter it, and deleting there may be disallowed).
- Run `python extract.py SOURCE pages.jsonl --list-only` to see how many pages there are and which
  ordering was detected. Sanity-check it against the docs' own table of contents:
  - a TOC is optional. A TOC page with numbered entries ("4.3.1 Title") is the best case: order and
    chapters come from it. Vendor docs rarely have one, and that is fine: the skill falls back to path order;
  - if auto-detection picked the wrong page, pass `--toc <path to the docs' TOC page>` (HTML or Markdown);
  - `path-order` means no TOC was found: files are taken in natural path order and grouped by top
    folder. Tell the user this in one line, since the order may differ from the docs' reading order.

### 2. Extract clean text

```
python extract.py SOURCE pages.jsonl [--toc TOC_PAGE] [--drop-regex "banner text to remove"]
```

Removed: scripts, styles, nav bars, headers/footers, sidebars, breadcrumbs, images, tab strips.
Kept: headings, paragraphs, list items, tables (as rows of cells), code/examples (`pre`).

Then **look at one or two representative pages** in `pages.jsonl` (e.g. a typical reference page
and a page with a big table). Repeating boilerplate (a "this page is part of …" banner, a version
notice on every page) wastes words on every page; remove it with `--drop-regex` and re-run. If a
site keeps its content in an unusual container, the generic selectors may grab too much or too
little; adjust `CONTENT_SELECTORS` / `DROP_SELECTORS` in `extract.py` instead of fixing it by hand.

**Shells with a per-command time limit** (e.g. 2–3 minutes): long runs get killed, and background
processes started with `nohup … &` may be killed when the call returns. Process in slices instead:
`--start 0 --end 1500`, then `--start 1500 --end 3000 --append`, and so on. Roughly 100–200 HTML
pages per second is typical; use `--list-only` to size the slices.

### 3. Plan the split

```
python plan.py pages.jsonl parts.json --name DOCNAME [--cap 300000] [--max-files 50]
```

Chapters (top-level TOC numbers, or top folders) stay together, so each PDF is a coherent topic:
this makes it easier for the user to pick or deselect sources in NotebookLM. A chapter over the cap
is split into equal parts on page boundaries. Small chapters are merged only when the file count
would otherwise exceed the limit. With a TOC, unnumbered entries (indexes, generated listings) are
attached to the preceding chapter, and front matter (leading unnumbered pages and chapter 0) is merged
with the first chapter as `ch00-01_Front-Matter`. Numeric chapter labels become `chNN` in file names.
Read the printed `NOTE:` lines and pass anything important to the user,
for example if a single page alone exceeds the cap or the corpus needs more than one notebook.

### 4. Render

```
python render.py pages.jsonl parts.json OUTDIR --base-url https://site/docs/ --source-label "Product X docs v1.2"
```

Each source page starts with its section number + title (also a PDF bookmark) and its original URL
(`--base-url`) or file path, so NotebookLM citations can be traced back. Use `--only 1,2,3` to render
in slices under a time limit. Big parts take a few seconds each.

### 5. Verify — do not skip

```
python verify.py pages.jsonl parts.json OUTDIR [--only …]   # then once without --only
```

It counts words **on the text extracted from the finished PDFs** (what NotebookLM sees), checks size,
file count, that every source page has a bookmark and that every page is in exactly one PDF, and
writes the report `OUTDIR/REPORT.md` (always in English, Markdown, under exactly that name). If a file exceeds the word limit, lower `--cap` (e.g. 250000), re-plan,
re-render, and re-verify. Also render one page of one PDF to an image and look at it: this is the
quickest way to notice broken text (glued words, missing tables).

### 6. Deliver

Put the PDFs and `REPORT.md` in the folder the user will upload from. Reply briefly in the user's language:
- a compact table: file count, the largest file in MB and in words, pages covered/total;
- the split, e.g. which chapter was divided into how many parts;
- anything left out or worth knowing, such as boilerplate removed, path-order fallback, or interactive content that became static;
- the practical bottom line: upload all files to one notebook, or which files to skip if the user
  only needs part of the docs (huge generated listings such as reference tables or API indexes are
  usually the first candidates).

## Design choices and why

- **Text-only, no images**: NotebookLM reasons over text; images add size and nothing it can use, and
  diagrams in docs are usually also described in text.
- **Tables as `cell | cell` lines**: they survive PDF text extraction intact, while real PDF tables
  often come out scrambled.
- **Code in monospace, wrapped at 120 chars**: long lines would otherwise be cut off at the page edge
  and lost from the extracted text.
- **Fragment links (`page.html#x`) deduplicated**: a TOC often links to sections inside one page;
  each file is included once, at its first position.
- **Windows-made zips with backslash paths** are normalised; a single common top folder (e.g. `site/`)
  is treated as the doc root.
- **Scaling**: a spec of a few thousand pages (~4M words, a ~200 MB zip) typically becomes
  ~20 PDFs of 0.3–2 MB in a few minutes; a single huge chapter is split into several parts.
