"""Draw the site's mark from the fonts' own outlines.

    FONTS/.venv/bin/python tools/mark.py FONTS [NAME]

FONTS is a checkout of the fonts with out/ built; NAME picks one of DESIGNS (default: CHOSEN).
Each design has two drawings on one square of 1000: the full mark, and a small one for
browser tabs, where there are only 16 px to draw in. Writes public/favicon.svg, favicon.png
and apple-touch-icon.png, and the mark in the page's navigation (between the "mark"
comments in public/index.html).
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
HAND, HAND_LIGHT, MARKER = 'YisuHuasha-Bold', 'YisuHuasha-Regular', 'YisuLouhen-Bold'
# What each colour name means by day, by night, and inside the page (which has both).
DAY = dict(ink='#1d1c1b', hot='#b3362b', seal='#b3362b', cream='#f6efe6', paper='#efeee9', chip='#f6f5f1')
NIGHT = dict(ink='#ece8da', hot='#d9b45a', seal='#c4472f', cream='#f6efe6', paper='#0b0f17', chip='#121927')
PAGE = dict(ink='var(--ink)', hot='var(--accent)', seal='var(--seal)', cream='#f6efe6', paper='var(--paper)', chip='var(--panel)')
# A drawing: tile is the rounded square behind (its corner radius and colour), parts are
# glyphs with the middle of their outline at (cx, cy), scaled to a width or a height, each
# in a named colour; cuts are glyphs taken out of the parts; gain thickens every stroke.
DESIGNS = {
    # A red seal cut with 一粟; for tabs, the top of 粟 is reduced to the one stroke: 一 over 米.
    'H': dict(
        full=dict(tile=(130, 'seal'), parts=[(HAND, '一', 500, 222, dict(w=620), 'cream'), (HAND, '粟', 506, 610, dict(h=575), 'cream')]),
        small=dict(tile=(170, 'seal'), gain=40, parts=[(MARKER, '一', 500, 205, dict(w=690), 'cream'), (MARKER, '米', 500, 628, dict(h=570), 'cream')])),
    # One grain, split by the one stroke.
    'I': dict(
        full=dict(parts=[(HAND, '、', 500, 500, dict(h=780), 'hot')], cuts=[(HAND_LIGHT, '一', 530, 540, dict(w=900))]),
        small=dict(parts=[(HAND, '、', 500, 500, dict(h=940), 'hot')], cuts=[(HAND, '一', 530, 548, dict(w=1250))])),
    # A grain over the sea: the one stroke in the marker's bold, the grain above it.
    'K': dict(
        full=dict(parts=[(MARKER, '一', 500, 700, dict(w=900), 'ink'), (HAND, '、', 640, 340, dict(h=360), 'hot')]),
        small=dict(tile=(190, 'chip'), gain=24, parts=[(MARKER, '一', 500, 710, dict(w=800), 'ink'), (HAND, '、', 630, 345, dict(h=390), 'hot')])),
}
CHOSEN = 'K'


class Mark:
    def __init__(self, fonts, spec, scale=1.0):
        self.spec, self.scale = spec, scale
        self.parts = [self.place(fonts, *p[:5]) + (p[5],) for p in spec['parts']]
        self.cuts = [self.place(fonts, *c) for c in spec.get('cuts', [])]

    def place(self, fonts, face, ch, cx, cy, size):
        path = Path(fonts) / 'out' / f'{face}.otf'
        font = TTFont(path)
        glyphs = font.getGlyphSet()
        glyph = glyphs[font.getBestCmap()[ord(ch)]]
        bounds = BoundsPen(glyphs)
        glyph.draw(bounds)
        x0, y0, x1, y1 = bounds.bounds
        k = self.scale
        s = (size['w'] / (x1 - x0) if 'w' in size else size['h'] / (y1 - y0)) * k
        cx, cy = 500 + (cx - 500) * k, 500 + (cy - 500) * k
        # The glyph's origin on the square; its y axis points up, the square's down.
        ox, oy = cx - (x0 + x1) / 2 * s, cy + (y0 + y1) / 2 * s
        pen = SVGPathPen(glyphs, ntos=lambda v: str(round(v)))
        glyph.draw(TransformPen(pen, Transform(s, 0, 0, -s, ox, oy)))
        return path, ch, s, ox, oy, pen.getCommands()

    def colours(self):
        return list(dict.fromkeys(p[6] for p in self.parts))

    def svg(self, colours=DAY, attrs='', square=False, night=None, uid='mark-cut'):
        """The mark as SVG. With night, the file follows the reader's light or dark setting."""
        gain, tile = self.spec.get('gain', 0), self.spec.get('tile')
        paint = lambda key: f'class="c-{key}"' if night else f'fill="{colours[key]}"'
        out = ''
        if night:
            keys = self.colours() + ([tile[1]] if tile else [])
            edge = lambda pal, k: f';stroke:{pal[k]}' if gain else ''
            rule = lambda pal: ''.join(f'.c-{k}{{fill:{pal[k]}{edge(pal, k)}}}' for k in keys)
            out += f'<style>{rule(colours)}@media(prefers-color-scheme:dark){{{rule(night)}}}</style>'
        if tile:
            out += f'<rect width="1000" height="1000" rx="{0 if square else tile[0]}" {paint(tile[1])} stroke-width="0"/>'
        ink = ''
        for key in self.colours():
            d = ''.join(p[5] for p in self.parts if p[6] == key)
            edge = f' stroke-width="{gain}" stroke-linejoin="round"' if gain else ''
            if gain and not night:
                edge += f' stroke="{colours[key]}"'
            ink += f'<path {paint(key)}{edge} d="{d}"/>'
        if self.cuts:
            d = ''.join(c[5] for c in self.cuts)
            out += (f'<mask id="{uid}"><rect width="1000" height="1000" fill="#fff"/><path d="{d}"/></mask>'
                    f'<g mask="url(#{uid})">{ink}</g>')
        else:
            out += ink
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"{attrs}>{out}</svg>'

    def image(self, px, colours=DAY, square=False, back=None):
        """The mark as a picture px wide, drawn large and then reduced."""
        big = px * max(4, -(-768 // px))
        k = big / 1000
        im = Image.new('RGBA', (big, big), back or (0, 0, 0, 0))
        tile, gain = self.spec.get('tile'), round(self.spec.get('gain', 0) * k / 2)
        if tile:
            ImageDraw.Draw(im).rounded_rectangle((0, 0, big - 1, big - 1), 0 if square else tile[0] * k, fill=colours[tile[1]])

        def write(d, part, value):
            path, ch, s, ox, oy = part[:5]
            d.text((ox * k, oy * k), ch, font=ImageFont.truetype(str(path), s * 1000 * k), fill=value, anchor='ls',
                   stroke_width=gain, stroke_fill=value)

        for key in self.colours():
            mask = Image.new('L', (big, big), 0)
            d = ImageDraw.Draw(mask)
            for p in self.parts:
                if p[6] == key:
                    write(d, p, 255)
            gain, keep = 0, gain
            for c in self.cuts:
                write(d, c, 0)
            gain = keep
            im.paste(Image.new('RGBA', (big, big), colours[key]), (0, 0), mask)
        return im.resize((px, px), Image.LANCZOS)


def touch(fonts, name):
    """The home-screen icon: no corners of its own (the phone cuts them), nothing see-through."""
    spec = DESIGNS[name]['full']
    if spec.get('tile'):
        return Mark(fonts, spec).image(180, square=True).convert('RGB')
    return Mark(fonts, spec, 0.78).image(180, back=DAY['paper']).convert('RGB')


def write(fonts, name, site=SITE):
    design = DESIGNS[name]
    full, small = Mark(fonts, design['full']), Mark(fonts, design['small'])
    (site / 'favicon.svg').write_text(small.svg(DAY, night=NIGHT) + '\n')
    small.image(32).save(site / 'favicon.png', optimize=True)
    touch(fonts, name).save(site / 'apple-touch-icon.png', optimize=True)
    page = site / 'index.html'
    inline = full.svg(PAGE, ' class="mark" aria-hidden="true"')
    html, n = re.subn(r'(<!--mark-->).*?(<!--/mark-->)', lambda m: m[1] + inline + m[2], page.read_text(), flags=re.S)
    assert n == 1, 'the page has no <!--mark--> … <!--/mark--> pair'
    page.write_text(html)
    return {f: (site / f).stat().st_size for f in ('favicon.svg', 'favicon.png', 'apple-touch-icon.png')} | {'inline': len(inline)}


if __name__ == '__main__':
    print(write(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else CHOSEN))
