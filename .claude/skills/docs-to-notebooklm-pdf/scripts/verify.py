#!/usr/bin/env python3
"""Stage 4: check the PDFs against NotebookLM limits and against the source, write REPORT.md (English, Markdown).

Checks per file: size <= --max-mb, words (as extracted from the PDF, which is what NotebookLM sees)
<= --max-words, every planned page present as a bookmark. Globally: file count <= --max-files and
every source page covered exactly once. Exit code 1 if anything fails.
"""
import argparse, json, os, sys
from pypdf import PdfReader


def flat(ol):
    for o in ol:
        if isinstance(o, list):
            yield from flat(o)
        else:
            yield o.title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages'); ap.add_argument('parts'); ap.add_argument('outdir')
    ap.add_argument('--max-files', type=int, default=50)
    ap.add_argument('--max-mb', type=float, default=200)
    ap.add_argument('--max-words', type=int, default=500000)
    ap.add_argument('--warn-words', type=int, default=450000, help='flag files close to the word limit')
    ap.add_argument('--only', default='', help='verify only these 1-based part numbers (for time-limited shells)')
    ap.add_argument('--report', default='REPORT.md')
    a = ap.parse_args()

    plan = json.load(open(a.parts, encoding='utf-8'))
    pages = {}
    for line in open(a.pages, encoding='utf-8'):
        p = json.loads(line)
        pages[p['i']] = p
    only = {int(x) for x in a.only.split(',') if x}
    cache_path = os.path.join(a.outdir, '.verify_cache.json')
    cache = json.load(open(cache_path, encoding='utf-8')) if os.path.exists(cache_path) else {}
    problems, rows = [], []
    covered = []
    for n, part in enumerate(plan['parts'], 1):
        f = os.path.join(a.outdir, part['file'])
        covered += list(range(part['lo'], part['hi']))
        if only and n not in only:
            continue
        if not os.path.exists(f):
            problems.append(f'missing file {part["file"]}')
            continue
        r = PdfReader(f)
        words = sum(len((pg.extract_text() or '').split()) for pg in r.pages)
        heads = set(flat(r.outline))
        expect = [pages[i] for i in range(part['lo'], part['hi']) if i in pages]
        missing = [p['href'] for p in expect
                   if (f"{p['sec']} {p['title']}" if p['sec'] else p['title'])[:150] not in heads]
        mb = os.path.getsize(f) / 1e6
        cache[part['file']] = dict(n=n, pdf_pages=len(r.pages), words=words, mb=round(mb, 2),
                                   src_pages=len(expect), missing=missing[:5], n_missing=len(missing),
                                   first=part['first'], last=part['last'])
        print(f"{n:02d} {part['file']}: {words} words, {mb:.2f} MB, {len(r.pages)} PDF pages, missing bookmarks {len(missing)}", flush=True)
    json.dump(cache, open(cache_path, 'w', encoding='utf-8'))
    if only:
        print('partial run; rerun without --only (results are cached) to get the full report')
        return

    total_words = 0
    for part in plan['parts']:
        c = cache.get(part['file'])
        if not c:
            problems.append(f'not verified: {part["file"]}')
            continue
        total_words += c['words']
        if c['mb'] > a.max_mb:
            problems.append(f"{part['file']}: {c['mb']} MB > {a.max_mb} MB")
        if c['words'] > a.max_words:
            problems.append(f"{part['file']}: {c['words']} words > {a.max_words} (re-plan with a lower --cap)")
        elif c['words'] > a.warn_words:
            problems.append(f"WARNING {part['file']}: {c['words']} words is close to the {a.max_words} limit")
        if c['n_missing']:
            problems.append(f"{part['file']}: {c['n_missing']} pages without a bookmark, e.g. {c['missing']}")
        rows.append(c | {'file': part['file']})
    if len(plan['parts']) > a.max_files:
        problems.append(f"{len(plan['parts'])} files > {a.max_files}")
    dup = len(covered) - len(set(covered))
    uncovered = sorted(set(pages) - set(covered))
    if dup:
        problems.append(f'{dup} pages appear in more than one PDF')
    if uncovered:
        problems.append(f'{len(uncovered)} source pages in no PDF, e.g. {[pages[i]["href"] for i in uncovered[:5]]}')

    def md(s):  # keep table cells intact
        return str(s).replace('|', '\\|')

    errors = [p for p in problems if not p.startswith('WARNING')]
    status = 'FAILED' if errors else ('PASSED with warnings' if problems else 'PASSED')
    n_cov = len(set(covered) & set(pages))
    max_w = max((c['words'] for c in rows), default=0)
    max_mb = max((c['mb'] for c in rows), default=0)
    L = [f"# {md(plan['name'])} — PDF set for NotebookLM", '',
         f"**Status:** {status}", '',
         '## Limits check', '',
         '| Check | Limit | Result | OK |', '|---|---|---|---|',
         f"| Number of files | ≤ {a.max_files} | {len(plan['parts'])} | {'✅' if len(plan['parts']) <= a.max_files else '❌'} |",
         f"| Largest file size | ≤ {a.max_mb:g} MB | {max_mb} MB | {'✅' if max_mb <= a.max_mb else '❌'} |",
         f"| Largest word count (PDF text) | ≤ {a.max_words:,} | {max_w:,} | {'✅' if max_w <= a.max_words else '❌'} |",
         f"| Source pages covered | {len(pages)} | {n_cov} | {'✅' if n_cov == len(pages) and not dup else '❌'} |",
         '', '## Files', '',
         '| # | File | Sections | Source pages | PDF pages | Words | MB |', '|---|---|---|---|---|---|---|']
    for c in rows:
        L.append(f"| {c['n']} | {md(c['file'])} | {md(c['first'])} – {md(c['last'])} | {c['src_pages']} | "
                 f"{c['pdf_pages']} | {c['words']:,} | {c['mb']} |")
    L.append(f"| | **Total** | | **{sum(c['src_pages'] for c in rows)}** | **{sum(c['pdf_pages'] for c in rows)}** | "
             f"**{total_words:,}** | **{round(sum(c['mb'] for c in rows), 1)}** |")
    if plan.get('notes'):
        L += ['', '## Planner notes', ''] + [f'- {x}' for x in plan['notes']]
    L += ['', '## Problems and warnings', ''] + ([f'- {x}' for x in problems] if problems else ['None. All checks passed.'])
    L += ['', '## Method', '',
          f"- Word cap used when planning: {plan['cap']:,} extracted words per file "
          '(PDF text extraction counts a few percent more, so the final count is verified on the PDFs).',
          '- Content is text only: navigation, headers/footers, scripts and images removed; '
          'tables kept as `cell | cell` lines, code kept in monospace.',
          '- Each source page starts with its section number, title and original URL/path, and has a PDF bookmark.']
    rep = os.path.join(a.outdir, a.report)
    open(rep, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    os.remove(cache_path)
    print(f'status: {status}')
    for p in problems:
        print('-', p)
    print('report:', rep)
    sys.exit(1 if any(not p.startswith('WARNING') for p in problems) else 0)


if __name__ == '__main__':
    main()
