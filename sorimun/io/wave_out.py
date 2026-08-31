"""소리로 만들어 .wav 로 쓴다. 표준 라이브러리만 쓴다.

이 소리는 들으라고도 있지만 **되읽으라고도** 있다. 내려받은 음원을
다시 넣으면 글로 정확히 돌아와야 한다. 그래서 이렇게 빚는다.

    화음 사이 짧은 무음   되읽기가 화음을 무음으로 가른다
    최소 길이 보장       아주 짧은 화음도 셈할 수 있게
    절제된 배음          배음이 이웃 음으로 오해되지 않게

길이는 부호가 아니므로 이렇게 바꾸어도 뜻은 그대로다.
"""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path

from ..compose import Piece

SAMPLE_RATE = 44100
# 배음 세기. 2배음을 절제해 옥타브 화음(0,12)과 헷갈리지 않게 한다.
PARTIALS = ((1, 1.00), (2, 0.28), (3, 0.14), (4, 0.06))
ATTACK = 0.012
RELEASE = 0.06       # 여운이 무음 골을 메우지 않게 짧게
GAP = 0.13           # 화음 사이 무음 — 되읽기의 경계
MIN_DUR = 0.30       # 화음 하나의 최소 길이


def _freq(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def schedule(piece: Piece, tempo: int | None = None):
    """(시작초, 길이초, 음들, 세기) 목록. 화음 사이에 무음을 벌려 둔다."""
    tempo = tempo or piece.tempo
    unit = 60.0 / tempo / 4
    out = []
    t = 0.0
    for n in sorted(piece.notes, key=lambda x: x.start):
        dur = max(MIN_DUR, n.duration * unit)
        out.append((t, dur, n.pitches, n.velocity))
        t += dur + GAP
    return out


def render(piece: Piece, tempo: int | None = None) -> array.array:
    sched = schedule(piece, tempo)
    total = int((sched[-1][0] + sched[-1][1] + RELEASE + 0.3) * SAMPLE_RATE) + 1
    buf = array.array("d", bytes(8 * total))

    for start, hold, pitches, vel in sched:
        t0 = int(start * SAMPLE_RATE)
        count = int((hold + RELEASE) * SAMPLE_RATE)
        amp = (vel / 127.0) ** 1.6 * 0.22 / max(1, len(pitches))
        for p in pitches:
            w = 2 * math.pi * _freq(p) / SAMPLE_RATE
            for i in range(count):
                t = i / SAMPLE_RATE
                if t < ATTACK:
                    env = t / ATTACK
                elif t < hold:
                    env = 1.0 - 0.25 * (t - ATTACK) / max(1e-6, hold - ATTACK)
                else:
                    env = 0.75 * math.exp(-(t - hold) * 60.0)
                    if env <= 0.0005:
                        break    # 여운이 다한 뒤에만 끊는다
                v = 0.0
                for k, g in PARTIALS:
                    v += g * math.sin(w * k * i)
                j = t0 + i
                if 0 <= j < total:
                    buf[j] += amp * env * v
    return buf


def write(piece: Piece, path: Path | str, tempo: int | None = None) -> Path:
    path = Path(path)
    buf = render(piece, tempo)
    peak = max((abs(x) for x in buf), default=0.0)
    gain = (0.89 / peak) if peak > 0 else 1.0
    pcm = array.array("h", (int(max(-1.0, min(1.0, x * gain)) * 32767) for x in buf))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return path
