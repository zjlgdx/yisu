"""Make the site's two pieces of music: public/audio/day.mp3 and night.mp3.

    python3 tools/music.py          (needs numpy and ffmpeg)

Nothing is recorded or sampled. Each note is a plucked string worked out here (a
Karplus-Strong loop: a burst of noise going round a delay line that loses a little
of its top each time round), tuned and played the way a 古琴 is: low, slow, five
notes to the octave, with slides (綽), a slow vibrato on long notes (吟) and
harmonics (泛音). Night adds a few long notes of a 簫, made from sine partials and
filtered breath. Each piece is written by a seeded phrase-maker, so it comes out
the same every time, and it wraps round its own end so it can loop.

Day is in the 宮 mode on F (F G A C D); night in the 羽 mode on D (D F G A C).
"""
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

SITE = Path(__file__).resolve().parent.parent
OUT = SITE / 'public' / 'audio'
SR = 44100
LENGTH = 96                      # seconds; the piece loops


def shape(x, gain):
    """Filter x by a gain curve over frequency (Hz -> factor)."""
    spec = np.fft.rfft(x)
    return np.fft.irfft(spec * gain(np.fft.rfftfreq(len(x), 1 / SR)), len(x))


def warp(y, ratio):
    """Play y back at a pitch ratio that changes over time (slides and vibrato)."""
    pos = np.concatenate(([0], np.cumsum(ratio[:-1])))
    return np.interp(pos, np.arange(len(y)), y, right=0)


def string(freq, dur, rng, soft=0.5, ring=7.0, slide=0.0, shake=0.0):
    """One plucked note. soft: how gentle the pluck; ring: seconds to die away;
    slide: semitones it starts below its pitch; shake: depth of the vibrato."""
    n = max(8, int(round(SR / freq)))
    burst = rng.standard_normal(n)
    width = max(1, int(n * (0.04 + 0.10 * soft)))
    burst = np.convolve(np.concatenate((burst, burst)), np.ones(width) / width, 'same')[n // 2:n // 2 + n]
    burst -= np.roll(burst, int(n * 0.17))                    # where along the string it is plucked
    burst /= np.abs(burst).max() + 1e-9
    loss = 10 ** (-3 / (ring * SR / n))
    turns = int(dur * SR / n) + 2
    out = np.empty(turns * n)
    out[:n] = prev = burst
    carry = burst[-1]
    for t in range(1, turns):
        back = np.concatenate(([carry], prev[:-1]))
        carry = prev[-1]
        prev = loss * (0.62 * prev + 0.38 * back)
        out[t * n:(t + 1) * n] = prev
    t = np.arange(len(out)) / SR
    ratio = np.full(len(out), freq * n / SR)                  # the delay line is a whole number of samples
    if slide:
        ratio *= 2 ** (-slide / 12 * np.clip(1 - (t - 0.06) / 0.30, 0, 1))
    if shake:
        ratio *= 1 + shake * np.sin(2 * np.pi * 4.6 * t) * np.clip((t - 0.6) / 0.8, 0, 1)
    y = warp(out, ratio)[:int(dur * SR)]
    y[:64] *= np.linspace(0, 1, 64)
    y[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))
    return y


def harmonic(freq, dur):
    """泛音: the string touched lightly, a clear tone an octave up."""
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t / 1.6) + 0.18 * np.sin(2 * np.pi * 4 * freq * t) * np.exp(-t / 0.7)
    y[:200] *= np.linspace(0, 1, 200)
    return 0.5 * y


def xiao(freq, dur, rng):
    """A long note of the 簫: three partials, a breath, a late slow vibrato."""
    t = np.arange(int(dur * SR)) / SR
    bend = 2 ** (-0.3 / 12 * np.clip(1 - t / 0.18, 0, 1)) * (1 + 0.005 * np.sin(2 * np.pi * 4.8 * t) * np.clip((t - 0.9) / 1.0, 0, 1))
    phase = 2 * np.pi * freq * np.cumsum(bend) / SR
    env = np.clip(t / 0.45, 0, 1) ** 1.5 * np.clip((dur - t) / 0.9, 0, 1) ** 1.5
    tone = np.sin(phase) + 0.30 * np.sin(2 * phase) + 0.09 * np.sin(3 * phase)
    air = shape(rng.standard_normal(len(t)), lambda f: np.exp(-((f - 3200) / 1800) ** 2))
    air *= 0.5 / (np.abs(air).max() + 1e-9)
    return (tone + 0.10 * air) * env


