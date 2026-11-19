# 一粟 Yisu: the website

The site for 一粟 (Yisu), three hand-drawn open-source Chinese fonts: 印泥 (the Typewriter), 畫沙 (the Ballpoint) and 漏痕 (the Marker). The fonts are built in [zjlgdx/pinboard-fonts](https://github.com/zjlgdx/pinboard-fonts), where their files still carry the name Pinboard.

The page writes its texts a stroke at a time, in vertical columns from right to left: 王羲之's 蘭亭集序 by day (the theme 天雨粟) and the opening of 蘇軾's 前赤壁賦 by night (鬼夜哭). Nothing on it is a picture of type. Every character is drawn on a canvas from the fonts' own centre lines with the fonts' own pens, and the running text is set in 畫沙.

## The name

一粟 is one grain of millet, from 前赤壁賦: 「寄蜉蝣於天地，渺滄海之一粟」. The two themes take their names from the 淮南子's story of the day writing was invented: 「倉頡作書，而天雨粟，鬼夜哭」. The tagline 立於一畫 is 石濤's.

## What is here

| Path | What it is |
| --- | --- |
| `public/index.html` | The whole page: styles, markup and the script that writes. |
| `public/strokes.js` | Stroke data for the characters the page itself shows. Generated. |
| `public/strokes-all.js` | Stroke data for every other character, fetched when a reader asks for one. Generated. |
| `public/fonts/yisu-huasha.woff2` | 畫沙 cut down to the page's running text. Generated. |
| `public/og.png` | The picture a link to the site shows. Generated. |
| `tools/` | The scripts that generate the files above from a checkout of the fonts. |
| `tools/extra.py` | Five characters the two texts need that the fonts don't draw yet, put together from parts the fonts already have. |
| `wrangler.jsonc` | The Cloudflare Workers configuration. |

## Regenerating the data

The generated files come from a checkout of the fonts with its Python environment set up and, for the last two, the fonts built in `out/`:

```
FONTS=../pinboard-fonts
$FONTS/.venv/bin/python tools/strokes.py $FONTS
$FONTS/.venv/bin/python tools/bodyfont.py $FONTS
$FONTS/.venv/bin/python tools/og.py $FONTS
```

Run them again after the page's text changes, and after each release of the fonts.

## Looking at it

```
python3 -m http.server --directory public
```

## Deploying

The site is static files served by a Cloudflare Worker (`wrangler.jsonc`, assets in `public/`). Its domain is yisu.aixie.de for now.

```
npx wrangler deploy
```

## Licence

The stroke data and the font file come from the fonts and are under the SIL Open Font License 1.1 (`OFL.txt`). The page and the tools are under MIT (`LICENSE`).
