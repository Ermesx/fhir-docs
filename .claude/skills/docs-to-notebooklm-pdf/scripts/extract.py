#!/usr/bin/env python3
"""Stage 1: turn a documentation source into clean text blocks, one JSON line per page.

Input: a .zip or a folder holding HTML (.html/.htm) and/or Markdown/text (.md/.markdown/.txt/.rst).
Output: pages.jsonl with {i, sec, title, href, group, words, blocks}
  blocks: ["h", level, text] | ["p", text] | ["pre", text] | ["t", [[cell, ...], ...]]

Page order:
  --toc FILE  a TOC/index page (path relative to the source root). Its links decide the order;
              links whose text starts with a section number ("4.3.1 Title") keep that number.
  otherwise   auto: look for a common TOC/summary/index page with many links, else natural path order.

Long runs can be split with --start/--end (indexes into the ordered page list) and --append,
so each call stays under a shell time limit.
"""
import argparse, json, os, re, sys, zipfile, warnings, posixpath
from urllib.parse import unquote

try:
    from bs4 import BeautifulSoup, NavigableString, Tag, Comment, XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    sys.exit("pip install beautifulsoup4 lxml")

HTML_EXT = ('.html', '.htm', '.xhtml')
TEXT_EXT = ('.md', '.markdown', '.txt', '.rst')
SECNUM = re.compile(r'^(\d+(?:\.\d+)*)\.?\s+(.*)$')
CONTENT_SELECTORS = ['main', '[role=main]', 'article', '[id$=-content]', '#content', '.content',
                     '#main-content', '.main-content', '.document', '.body', '#main']
DROP_SELECTORS = ['script', 'style', 'noscript', 'nav', 'header', 'footer', 'aside', 'form', 'iframe',
                  'svg', 'img', 'button', 'input', 'select', '[id*=navbar]', '[id*=breadcrumb]',
                  '[id$=-footer]', '[id$=-header]', '.navbar', '.breadcrumb', '.sidebar', '.toc-sidebar',
                  '.headerlink', '[role=navigation]']
BLK = ['p', 'div', 'li', 'br', 'dt', 'dd', 'ul', 'ol', 'table', 'tr', 'td', 'th', 'pre',
       'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']


def clean(t):
    return re.sub(r'\s+', ' ', t).strip()


def txt(el):
    """Text of an element with block boundaries turned into spaces (avoids 'C reate' / 'wordword')."""
    for b in el.find_all(BLK):
        b.insert_before(' ')
        b.insert_after(' ')
    return clean(el.get_text(''))


def natural_key(s):
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)', s)]


# ---------------------------------------------------------------- source access
class Source:
    """Uniform read access to a zip or a folder. Paths are normalised to forward slashes
    (Windows-made zips often store backslashes)."""

    def __init__(self, path):
        self.zip = None
        self.files = {}
        if zipfile.is_zipfile(path):
            self.zip = zipfile.ZipFile(path)
            for n in self.zip.namelist():
                if not n.endswith(('/', '\\')):
                    self.files[n.replace('\\', '/')] = n
        else:
            for root, _, fs in os.walk(path):
                for f in fs:
                    full = os.path.join(root, f)
                    self.files[os.path.relpath(full, path).replace(os.sep, '/')] = full
        # strip a single common top folder ("site/", "docs-1.2/") so links resolve from the doc root
        tops = {p.split('/')[0] for p in self.files if '/' in p}
        self.prefix = ''
        if len(tops) == 1 and all('/' in p for p in self.files):
            self.prefix = tops.pop() + '/'

    def rel(self, p):
        return p[len(self.prefix):] if p.startswith(self.prefix) else p

    def doc_paths(self):
        return [self.rel(p) for p in self.files if p.lower().endswith(HTML_EXT + TEXT_EXT)]

    def exists(self, rel):
        return (self.prefix + rel) in self.files

    def read(self, rel):
        key = self.files[self.prefix + rel]
        if self.zip:
            data = self.zip.read(key)
        else:
            with open(key, 'rb') as f:
                data = f.read()
        return data.decode('utf-8', errors='replace')


