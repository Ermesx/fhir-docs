#!/usr/bin/env python3
"""Stage 3: render each planned part as a lean, text-only A4 PDF with a bookmark per page.

No images, no colours, no navigation: just headings, paragraphs, tables as 'cell | cell' lines
and code in a monospace font. Every page starts with its section number, title and source URL/path,
so NotebookLM citations point back to the original.

  python render.py pages.jsonl parts.json OUTDIR [--base-url URL] [--only 3,4] [--source-label TEXT]
"""
import argparse, json, os, sys, textwrap, time
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Preformatted, Spacer

# Built-in PDF fonts (Helvetica/Courier): no font files needed, available in every PDF viewer.
# They cover Windows-1252 only, so other characters are mapped to ASCII look-alikes (see basic()).
R, B, M = 'Helvetica', 'Helvetica-Bold', 'Courier'
ASCII_MAP = {'→': '->', '←': '<-', '↔': '<->', '⇒': '=>', '≥': '>=', '≤': '<=',
             '≠': '!=', '✓': 'v', '✔': 'v', '✗': 'x', '✘': 'x', '−': '-',
             '‑': '-', '•': '*', '●': '*', ' ': ' ', '​': '', '﻿': ''}


def basic(text):
    for k, v in ASCII_MAP.items():
        text = text.replace(k, v)
    return text.encode('cp1252', 'replace').decode('cp1252')


body = ParagraphStyle('b', fontName=R, fontSize=9, leading=11.5, spaceAfter=3)
small = ParagraphStyle('t', fontName=R, fontSize=7.5, leading=9.5, spaceAfter=1, leftIndent=6)
mono = ParagraphStyle('m', fontName=M, fontSize=7, leading=8.5, spaceAfter=4)
H = {1: ParagraphStyle('h1', fontName=B, fontSize=14, leading=17, spaceBefore=10, spaceAfter=6),
     2: ParagraphStyle('h2', fontName=B, fontSize=11.5, leading=14, spaceBefore=8, spaceAfter=4),
     3: ParagraphStyle('h3', fontName=B, fontSize=10, leading=12.5, spaceBefore=6, spaceAfter=3)}
TITLE = ParagraphStyle('ti', fontName=B, fontSize=16, leading=20, spaceAfter=8)


class Doc(BaseDocTemplate):
    def __init__(self, *a, **k):
        BaseDocTemplate.__init__(self, *a, **k)
        self.addPageTemplates([PageTemplate('p', [Frame(15 * mm, 12 * mm, A4[0] - 30 * mm, A4[1] - 24 * mm)])])
        self.n, self.last = 0, -1

    def afterFlowable(self, f):
        lvl = getattr(f, '_ol', None)
        if lvl is None:
            return
        lvl = min(lvl, self.last + 1)  # PDF outlines cannot skip levels
        self.last = lvl
        self.n += 1
        key = f'k{self.n}'
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(f._olt[:150], key, level=lvl, closed=lvl > 0)


def para(text, style, ol=None):
    p = Paragraph(escape(basic(text)), style)
    if ol is not None:
        p._ol, p._olt = ol, text
    return p


def wrap_pre(t, width=120):
    lines = []
    for ln in t.expandtabs(2).split('\n'):
        ln = ln.rstrip()
        lines += [ln] if len(ln) <= width else (textwrap.wrap(ln, width, subsequent_indent='    ',
                                                              drop_whitespace=False) or [''])
    return lines


def render_part(part, pages, out_path, base_url, source_label):
    story = [para(part['doc_title'], TITLE),
             para(f'Source: {source_label}. Text-only edition for AI ingestion (NotebookLM); '
                  f'pages follow the source order (its table of contents when one exists).', body)]
    min_depth = min((p['sec'].count('.') for p in pages if p['sec']), default=0)
    for pg in pages:
        depth = (pg['sec'].count('.') - min_depth) if pg['sec'] else 0
        head = f"{pg['sec']} {pg['title']}" if pg['sec'] else pg['title']
        story.append(para(head, H[1], ol=max(0, min(depth, 3))))
        story.append(para(('URL: ' + base_url.rstrip('/') + '/' if base_url else 'File: ') + pg['href'], small))
        skip_first_h1 = True
        for b in pg['blocks']:
            k = b[0]
            if k == 'h':
                if skip_first_h1 and b[1] == 1:
                    skip_first_h1 = False
                    continue  # already printed as the page heading
                story.append(para(b[2], H[min(max(b[1], 2), 3)]))
            elif k == 'p':
                story.append(para(b[1], body))
            elif k == 'pre':
                L = wrap_pre(b[1])
                for i in range(0, len(L), 120):  # chunk so long listings can break across pages
                    story.append(Preformatted(basic('\n'.join(L[i:i + 120])), mono))
            elif k == 't':
                for r in b[1]:
                    story.append(para(' | '.join(r), small))
                story.append(Spacer(1, 3))
    Doc(out_path, pagesize=A4, title=part['doc_title'], subject='Text-only documentation for NotebookLM').build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages'); ap.add_argument('parts'); ap.add_argument('outdir')
    ap.add_argument('--base-url', default='', help='prefix that turns page paths into original URLs')
    ap.add_argument('--source-label', default='original documentation')
    ap.add_argument('--only', default='', help='comma-separated 1-based part numbers to render (for time-limited shells)')
    a = ap.parse_args()

    plan = json.load(open(a.parts, encoding='utf-8'))
    P = {}
    with open(a.pages, encoding='utf-8') as f:
        for line in f:
            p = json.loads(line)
            P[p['i']] = p
    os.makedirs(a.outdir, exist_ok=True)
    only = {int(x) for x in a.only.split(',') if x}
    for n, part in enumerate(plan['parts'], 1):
        if only and n not in only:
            continue
        t0 = time.time()
        pages = [P[i] for i in range(part['lo'], part['hi']) if i in P]
        out = os.path.join(a.outdir, part['file'])
        render_part(part, pages, out, a.base_url, a.source_label)
        print(f"OK {n:02d} {part['file']} pages={len(pages)} {os.path.getsize(out) / 1e6:.2f} MB {time.time() - t0:.1f}s", flush=True)


if __name__ == '__main__':
    sys.setrecursionlimit(10000)
    main()
