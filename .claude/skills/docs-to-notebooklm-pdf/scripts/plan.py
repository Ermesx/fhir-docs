#!/usr/bin/env python3
"""Stage 2: decide which pages go into which PDF so every file stays inside NotebookLM's limits.

Rules (in this order):
  * keep chapters (groups) together; split a chapter only when it exceeds the word cap,
    and then into equal-sized parts on page boundaries;
  * merge neighbouring small chapters (up to the cap) only when the file count would exceed --max-files;
  * if even that is not enough, raise the cap toward --hard-cap and say so.

The cap is on words *as extracted*. PDF text extraction later counts ~5-25% more words
(table separators, wrapped code), so the default 300k extracted words lands at ~330-375k in the PDF,
safely under NotebookLM's 500k-words-per-source limit. verify.py checks the real numbers.
"""
import argparse, json, re, math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pages')
    ap.add_argument('out', help='parts.json')
    ap.add_argument('--name', required=True, help='short doc name used in file names, e.g. ProductX-v2')
    ap.add_argument('--cap', type=int, default=300000, help='max extracted words per PDF')
    ap.add_argument('--hard-cap', type=int, default=380000)
    ap.add_argument('--max-files', type=int, default=50)
    a = ap.parse_args()

    P = [json.loads(l) for l in open(a.pages, encoding='utf-8')]
    P.sort(key=lambda p: p['i'])
    groups, gtitle = [], {}
    for p in P:
        if not groups or groups[-1][0] != p['group']:
            groups.append([p['group'], []])
        groups[-1][1].append(p)
        if p['group'] not in gtitle:
            gtitle[p['group']] = p['title'] if p['sec'] and '.' not in p['sec'] else p['group']

    def build(cap, merge):
        units = []  # list of (label, title, pages)
        for g, pages in groups:
            units.append((g, gtitle[g], pages))
        if merge:  # merge small neighbours greedily
            merged = []
            for u in units:
                if merged and sum(x['words'] for x in merged[-1][2]) + sum(x['words'] for x in u[2]) <= cap:
                    l, t, ps = merged[-1]
                    merged[-1] = (f'{l}-{u[0]}', f'{t} + {u[1]}', ps + u[2])
                else:
                    merged.append(u)
            units = merged
        parts = []
        for label, title, pages in units:
            tot = sum(p['words'] for p in pages)
            k = max(1, math.ceil(tot / cap))
            target = tot / k
            chunks, cur, w = [], [], 0
            for p in pages:
                if cur and w + p['words'] > target * 1.05 and len(chunks) < k - 1:
                    chunks.append(cur); cur, w = [], 0
                cur.append(p); w += p['words']
            chunks.append(cur)
            for j, ch in enumerate(chunks):
                parts.append(dict(label=label, title=title, part=j + 1, of=len(chunks), lo=ch[0]['i'],
                                  hi=ch[-1]['i'] + 1, first=ch[0]['sec'] or ch[0]['href'],
                                  last=ch[-1]['sec'] or ch[-1]['href'], pages=len(ch),
                                  words=sum(p['words'] for p in ch),
                                  max_page_words=max(p['words'] for p in ch)))
        return parts

    cap, notes = a.cap, []
    parts = build(cap, merge=False)
    if len(parts) > a.max_files:
        parts = build(cap, merge=True)
        notes.append('merged neighbouring small chapters to fit the file limit')
    while len(parts) > a.max_files and cap < a.hard_cap:
        cap = min(a.hard_cap, int(cap * 1.1))
        parts = build(cap, merge=True)
        notes.append(f'raised word cap to {cap}')
    if len(parts) > a.max_files:
        notes.append(f'STILL {len(parts)} files > {a.max_files}: split the corpus into several notebooks '
                     f'or drop low-value sections (e.g. large generated reference listings)')

    for n, p in enumerate(parts, 1):
        slug = re.sub(r'[^A-Za-z0-9]+', '-', p['title']).strip('-')[:40] or 'part'
        label = p['label'] if len(p['label']) <= 12 else p['label'][:12]
        suffix = f"_part{p['part']}-of-{p['of']}" if p['of'] > 1 else ''
        lab = re.sub(r'[^A-Za-z0-9-]+', '-', label)
        mid = slug if slug.lower() == lab.lower() else f'{lab}_{slug}'
        p['file'] = f"{a.name}_{n:02d}_{mid}{suffix}.pdf"
        span = f" (sections {p['first']} – {p['last']})" if p['first'] != p['last'] else ''
        p['doc_title'] = f"{a.name} — {p['title']}" + (f" — part {p['part']} of {p['of']}" if p['of'] > 1 else '') + span
        if p['max_page_words'] > cap:
            notes.append(f"{p['file']}: a single page has {p['max_page_words']} words (> cap); it cannot be split on page boundaries")
    json.dump({'name': a.name, 'cap': cap, 'notes': notes, 'parts': parts}, open(a.out, 'w'), ensure_ascii=False, indent=1)
    for p in parts:
        print(f"{p['file']}  pages={p['pages']} words={p['words']}  {p['first']} .. {p['last']}")
    print(f'{len(parts)} PDFs, total words {sum(p["words"] for p in parts)}, cap {cap}')
    for x in notes:
        print('NOTE:', x)


if __name__ == '__main__':
    main()
