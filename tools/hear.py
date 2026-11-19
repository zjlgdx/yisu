"""Check the narration's pronunciation by transcribing it back: nobody here can listen.

    python3 -I tools/hear.py UNIHAN_READINGS [clip-name ...]

For each clip in public/audio/vo/ (or just the ones named, as lanting-05), on its own
and with 0.6 s of silence after it, whisper-cli writes down what it hears, and that is
set against the sentence the clip should say, syllable by syllable. A classical text
comes back as modern homophones (會稽 as 会计), so characters are compared by sound:
two match when Unihan gives them a Mandarin reading in common, tones aside.

    =  same sound          ~  near (in/ing, z/zh, n/l: what a recogniser mixes up)
    x  a different sound   -  nothing heard for it

A clip with an x or a - is one to listen to. This is a sieve, not an ear: it cannot
hear tone, pace or feeling, and a recogniser makes mistakes of its own.

UNIHAN_READINGS is Unihan_Readings.txt from https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip.
Needs ffmpeg and whisper-cli, and a model at ~/.local/share/whisper/ (large-v3 or large-v3-turbo).
"""
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
VO = SITE / 'public' / 'audio' / 'vo'
MODELS = [Path.home() / '.local/share/whisper' / n for n in ('ggml-large-v3.bin', 'ggml-large-v3-turbo.bin')]
ENDS = '。！？；'
# What the narration is told to say where the 神龍本 writes another form (tools/audio.py's SAY).
SAY = {'脩': '修', '暎': '映', '俛': '俯', '攬': '覽', '領': '嶺', '迹': '跡'}


def plain(s):
    """A reading without its tone: xiū -> xiu, lǜ -> lv."""
    s = s.replace('ü', 'v').replace('ǖ', 'v').replace('ǘ', 'v').replace('ǚ', 'v').replace('ǜ', 'v')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if c.isascii() and c.isalpha())


def near(s):
    """The same reading with the pairs a recogniser confuses folded together."""
    s = re.sub(r'^(zh|ch|sh)', lambda m: m.group(1)[0], s)
    s = re.sub(r'^l', 'n', s)
    return re.sub(r'ng$', 'n', s)


def readings(path):
    table = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.startswith('U+'):
            code, field, value = line.split('\t')
            if field in ('kMandarin', 'kHanyuPinyin', 'kXHC1983', 'kHanyuPinlu', 'kTGHZ2013'):
                for word in re.split(r'[\s,]+', value):
                    sound = plain(word.split(':')[-1].split('(')[0])
                    if sound:
                        table.setdefault(chr(int(code[2:], 16)), set()).add(sound)
    return table


def align(want, heard, same):
    """Edit-distance alignment: for each wanted character, the heard one it pairs with, or None."""
    n, m = len(want), len(heard)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        cost[i][0] = i
    for j in range(m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(cost[i - 1][j] + 1, cost[i][j - 1] + 1,
                             cost[i - 1][j - 1] + (0 if same(want[i - 1], heard[j - 1]) == '=' else 0.5 if same(want[i - 1], heard[j - 1]) == '~' else 1))
    pairs, i, j = [], n, m
    while i > 0:
        if j > 0 and cost[i][j] == cost[i - 1][j - 1] + {'=': 0, '~': 0.5, 'x': 1}[same(want[i - 1], heard[j - 1])]:
            pairs.append(heard[j - 1]); i -= 1; j -= 1
        elif j > 0 and cost[i][j] == cost[i][j - 1] + 1:
            j -= 1
        else:
            pairs.append(None); i -= 1
    return pairs[::-1]


def main():
    table = readings(sys.argv[1])
    model = next((m for m in MODELS if m.exists()), None)
    if not model:
        sys.exit('no whisper model in ~/.local/share/whisper/')

    def same(a, b):
        ra, rb = table.get(a, {a}), table.get(b, {b})
        if a == b or ra & rb:
            return '='
        return '~' if {near(r) for r in ra} & {near(r) for r in rb} else 'x'

    html = (SITE / 'public' / 'index.html').read_text(encoding='utf-8')
    only, doubt, total = set(sys.argv[2:]), [], 0
    for piece in ('lanting', 'chibi', 'tengwang'):
        text = re.sub(r'<[^>]+>|\s+', '', re.search(rf'<p id="text-{piece}"[^>]*>(.*?)</p>', html, re.S).group(1))
        sents = [s for s in re.split(rf'(?<=[{ENDS}])', text) if s]
        for k, sent in enumerate(sents):
            name = f'{piece}-{k:02d}'
            if only and name not in only:
                continue
            want = [SAY.get(c, c) for c in sent if '㐀' <= c <= '鿿']
            with tempfile.TemporaryDirectory() as d:
                wav = str(Path(d) / 'a.wav')
                subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(VO / f'{name}.mp3'), '-af', 'apad=pad_dur=0.6',
                                '-ar', '16000', '-ac', '1', wav], check=True)
                out = subprocess.run(['whisper-cli', '-m', str(model), '-l', 'zh', '-nt', '-np', wav], capture_output=True, text=True).stdout
            heard = [c for c in out if '㐀' <= c <= '鿿']
            marks = ''.join('-' if h is None else same(w, h) for w, h in zip(want, align(want, heard, same)))
            total += 1
            flag = 'x' in marks or '-' in marks
            if flag:
                doubt.append(name)
            print(f'{name}  {"LISTEN" if flag else "ok    "}  {marks.count("=")}/{len(want)} same, {marks.count("~")} near\n'
                  f'    文 {"".join(want)}\n    聽 {"".join(heard)}\n       {marks.replace("=", "　").replace("~", "～").replace("x", "✗").replace("-", "？")}', flush=True)
    print(f'\n{total - len(doubt)} of {total} clips came back with every syllable the same or near. To listen to: {" ".join(doubt) or "none"}')


if __name__ == '__main__':
    main()
