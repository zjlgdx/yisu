# 一粟 Yisu: the website

The site for 一粟 (Yisu), three hand-drawn open-source Chinese fonts: 印泥 (the Typewriter), 畫沙 (the Ballpoint) and 漏痕 (the Marker). The fonts are built in [zjlgdx/pinboard-fonts](https://github.com/zjlgdx/pinboard-fonts), where their files still carry the name Pinboard.

The page writes its texts a stroke at a time, in vertical columns from right to left: 王羲之's 蘭亭集序 by day (the theme 天雨粟) and the opening of 蘇軾's 前赤壁賦 by night (鬼夜哭). Nothing on it is a picture of type. The scroll is drawn on a canvas from the fonts' own centre lines with the fonts' own pens; everything else, the specimens and the box to type in included, is set in the fonts themselves. A recorded voice can read each sentence as it is written, and the writing keeps time with it.

## The name

一粟 is one grain of millet, from 前赤壁賦: 「寄蜉蝣於天地，渺滄海之一粟」. The two themes take their names from the 淮南子's story of the day writing was invented: 「倉頡作書，而天雨粟，鬼夜哭」. The tagline 立於一畫 is 石濤's.

## What is here

| Path | What it is |
| --- | --- |
| `public/index.html` | The whole page: styles, markup and the script that writes. |
| `public/strokes.js` | Stroke data for the characters the page itself shows. Generated. |
| `public/strokes-all.js` | Stroke data for every other character, fetched when a reader asks for one. Generated. |
| `public/fonts/*.woff2`, `faces.css` | The three families in both weights, cut down to what the page shows in each. Generated. |
| `public/fonts/full/` | Every font whole, in slices of 300 characters that a browser fetches as a reader types. Generated, about 45 MB, not committed. |
| `public/audio/vo/`, `vo.json` | The narration, one clip per sentence, and each clip's length. Generated. |
| `public/audio/day.mp3`, `night.mp3` | The music for each theme. Generated. |
| `public/og.png` | The picture a link to the site shows. Generated. |
| `public/favicon.svg`, `favicon.png`, `apple-touch-icon.png` | The mark: a red seal cut with 一粟, and its simpler form for browser tabs. Generated, as is the mark in the page's navigation. |
| `public/_headers` | Cache rules for the files above. |
| `tools/` | The scripts that generate those files. |
| `tools/extra.py` | Five characters the two texts need that the fonts don't draw yet, put together from parts the fonts already have. |
| `wrangler.jsonc` | The Cloudflare Workers configuration. |

## Regenerating the data

Most of the generated files come from a checkout of the fonts with its Python environment set up and the fonts built in `out/`:

```
FONTS=../pinboard-fonts
$FONTS/.venv/bin/python tools/strokes.py $FONTS
$FONTS/.venv/bin/python tools/webfonts.py $FONTS full
$FONTS/.venv/bin/python tools/mark.py $FONTS
$FONTS/.venv/bin/python tools/og.py $FONTS
```

Run them again after the page's text changes, and after each release of the fonts. In `index.html`, `class="spec"` marks text set in all three families, and `class="far"` marks the two long texts.

The sound is made apart from the fonts:

```
MINIMAX_API_KEY=... python3 -I tools/audio.py
python3 -I tools/hear.py Unihan_Readings.txt
$FONTS/.venv/bin/python tools/music.py
```

`tools/audio.py` asks MiniMax's speech synthesis for one clip per sentence (run it again when a text changes; the page paces its writing by the clips' lengths). `tools/hear.py UNIHAN_READINGS` then checks the reading without anyone listening: whisper-cli writes down what each clip says, and that is set against the text sound by sound (Unihan's Mandarin readings, tones aside). A clip it marks LISTEN gets another take (`TAKES` in `tools/audio.py`) or a person's ear. `tools/music.py` needs only numpy and ffmpeg: it works out each plucked note itself, so nothing in the music is recorded or sampled.

## Looking at it

```
python3 -m http.server --directory public
```

## Deploying

The site is static files served by a Cloudflare Worker (`wrangler.jsonc`, assets in `public/`). Its domain is yisu.aixie.de for now.

```
npx wrangler deploy
```

`public/fonts/full/` is not in the repository, so make it first (`tools/webfonts.py FONTS full`), or the box to type in falls back to the reader's own fonts for characters the page doesn't already show.

## Licence

The stroke data and the font files come from the fonts and are under the SIL Open Font License 1.1 (`OFL.txt`). The page and the tools are under MIT (`LICENSE`).
