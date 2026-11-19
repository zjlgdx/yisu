"""Write the stroke data the page draws with, from a checkout of the fonts.

    FONTS/.venv/bin/python tools/strokes.py FONTS

FONTS is a checkout of https://github.com/zjlgdx/pinboard-fonts. Every character
there is a list of centre lines on a 1000 grid (y down), in the order they are
drawn; this writes them as {char: [[kind, [x, y, x, y, ...]], ...]}:

    public/strokes.js      the characters index.html itself shows, loaded with the page
    public/strokes-all.js  every other character, loaded when a reader asks for one
"""
import json
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
PUB = SITE / 'public'
FONTS = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(FONTS), str(FONTS / 'tools')]
import _repo
_repo.load(str(SITE / 'tools' / 'extra.py'))
import build
import hanzi


def thin(pts, tol):
    """Douglas-Peucker: the polyline without the points a straight run doesn't need."""
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    dx, dy = bx - ax, by - ay
    n = (dx * dx + dy * dy) ** 0.5
    far, at = 0, 0
    for i, (x, y) in enumerate(pts[1:-1], 1):
        # A stroke that ends where it began (the ring of 。) has no chord to measure from.
        d = abs((x - ax) * dy - (y - ay) * dx) / n if n > 1e-6 else ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5
        if d > far:
            far, at = d, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return thin(pts[:at + 1], tol)[:-1] + thin(pts[at:], tol)


def strokes(ch):
    out = []
    for kind, d in hanzi.flatten(hanzi.C[ch]):
        for pts, _closed in build.subpaths(d):
            line = thin([(x, y) for x, y, _c in pts], 1.2)
            out.append([kind, [round(v) for x, y in line for v in (x, y)]])
    return out


def write(name, chars):
    data = {ch: strokes(ch) for ch in chars}
    path = PUB / name
    path.write_text('window.YISU_STROKES=Object.assign(window.YISU_STROKES||{},'
                    + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ');\n', encoding='utf-8')
    print(f'{name}: {len(data)} characters, {path.stat().st_size // 1024} KB')


page = [ch for ch in dict.fromkeys((PUB / 'index.html').read_text(encoding='utf-8')) if ch in hanzi.C]
write('strokes.js', page)
write('strokes-all.js', [ch for ch in hanzi.C if ch not in page])
