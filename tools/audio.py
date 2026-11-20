"""Make the site's narration with MiniMax's speech synthesis.

    MINIMAX_API_KEY=... python3 -I tools/audio.py

One clip per sentence of the texts in public/index.html, in public/audio/vo/,
and their lengths in public/audio/vo.json, with when each clause in them begins
(under "marks"). The page paces its writing to these
lengths, so run this again whenever a text changes. (The music is tools/music.py:
MiniMax's music API no longer takes new accounts.)

Each API answer is kept in .audio-cache/ under a hash of what was asked, so a second
run only asks for what changed. Needs ffmpeg. The key is read from the environment,
sent only to api.minimax.io and never printed.
"""
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
AUDIO = SITE / 'public' / 'audio'
CACHE = SITE / '.audio-cache'
HOST = 'https://api.minimax.io'

VOICE = {'model': 'speech-2.8-hd', 'voice_id': 'Chinese (Mandarin)_Radio_Host', 'speed': 0.72, 'emotion': 'calm'}
# A recitation breathes at every comma: this long, in seconds.
BREATH = 0.45
# Readings the voice would otherwise get wrong: classical senses of common characters.
TONES = ['會稽/(kuai4)(ji1)', '少長咸集/(shao4)(zhang3)(xian2)(ji2)', '夫人之相與/(fu2)(ren2)(zhi1)(xiang1)(yu3)',
         '悲夫/(bei1)(fu2)', '趣舍/(qu3)(she3)', '信可樂也/(xin4)(ke3)(le4)(ye3)', '流觴曲水/(liu2)(shang1)(qu1)(shui3)',
         '一觴一詠/(yi4)(shang1)(yi4)(yong3)', '彭殤/(peng2)(shang1)', '騁懷/(cheng3)(huai2)', '激湍/(ji1)(tuan1)',
         '形骸/(xing2)(hai2)', '嗟悼/(jie1)(dao4)', '修禊/(xiu1)(xi4)', '虛誕/(xu1)(dan4)', '舉酒屬客/(ju3)(jiu3)(zhu3)(ke4)',
         '馮虛御風/(ping2)(xu1)(yu4)(feng1)', '少焉/(shao3)(yan1)', '斗牛/(dou3)(niu2)', '窈窕/(yao3)(tiao3)', '壬戌/(ren2)(xu1)']
# The same for 滕王閣序, apart: a clip is kept under a hash of what was asked, this list included,
# so adding to the list above would ask for the first two texts all over again.
TONES_MORE = {'tengwang': [
         '翼軫/(yi4)(zhen3)', '甌越/(ou1)(yue4)', '牛斗/(niu2)(dou3)', '陳蕃/(chen2)(fan2)', '棨戟/(qi3)(ji3)', '懿範/(yi4)(fan4)',
         '襜帷/(chan1)(wei2)', '勝餞/(sheng4)(jian4)', '潦水/(lao3)(shui3)', '驂騑/(can1)(fei1)', '崇阿/(chong2)(e1)',
         '鶴汀鳧渚/(he4)(ting1)(fu2)(zhu3)', '重霄/(chong2)(xiao1)', '繡闥/(xiu4)(ta4)', '雕甍/(diao1)(meng2)', '駭矚/(hai4)(zhu3)',
         '舸艦/(ge3)(jian4)', '之舳/(zhi1)(zhu2)', '雨霽/(yu3)(ji4)', '彭蠡/(peng2)(li3)', '遄飛/(chuan2)(fei1)',
         '爽籟/(shuang3)(lai4)', '雲遏/(yun2)(e4)', '睢園/(sui1)(yuan2)', '鄴水/(ye4)(shui3)', '睇眄/(di4)(mian3)', '二難並/(er4)(nan2)(bing4)',
         '地迥/(di4)(jiong3)', '吳會/(wu2)(kuai4)', '南溟/(nan2)(ming2)', '帝閽/(di4)(hun1)', '多舛/(duo1)(chuan3)', '涸轍/(he2)(zhe2)',
         '雖賒/(sui1)(she1)', '寧移/(ning4)(yi2)', '處涸/(chu3)(he2)', '宗愨/(zong1)(que4)', '簪笏/(zan1)(hu4)', '叨陪/(tao1)(pei2)',
         '捧袂/(peng3)(mei4)', '梓澤/(zi3)(ze2)', '恭疏/(gong1)(shu1)', '鳴鸞/(ming2)(luan2)', '朝飛/(zhao1)(fei1)', '暮捲/(mu4)(juan3)',
         '檻外/(jian4)(wai4)', '江渚/(jiang1)(zhu3)', '長風/(chang2)(feng1)', '長洲/(chang2)(zhou1)',
         '興盡/(xing4)(jin4)', '逸興/(yi4)(xing4)', '有數/(you3)(shu4)', '賈誼/(jia3)(yi4)', '長沙/(chang2)(sha1)', '都督/(du1)(du1)',
         '紆其/(yu1)(qi2)', '難越/(nan2)(yue4)', '嗟乎/(jie1)(hu1)', '馮唐/(feng2)(tang2)', '難封/(nan2)(feng1)', '海曲/(hai3)(qu1)',
         '老當益壯/(lao3)(dang1)(yi4)(zhuang4)', '弱冠/(ruo4)(guan4)', '嗚乎/(wu1)(hu1)', '難再/(nan2)(zai4)', '閒雲/(xian2)(yun2)',
         '幾度/(ji3)(du4)', '勝友/(sheng4)(you3)', '序屬/(xu4)(shu3)', '偉餞/(wei3)(jian4)']}