# ---------------------------------------------------------------- ordering
def toc_entries(src, toc_rel, min_links=10):
    """Ordered (sec, title, href) from a TOC page. External links and duplicates are dropped,
    anchors are cut (first occurrence of a file wins)."""
    base = posixpath.dirname(toc_rel)
    out, seen = [], set()
    if toc_rel.lower().endswith(HTML_EXT):
        soup = BeautifulSoup(src.read(toc_rel), 'lxml')
        root = next((soup.select_one(s) for s in CONTENT_SELECTORS if soup.select_one(s)), soup.body or soup)
        links = [(clean(a.get_text(' ')), a['href']) for a in root.select('a[href]')]
    else:  # Markdown TOC such as SUMMARY.md
        links = re.findall(r'\[([^\]]+)\]\(([^)\s]+)', src.read(toc_rel))
    for text, href in links:
        if '://' in href or href.startswith(('mailto:', 'javascript:')):
            continue
        href = unquote(href.split('#')[0].split('?')[0]).replace('\\', '/')
        if not href:
            continue
        rel = posixpath.normpath(posixpath.join(base, href))
        if rel in seen or not src.exists(rel) or not rel.lower().endswith(HTML_EXT + TEXT_EXT):
            continue
        seen.add(rel)
        m = SECNUM.match(text)
        out.append((m.group(1), m.group(2), rel) if m else (None, text, rel))
    return out if len(out) >= min_links else []


def ordered_pages(src, toc):
    if toc:
        ents = toc_entries(src, toc, min_links=1)
        if not ents:
            sys.exit(f'TOC {toc} gave no usable links')
        return ents, f'toc:{toc}'
    for cand in ['toc.html', 'SUMMARY.md', 'summary.md', 'contents.html', 'genindex.html', 'index.html', 'README.md']:
        if src.exists(cand):
            ents = toc_entries(src, cand)
            if ents:
                return ents, f'auto-toc:{cand}'
    def key(p):  # folders in natural order; inside a folder: index/README first, then files, then subfolders
        parts = p.split('/')
        base = parts[-1].lower()
        first = 0 if re.match(r'(index|readme|intro|introduction|overview)\.', base) else 1
        return [(1, natural_key(d)) for d in parts[:-1]] + [(0, first, natural_key(base))]
    paths = sorted(src.doc_paths(), key=key)
    return [(None, None, p) for p in paths], 'path-order'


# ---------------------------------------------------------------- HTML -> blocks
def html_blocks(html, drop_re):
    soup = BeautifulSoup(html, 'lxml')
    title = clean(soup.title.get_text()) if soup.title else ''
    root = next((soup.select_one(s) for s in CONTENT_SELECTORS if soup.select_one(s)), soup.body or soup)
    for sel in DROP_SELECTORS:
        for el in root.select(sel):
            el.decompose()
    for c in root.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    out = []

    def add_p(t):
        if t and not (drop_re and drop_re.search(t)):
            out.append(['p', t])

    def walk(el):
        for c in el.children:
            if not isinstance(c, Tag):
                continue
            n = c.name
            cls = ' '.join(c.get('class') or [])
            if n in ('ul', 'ol') and re.search(r'\bnav|tabs?\b', cls):
                continue
            if n in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                t = txt(c)
                if t:
                    out.append(['h', int(n[1]), t])
            elif n == 'pre':
                t = c.get_text().strip('\n')
                if t.strip():
                    out.append(['pre', t])
            elif n == 'table':
                rows = []
                for tr in c.find_all('tr'):
                    cells = [txt(td) for td in tr.find_all(['td', 'th'], recursive=False)]
                    while cells and not cells[-1]:
                        cells.pop()
                    if any(cells):
                        rows.append(cells)
                if rows:
                    out.append(['t', rows])
            elif n in ('p', 'li', 'dt', 'dd', 'blockquote', 'caption', 'figcaption'):
                if c.find(['table', 'pre', 'h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol']):
                    direct = clean(''.join(s for s in c.find_all(string=True, recursive=False)))
                    if direct:
                        add_p(('• ' if n == 'li' else '') + direct)
                    walk(c)
                else:
                    t = txt(c)
                    if t:
                        add_p(('• ' if n == 'li' else '') + t)
            else:
                direct = clean(''.join(s for s in c.find_all(string=True, recursive=False)))
                if len(direct) > 2:
                    add_p(direct)
                walk(c)

    walk(root)
    return title, out


