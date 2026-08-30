"""소리로 만들어 .wav 로 쓴다. 표준 라이브러리만 쓴다.

신시사이저가 없어도 결과를 바로 들어볼 수 있게 하려는 것이다.
배음을 몇 개 얹은 단순한 가산합성에 부드러운 포락선을 씌운다.
"""

from __future__ import annotations

import array
import math
import wave
from pathlib import Path

from ..compose import Score

SAMPLE_RATE = 44100
# 배음 세기. 종 비슷한, 조금 차가운 음색.
PARTIALS = ((1, 1.00), (2, 0.42), (3, 0.20), (4, 0.11), (6, 0.05))
ATTACK = 0.012
RELEASE = 0.28


def _freq(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _unit_seconds(tempo: int) -> float:
    """16분음표 하나의 길이(초)."""
    return 60.0 / tempo / 4


def render(score: Score, tempo: int | None = None) -> array.array:
    tempo = tempo or score.tempo
    us = _unit_seconds(tempo)
    total = int((score.length * us + RELEASE + 0.4) * SAMPLE_RATE) + 1
    buf = array.array("d", bytes(8 * total))

    for n in score.notes:
        t0 = int(n.start * us * SAMPLE_RATE)
        hold = n.duration * us
        dur = hold + RELEASE
        count = int(dur * SAMPLE_RATE)
        amp = (n.velocity / 127.0) ** 1.6 * 0.22 / max(1, len(n.pitches))

        for p in n.pitches:
            w = 2 * math.pi * _freq(p) / SAMPLE_RATE
            for i in range(count):
                t = i / SAMPLE_RATE
                if t < ATTACK:
                    env = t / ATTACK
                elif t < hold:
                    env = 1.0 - 0.35 * (t - ATTACK) / max(1e-6, hold - ATTACK)
                else:
                    env = 0.65 * math.exp(-(t - hold) * 4.2)
                if env <= 0.0005:
                    break
                s = 0.0
                for k, g in PARTIALS:
                    s += g * math.sin(w * k * i)
                j = t0 + i
                if 0 <= j < total:
                    buf[j] += amp * env * s

    return buf


def write(score: Score, path: Path | str, tempo: int | None = None) -> Path:
    """악보를 16비트 모노 .wav 로 쓴다."""
    path = Path(path)
    buf = render(score, tempo)

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