# The 神龍本's forms, said as the characters they stand for.
SAY = [('脩', '修'), ('暎', '映'), ('俛', '俯'), ('攬', '覽'), ('峻領', '峻嶺'), ('陳迹', '陳跡'), ('「', ''), ('」', '')]
ENDS = '。！？；'
# A closing quotation mark stays with the sentence it closes: 「…死生亦大矣。」豈不痛哉！
CLOSE = '」』'
# Asked for alone, a sentence of a few characters comes back read in a hurry, half as fast
# again as the rest. Those are asked for slower.
SHORT, SHORT_SPEED = 4, 0.55
PIECES = ('lanting', 'chibi', 'tengwang')
# Which reading of a sentence is used, where the first came back from tools/hear.py with a
# syllable in doubt: the clip's name and the take that transcribed cleanly. (lanting-03's 湍
# came back as tan or duan in four takes out of four; a listener has to judge that one. So
# with seven clips of 滕王閣序: 棨戟 in tengwang-07, 崇阿 in 18, 岡巒 in 23, 地迥 in 38,
# 不墜 in 52, the 勃 that opens 58 and 簪笏 in 60, rare words a recogniser writes down as
# commoner ones take after take, with the reading pinned or not.)
TAKES = {'chibi-07': 2, 'lanting-07': 2, 'lanting-12': 2,
         'tengwang-02': 2, 'tengwang-03': 2, 'tengwang-51': 2, 'tengwang-54': 2, 'tengwang-58': 2, 'tengwang-66': 2, 'tengwang-67': 2, 'tengwang-69': 2}
# A reading pinned for one clip only, so that only that clip is asked for again.
PINS = {'tengwang-23': ['岡巒/(gang1)(luan2)'], 'tengwang-52': ['不墜/(bu2)(zhui4)']}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: urllib would send the key along to wherever it points."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, 'refusing a redirect', headers, fp)


OPENER = urllib.request.build_opener(NoRedirect)


def ask(path, body, timeout, take=1):
    """POST body to the API; the answer's audio as a file, from the cache when this was asked before.
    The same words asked again come back read a little differently: take 2, 3... keep those apart."""
    key = hashlib.sha1(json.dumps([path, body] + [take] * (take > 1), sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    cached = CACHE / (key + '.mp3')
    if cached.exists():
        return cached
    CACHE.mkdir(exist_ok=True)
    req = urllib.request.Request(HOST + path, json.dumps(body).encode(),
                                 {'Authorization': 'Bearer ' + os.environ['MINIMAX_API_KEY'], 'Content-Type': 'application/json'})
    for attempt in range(5):  # the endpoint returns the odd 502
        try:
            res = json.load(OPENER.open(req, timeout=timeout))
            break
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 4:
                raise
            time.sleep(2 ** attempt)
    if res.get('base_resp', {}).get('status_code', 0) != 0:
        raise RuntimeError(res['base_resp'])
    cached.write_bytes(binascii.unhexlify(res['data']['audio']))
    return cached


def ffmpeg(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)


def seconds(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)]))


