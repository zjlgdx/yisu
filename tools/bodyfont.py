"""Cut the Ballpoint (畫沙) down to the characters index.html uses, for its running text.

    FONTS/.venv/bin/python tools/bodyfont.py FONTS

FONTS is a checkout of https://github.com/zjlgdx/pinboard-fonts with the fonts
built in out/. Writes public/fonts/yisu-huasha.woff2.
"""
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

SITE = Path(__file__).resolve().parent.parent
PUB = SITE / 'public'
font = TTFont(Path(sys.argv[1]) / 'out' / 'PinboardBallpoint-Regular.otf')
# Not the two long texts: the page draws those on its canvas, a stroke at a time.
page = (PUB / 'index.html').read_text(encoding='utf-8').splitlines()
text = ''.join(dict.fromkeys(''.join(l for l in page if not l.startswith(('const LANTING', 'const CHIBI')))))
cmap = font.getBestCmap()
opts = subset.Options()
opts.flavor = 'woff2'
opts.layout_features = ['kern', 'ccmp', 'mark', 'mkmk', 'vert']
opts.name_IDs = [1, 2]
opts.hinting = False
opts.desubroutinize = True
sub = subset.Subsetter(opts)
sub.populate(text=text + ' ')
sub.subset(font)
font.flavor = 'woff2'
out = PUB / 'fonts' / 'yisu-huasha.woff2'
font.save(out)
missing = ''.join(ch for ch in text if ord(ch) > 0x2e7f and ord(ch) not in cmap and ch not in '')
print(f'{out.name}: {out.stat().st_size // 1024} KB; not in the font: {missing or "none"}')
