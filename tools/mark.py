"""Draw the site's mark, a red seal cut with 一粟, from the fonts' own outlines.

    FONTS/.venv/bin/python tools/mark.py FONTS

FONTS is a checkout of the fonts with out/ built. Two drawings share one square of 1000:
the full seal (一 over 粟) for anything 40 px and up, and a small one for browser tabs,
where the top of 粟 is reduced to the one stroke, leaving 一 over 米, in a thicker pen with
some ink gain so that each stroke is about two pixels at 16 px.
Writes public/favicon.svg, favicon.png and apple-touch-icon.png, and the mark in the
page's navigation (between the "mark" comments in public/index.html).
"""
import re
import sys
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

SITE = Path(__file__).resolve().parent.parent / 'public'
SEAL, CREAM = '#b3362b', '#f6efe6'
HAND, MARKER = 'PinboardBallpoint-Bold', 'PinboardMarker-Bold'
# A drawing: the corner radius, the extra stroke width, and each glyph with the middle of
# its outline at (cx, cy) and either a width or a height, all on the square of 1000.
FULL = dict(radius=130, gain=0, glyphs=[(HAND, '一', 500, 222, dict(w=620)), (HAND, '粟', 506, 610, dict(h=575))])
SMALL = dict(radius=170, gain=40, glyphs=[(MARKER, '一', 500, 205, dict(w=690)), (MARKER, '米', 500, 628, dict(h=570))])


class Mark:
    def __init__(self, fonts, spec):
        self.spec, self.parts = spec, []
        for face, ch, cx, cy, size in spec['glyphs']:
            path = Path(fonts) / 'out' / f'{face}.otf'
            font = TTFont(path)
            glyphs = font.getGlyphSet()
            glyph = glyphs[font.getBestCmap()[ord(ch)]]
            bounds = BoundsPen(glyphs)
            glyph.draw(bounds)
            x0, y0, x1, y1 = bounds.bounds
            s = size['w'] / (x1 - x0) if 'w' in size else size['h'] / (y1 - y0)
            # The glyph's origin on the square; its y axis points up, the square's down.
            ox, oy = cx - (x0 + x1) / 2 * s, cy + (y0 + y1) / 2 * s
            pen = SVGPathPen(glyphs, ntos=lambda v: str(round(v)))
            glyph.draw(TransformPen(pen, Transform(s, 0, 0, -s, ox, oy)))
            self.parts.append((path, ch, s, ox, oy, pen.getCommands()))

    def svg(self, seal=SEAL, cream=CREAM, attrs='', square=False):
        r, gain = 0 if square else self.spec['radius'], self.spec['gain']
        ink = f'fill="{cream}"' + (f' stroke="{cream}" stroke-width="{gain}" stroke-linejoin="round"' if gain else '')
        d = ''.join(p[5] for p in self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"{attrs}>'
                f'<rect width="1000" height="1000" rx="{r}" fill="{seal}"/><path {ink} d="{d}"/></svg>')

    def image(self, px, square=False, seal=SEAL, cream=CREAM):
        """The mark as a picture px wide, drawn large and then reduced."""
        big = px * max(4, -(-768 // px))
        k = big / 1000
        im = Image.new('RGBA', (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, big - 1, big - 1), 0 if square else self.spec['radius'] * k, fill=seal)
        for path, ch, s, ox, oy, _ in self.parts:
            font = ImageFont.truetype(str(path), s * 1000 * k)
            d.text((ox * k, oy * k), ch, font=font, fill=cream, anchor='ls',
                   stroke_width=round(self.spec['gain'] * k / 2), stroke_fill=cream)
        return im.resize((px, px), Image.LANCZOS)


if __name__ == '__main__':
    full, small = Mark(sys.argv[1], FULL), Mark(sys.argv[1], SMALL)
    (SITE / 'favicon.svg').write_text(small.svg() + '\n')
    small.image(32).save(SITE / 'favicon.png', optimize=True)
    full.image(180, square=True).convert('RGB').save(SITE / 'apple-touch-icon.png', optimize=True)
    page = SITE / 'index.html'
    html = page.read_text()
    inline = full.svg('var(--seal)', CREAM, ' class="mark" aria-hidden="true"')
    html, n = re.subn(r'(<!--mark-->).*?(<!--/mark-->)', lambda m: m[1] + inline + m[2], html, flags=re.S)
    assert n == 1, 'the page has no <!--mark--> … <!--/mark--> pair'
    page.write_text(html)
    print('favicon.svg', (SITE / 'favicon.svg').stat().st_size, 'favicon.png', (SITE / 'favicon.png').stat().st_size,
          'apple-touch-icon.png', (SITE / 'apple-touch-icon.png').stat().st_size, 'inline', len(inline))