def write(seed, tonic, night):
    """The piece as [(start, sound, gain)]. tonic is the mode's first note, in Hz."""
    rng = np.random.default_rng(seed)
    steps = [0, 3, 5, 7, 10] if night else [0, 2, 4, 7, 9]
    ladder = [tonic * 2 ** ((s + 12 * o) / 12) for o in (1, 2) for s in steps]        # the melody's two octaves
    rest = [0, 3] if night else [0, 3, 5]                     # degrees a phrase may end on (in the lower octave)
    notes, t, at = [], 1.5, 4
    while t < LENGTH - 3:                                     # the last phrase rings on over the loop's start
        if rng.random() < 0.65:                               # an open low string under the phrase
            low = tonic * (1 if rng.random() < 0.6 else 1.5)
            notes.append((t, string(low, 7.5, rng, soft=0.8, ring=9), 0.8))
        count = int(rng.integers(3, 6 if night else 7))
        for q in range(count):
            final = q == count - 1
            if final:
                at = min(rest, key=lambda d: abs(d - at) + 0.01 * d)
            else:
                at = int(np.clip(at + rng.choice([-2, -1, -1, 1, 1, 2]) + (1 if at < 2 else -1 if at > 7 else 0), 0, 9))
            gap = float(rng.choice([1.3, 1.7, 2.1, 2.6] if night else [1.1, 1.5, 1.9, 2.3]))
            dur = 7.0 if final else gap + 2.2
            slide = float(rng.choice([2, 3])) if rng.random() < (0.4 if night else 0.25) and not final else 0.0
            shake = 0.006 if final or dur > 4 else 0.0
            notes.append((t, string(ladder[at], dur, rng, soft=rng.uniform(0.3, 0.7), ring=8 if night else 7, slide=slide, shake=shake),
                          float(rng.uniform(0.6, 1.0))))
            t += gap
        if rng.random() < 0.3:
            notes.append((t + 0.4, harmonic(ladder[at], 4.0), 0.5))
        pause = float(rng.uniform(3.2, 5.2) if night else rng.uniform(2.6, 4.2))
        if night and rng.random() < 0.55:                     # the 簫 answers in the silence
            notes.append((t + 0.8, xiao(tonic * 4 * 2 ** (int(rng.choice([0, 3, 7])) / 12), pause + 2.5, rng), 0.16))
        t += pause
    return notes


def render(seed, tonic, night):
    n = LENGTH * SR
    dry = np.zeros(n)
    for start, sound, gain in write(seed, tonic, night):
        idx = (int(start * SR) + np.arange(len(sound))) % n   # a note that rings past the end comes round to the start
        np.add.at(dry, idx, sound * gain)
    # the instrument's body: a little warmth low down, nothing harsh on top
    dry = shape(dry, lambda f: (f / (f + 45)) * (1 + 0.6 * np.exp(-((f - 190) / 110) ** 2)) / (1 + (f / 3600) ** 2))
    rng = np.random.default_rng(seed + 1)
    tail, wet = (4.4, 0.42) if night else (2.9, 0.28)
    sides = []
    for _ in range(2):                                        # a room: decaying noise, different for each ear
        t = np.arange(n) / SR
        room = rng.standard_normal(n) * 10 ** (-3 * t / tail) * (t > 0.022) * (t < tail * 1.6)
        room = shape(room, lambda f: 1 / (1 + (f / 3800) ** 2) * (f / (f + 120)))
        room /= np.sqrt((room ** 2).sum())
        sides.append(dry + wet * 2.0 * np.fft.irfft(np.fft.rfft(dry) * np.fft.rfft(room), n))
    return np.stack(sides, 1)


def loudness(path):
    log = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', log)[-1]), float(re.findall(r'Peak:\s+(-?[\d.]+) dBFS', log)[-1])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, seed, tonic, night in (('day', 9, 87.31, False), ('night', 27, 73.42, True)):
        x = render(seed, tonic, night)
        x *= 0.5 / np.abs(x).max()
        raw = OUT / f'.{name}.wav'
        with wave.open(str(raw), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x * 32767).astype('<i2').tobytes())
        lufs, peak = loudness(raw)
        gain = min(-21 - lufs, -2 - peak)                     # background level, and never clipping
        out = OUT / f'{name}.mp3'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af', f'volume={gain:.2f}dB',
                        '-ar', '44100', '-b:a', '112k', str(out)], check=True)
        raw.unlink()
        lufs, peak = loudness(out)
        print(f'{out.name}: {LENGTH} s, {out.stat().st_size // 1024} KB, {lufs:.1f} LUFS, peak {peak:.1f} dBFS')


if __name__ == '__main__':
    sys.exit(main())
