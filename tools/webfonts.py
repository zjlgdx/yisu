"""Cut the three families down for the page, from a checkout of the fonts with out/ built.

    FONTS/.venv/bin/python tools/webfonts.py FONTS [full]

FONTS is a checkout of https://github.com/zjlgdx/pinboard-fonts. This writes

    public/fonts/<family>-<weight>.woff2   what index.html itself shows in that font
    public/fonts/huasha-400-t.woff2        the rest of the two texts under 讀全文
    public/fonts/faces.css                 the @font-face rules for those

and, with `full`, the whole of every font for the tester, in slices a browser fetches
only when a reader types a character from one (not committed: about 45 MB):

    public/fonts/full/<family>-<weight>-NN.woff2   Chinese characters, 300 to a file, most common first
    public/fonts/full/<family>-<weight>-a.woff2    everything else
    public/fonts/full/index.json                   what the page makes their @font-face rules from

In index.html, class="spec" marks text set in all three families, data-spec="..." names
more characters for them, and class="far" marks the two long texts.
"""
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

SITE = Path(__file__).resolve().parent.parent
PUB = SITE / 'public'
FAMILIES = {'yinni': ('Yisu Yinni', 'PinboardTypewriter'), 'huasha': ('Yisu Huasha', 'PinboardBallpoint'),
            'louhen': ('Yisu Louhen', 'PinboardMarker')}
WEIGHTS = {400: 'Regular', 700: 'Bold'}
SIZE = 300
# In every family whatever the page says: letters, figures, 注音 and the marks of a sentence.
ALWAYS = ''.join(map(chr, range(0x20, 0x7f))) + ''.join(map(chr, range(0x3105, 0x3130))) + 'ˉˊˇˋ˙，。、；：？！「」『』（）《》〈〉﹁﹂﹃﹄…—·“”‘’'
VOID = {'meta', 'link', 'input', 'br', 'img', 'hr', 'source', 'wbr'}


class Marked(HTMLParser):
    """The text inside elements of one class, and every data-spec value."""

    def __init__(self, cls):
        super().__init__()
        self.cls, self.stack, self.text = cls, [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('data-spec') and self.cls == 'spec':
            self.text.append(a['data-spec'])
        if tag not in VOID:
            self.stack.append(self.cls in (a.get('class') or '').split())

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if any(self.stack):
            self.text.append(data)


def marked(html, cls):
    p = Marked(cls)
    p.feed(html)
    return ''.join(p.text)


def han(c):
    return 0x3400 <= c <= 0x9fff or 0xf900 <= c <= 0xfaff or 0x20000 <= c <= 0x3ffff


def ranges(codes):
    """U+4E00-4E05,U+4E07 for a set of code points."""
    out, run = [], []
    for c in sorted(codes):
        if run and c == run[-1] + 1:
            run.append(c)
        else:
            run and out.append(run)
            run = [c]
    run and out.append(run)
    return ','.join(f'U+{r[0]:X}' + (f'-{r[-1]:X}' if len(r) > 1 else '') for r in out)


def cut(job):
    """One subset: (source .otf, code points, where to write)."""
    src, codes, out = job
    font = TTFont(src)
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['*']
    opts.name_IDs = [1, 2]
    opts.hinting = False
    opts.desubroutinize = True
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=codes)
    sub.subset(font)
    font.flavor = 'woff2'
    font.save(out)
    return str(Path(out).relative_to(PUB / 'fonts')), Path(out).stat().st_size


def main():
    fonts = Path(sys.argv[1]).resolve()
    html = (PUB / 'index.html').read_text(encoding='utf-8')
    far = marked(html, 'far')
    spec = set(map(ord, ALWAYS + marked(html, 'spec')))
    # Everything the file says outside the two long texts is the running text, in 畫沙.
    page = spec | set(map(ord, re.sub(r'<p[^>]*class="far"[^>]*>.*?</p>', '', html, flags=re.S)))
    texts = set(map(ord, far)) - page
    order = []
    for row in (fonts / 'hanzi_order.tsv').read_text(encoding='utf-8').splitlines():
        if row and not row.startswith('#'):
            col = row.split('\t')
            order += [ord(ch) for ch in col[3] + col[2] if han(ord(ch))]
    jobs, faces, index = [], [], []
    (PUB / 'fonts' / 'full').mkdir(parents=True, exist_ok=True)
    for key, (family, stem) in FAMILIES.items():
        for weight, style in WEIGHTS.items():
            src = str(fonts / 'out' / f'{stem}-{style}.otf')
            cmap = set(TTFont(src, lazy=True).getBestCmap())
            name = f'{key}-{weight}'
            base = (page if name == 'huasha-400' else spec) & cmap
            head = f'@font-face {{ font-family: "{family}"; font-weight: {weight}; font-display: swap; src: url('
            if name == 'huasha-400':
                jobs.append((src, sorted(texts & cmap), str(PUB / 'fonts' / f'{name}-t.woff2')))
                faces.append(f'{head}{name}-t.woff2) format("woff2"); unicode-range: {ranges(texts & cmap)}; }}')
                print('not in the fonts yet:', ''.join(chr(c) for c in sorted((page | texts) - cmap) if han(c)) or 'none')
            jobs.append((src, sorted(base), str(PUB / 'fonts' / f'{name}.woff2')))
            faces.append(f'{head}{name}.woff2) format("woff2"); }}')
            if 'full' in sys.argv[2:]:
                skip = base | (texts if name == 'huasha-400' else set())
                hanzi = list(dict.fromkeys(c for c in order if c in cmap)) if name == 'yinni-400' or not index else None
                if hanzi is not None:
                    hanzi += sorted(c for c in cmap if han(c) and c not in set(hanzi))
                    index_order = hanzi
                for q in range(0, len(index_order), SIZE):
                    part = [c for c in index_order[q:q + SIZE] if c in cmap and c not in skip]
                    if part:
                        jobs.append((src, part, str(PUB / 'fonts' / 'full' / f'{name}-{q // SIZE:02d}.woff2')))
                other = sorted(c for c in cmap if not han(c) and c not in skip)
                jobs.append((src, other, str(PUB / 'fonts' / 'full' / f'{name}-a.woff2')))
                index.append({'family': family, 'weight': weight, 'file': name,
                              'skip': ''.join(chr(c) for c in sorted(skip) if han(c)), 'other': ranges(other)})
    # The texts' own face comes first: a browser tries the last rule first, and that is the page's.
    (PUB / 'fonts' / 'faces.css').write_text(
        '/* Made by tools/webfonts.py. */\n' + '\n'.join(faces) + '\n', encoding='utf-8')
    with ProcessPoolExecutor(6) as pool:
        sizes = dict(pool.map(cut, jobs, chunksize=1))
    for k, v in sizes.items():
        if not k.startswith('full/'):
            print(f'{k}: {v // 1024} KB')
    if index:
        (PUB / 'fonts' / 'full' / 'index.json').write_text(
            json.dumps({'size': SIZE, 'order': ''.join(map(chr, index_order)), 'fonts': index},
                       ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        whole = [v for k, v in sizes.items() if k.startswith('full/')]
        print(f'full/: {len(whole)} files, {sum(whole) // 1048576} MB, {len(index_order)} characters in order')


if __name__ == '__main__':
    main()