def lufs(path):
    # Loop the clip so a short sentence passes the meter's 400 ms gate.
    out = subprocess.run(['ffmpeg', '-nostats', '-stream_loop', '5', '-i', str(path), '-af', 'ebur128', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', out)[-1])


def sentences(text):
    out, cur = [], ''
    for ch in text:
        if ch in CLOSE and not cur and out:
            out[-1] += ch
            continue
        cur += ch
        if ch in ENDS:
            out.append(cur)
            cur = ''
    return out + ([cur] if cur else [])


def breaths(path, n):
    """When each clause after the first begins in a clip: the ends of its n longest pauses, in
    order. The page writes each clause by these, so the caption and the pen keep with the voice.
    None when the clip doesn't show n clear pauses."""
    if not n:
        return []
    out = subprocess.run(['ffmpeg', '-nostats', '-i', str(path), '-af', 'silencedetect=noise=-40dB:d=0.2', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    lens = [float(x) for x in re.findall(r'silence_duration: ([\d.]+)', out)]
    gaps = sorted(zip(lens, ends), reverse=True)[:n]
    return sorted(round(e, 2) for _, e in gaps) if len(gaps) == n else None


def voice():
    page = (SITE / 'public' / 'index.html').read_text(encoding='utf-8')
    (AUDIO / 'vo').mkdir(parents=True, exist_ok=True)
    lengths, marks = {}, {}
    # Silence off both ends, but the last syllable's fall kept (a tenth of a second below the
    # threshold), then faded, so no clip stops in the middle of a sound.
    trim = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,areverse,'
            'silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.1,areverse')
    for piece in PIECES:
        lengths[piece], marks[piece] = [], []
        for i, sentence in enumerate(sentences(re.sub(r'<[^>]+>|\s+', '', re.search(rf'<p id="text-{piece}"[^>]*>(.*?)</p>', page, re.S).group(1)))):
            said = sentence
            for a, b in SAY:
                said = said.replace(a, b)
            said = re.sub(r'([，、：])(?=.)', rf'\1<#{BREATH}#>', said)
            raw = ask('/v1/t2a_v2', {
                'model': VOICE['model'], 'text': said, 'stream': False, 'language_boost': 'Chinese',
                'voice_setting': {'voice_id': VOICE['voice_id'], 'vol': 1, 'pitch': 0, 'emotion': VOICE['emotion'],
                                  'speed': SHORT_SPEED if len(re.findall(r'[\u3400-\u9fff]', said)) <= SHORT else VOICE['speed']},
                'pronunciation_dict': {'tone': TONES_MORE.get(piece, TONES) + PINS.get(f'{piece}-{i:02d}', [])},
                'audio_setting': {'sample_rate': 32000, 'bitrate': 128000, 'format': 'mp3', 'channel': 1}}, 90, TAKES.get(f'{piece}-{i:02d}', 1))
            # Each sentence is a separate take, so its silences and loudness drift: trim, then level.
            out = AUDIO / 'vo' / f'{piece}-{i:02d}.mp3'
            wav = CACHE / 'trimmed.wav'
            ffmpeg('-i', str(raw), '-af', trim, str(wav))
            gain, d = max(-12, min(12, -19 - lufs(wav))), seconds(wav)
            ffmpeg('-i', str(wav), '-af', f'volume={gain:.2f}dB,alimiter=limit=0.89,afade=t=in:d=0.01,afade=t=out:st={d - 0.08:.3f}:d=0.08',
                   '-ar', '32000', '-ac', '1', '-b:a', '64k', str(out))
            lengths[piece].append(round(seconds(out), 2))
            marks[piece].append(breaths(out, said.count('<#')))
            print(f'{out.name} {lengths[piece][-1]:5.2f}s  {said}')
    (AUDIO / 'vo.json').write_text(json.dumps({**lengths, 'marks': marks}, separators=(',', ':')) + '\n')
    for piece, v in lengths.items():
        found = sum(m is not None for m in marks[piece])
        print(f'{piece}: {len(v)} sentences, {sum(v):.0f} s, the clauses found in {found}')


if __name__ == '__main__':
    voice()