# ---------------------------------------------------------------- Markdown/text -> blocks
def md_blocks(text, drop_re):
    out, para, code, fence = [], [], [], None
    table = []
    title = ''

    def flush_para():
        if para:
            t = clean(' '.join(para))
            if t and not (drop_re and drop_re.search(t)):
                out.append(['p', t])
            para.clear()

    def flush_table():
        if table:
            out.append(['t', table[:]])
            table.clear()

    for line in text.splitlines():
        if fence is not None:
            if line.strip().startswith(fence):
                out.append(['pre', '\n'.join(code)])
                code.clear()
                fence = None
            else:
                code.append(line)
            continue
        s = line.strip()
        if s.startswith(('```', '~~~')):
            flush_para(); flush_table()
            fence = s[:3]
            continue
        m = re.match(r'^(#{1,6})\s+(.*?)\s*#*$', s)
        if m:
            flush_para(); flush_table()
            out.append(['h', len(m.group(1)), clean(m.group(2))])
            title = title or clean(m.group(2))
            continue
        if s.startswith('|') and s.endswith('|'):
            flush_para()
            cells = [clean(x) for x in s.strip('|').split('|')]
            if not all(re.fullmatch(r':?-{2,}:?', x) for x in cells if x):
                table.append(cells)
            continue
        flush_table()
        if not s:
            flush_para()
            continue
        li = re.match(r'^([-*+]|\d+[.)])\s+(.*)$', s)
        if li:
            flush_para()
            para.append('• ' + li.group(2))
            flush_para()
            continue
        para.append(s)
    flush_para(); flush_table()
    if code:
        out.append(['pre', '\n'.join(code)])
    return title, out


def block_words(b):
    if b[0] == 'h':
        return len(b[2].split())
    if b[0] == 't':
        return sum(len(' '.join(r).split()) for r in b[1])
    return len(b[1].split())


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', help='.zip or folder')
    ap.add_argument('out', help='pages.jsonl')
    ap.add_argument('--toc', help='TOC page path relative to the doc root (e.g. toc.html, SUMMARY.md)')
    ap.add_argument('--drop-regex', help='drop paragraphs matching this regex (boilerplate banners)')
    ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--end', type=int, default=10**9)
    ap.add_argument('--append', action='store_true', help='append to out instead of overwriting')
    ap.add_argument('--list-only', action='store_true', help='print page count and ordering method, then stop')
    a = ap.parse_args()

    drop_re = re.compile(a.drop_regex) if a.drop_regex else None
    src = Source(a.source)
    pages, how = ordered_pages(src, a.toc)
    print(f'order={how} pages={len(pages)} root_prefix={src.prefix!r}', flush=True)
    if a.list_only:
        return

    words_total = 0
    mode = 'a' if a.append else 'w'
    with open(a.out, mode, encoding='utf-8') as o:
        for i, (sec, title, rel) in enumerate(pages):
            if not (a.start <= i < a.end):
                continue
            raw = src.read(rel)
            if rel.lower().endswith(HTML_EXT):
                t2, blocks = html_blocks(raw, drop_re)
            else:
                t2, blocks = md_blocks(raw, drop_re)
            title = title or t2 or posixpath.basename(rel)
            # group = top-level chapter: first number of the section, else first folder, else 'root'
            if sec:
                group = sec.split('.')[0]
            else:
                group = rel.split('/')[0] if '/' in rel else 'root'
            w = sum(block_words(b) for b in blocks)
            words_total += w
            o.write(json.dumps({'i': i, 'sec': sec, 'title': title, 'href': rel, 'group': group,
                                'words': w, 'blocks': blocks}, ensure_ascii=False) + '\n')
            if i % 250 == 0:
                print(f'  {i}/{len(pages)} words so far {words_total}', flush=True)
    print(f'DONE range {a.start}:{min(a.end, len(pages))} of {len(pages)} words {words_total}', flush=True)


if __name__ == '__main__':
    main()
