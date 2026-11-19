"""Draw the picture a link to the site shows (public/og.png), in the fonts themselves.

    FONTS/.venv/bin/python tools/og.py FONTS
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from mark import FULL, Mark

SITE = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) / 'out'
PAPER, INK, SOFT = '#efeee9', '#1d1c1b', '#5e5b55'
im = Image.new('RGB', (1200, 630), PAPER)
d = ImageDraw.Draw(im)
hand = lambda size: ImageFont.truetype(str(OUT / 'PinboardBallpoint-Regular.otf'), size)
d.text((110, 150), '一粟', font=hand(300), fill=INK)
d.text((760, 190), '立於一畫', font=hand(64), fill=SOFT)
d.text((760, 290), 'Yisu', font=hand(64), fill=SOFT)
d.text((760, 390), '印泥  畫沙  漏痕', font=hand(40), fill=SOFT)
seal = Mark(sys.argv[1], FULL).image(104)
im.paste(seal, (986, 462), seal)
im.save(SITE / 'public' / 'og.png', optimize=True)
