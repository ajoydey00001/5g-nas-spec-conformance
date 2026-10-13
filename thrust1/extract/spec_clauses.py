"""Split a 3GPP spec (.zip with one .docx, or a .docx) into clauses.

  python3 -I spec_clauses.py 24501-h80.zip clauses.jsonl

One JSON object per clause: {"id": "5.4.2.2", "title": "...", "level": 4, "text": "..."}.
Clause boundaries are the Word heading paragraphs (styles "Heading 1".."Heading 9", which 3GPP uses as
"<number><TAB><title>"). Tables are kept as tab-separated rows inside the clause text.
"""
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
HEADING_ID = re.compile(r'^\s*([0-9A-Z]+(?:\.[0-9]+)*)\s+(.*)$')


def docx_bytes(path):
    if path.endswith('.docx'):
        return open(path, 'rb').read()
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.lower().endswith('.docx')][0]
    return z.read(name)


def heading_levels(docx):
    """styleId -> heading level, from styles.xml ("Heading 1" .. "Heading 9")."""
    levels = {}
    root = ET.fromstring(docx.read('word/styles.xml'))
    for st in root.iter(W + 'style'):
        name = st.find(W + 'name')
        if name is None:
            continue
        m = re.match(r'heading (\d)$', name.get(W + 'val', '').lower())
        if m:
            levels[st.get(W + 'styleId')] = int(m.group(1))
    return levels


def para_text(p):
    out = []
    for node in p.iter():
        if node.tag == W + 't' and node.text:
            out.append(node.text)
        elif node.tag == W + 'tab':
            out.append('\t')
        elif node.tag in (W + 'br', W + 'cr'):
            out.append('\n')
    return ''.join(out)


def blocks(body):
    """Yield ('p', style, text) and ('tbl', None, text) in document order."""
    for child in body:
        if child.tag == W + 'p':
            ppr = child.find(W + 'pPr')
            style = None
            if ppr is not None and ppr.find(W + 'pStyle') is not None:
                style = ppr.find(W + 'pStyle').get(W + 'val')
            yield 'p', style, para_text(child)
        elif child.tag == W + 'tbl':
            rows = []
            for tr in child.iter(W + 'tr'):
                cells = [' '.join(para_text(p) for p in tc.iter(W + 'p')).strip() for tc in tr.iter(W + 'tc')]
                rows.append('\t'.join(cells))
            yield 'tbl', None, '\n'.join(rows)
        elif child.tag == W + 'sdt':  # content controls (e.g. the table of contents)
            content = child.find(W + 'sdtContent')
            if content is not None:
                yield from blocks(content)


def clauses(path):
    docx = zipfile.ZipFile(io.BytesIO(docx_bytes(path)))
    levels = heading_levels(docx)
    body = ET.fromstring(docx.read('word/document.xml')).find(W + 'body')
    cur = None
    for kind, style, text in blocks(body):
        if kind == 'p' and style in levels:
            m = HEADING_ID.match(text.replace('\t', ' '))
            if m:
                if cur:
                    yield cur
                cur = {'id': m.group(1), 'title': m.group(2).strip(), 'level': levels[style], 'text': []}
                continue
        if cur is not None and text.strip():
            cur['text'].append(text.strip())
    if cur:
        yield cur


def main(src, dst):
    n = 0
    with open(dst, 'w') as f:
        for c in clauses(src):
            c['text'] = '\n'.join(c['text'])
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
            n += 1
    print('%d clauses -> %s' % (n, dst))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
