"""소리에서 화음의 차례를 읽는다 — 오디오를 다시 넣는 길.

우리 소리는 화음 사이에 짧은 무음을 벌려 두었다(wave_out). 그래서

    1. 소리의 크기로 화음 구간을 가른다
    2. 구간마다 25개 후보 음(C3~C5)의 힘을 골츠엘로 잰다
    3. 힘이 큰 것부터 고르되, 이미 고른 음의 배음으로 설명되는 것은
       거른다 (2배음 세기를 절제해 두어 문턱이 뚜렷하다)

길이는 재지만 쓰지 않는다. 부호는 음높이와 화성뿐이기 때문이다.
"""

from __future__ import annotations

import math
import wave
from pathlib import Path

from ..core import pitch

# wave_out 의 배음 구성과 맞물린다
PARTIAL_GAIN = {2: 0.28, 3: 0.14, 4: 0.06}
SILENCE_RATIO = 0.045     # 최고 RMS 대비 이 아래면 무음
MIN_SEG = 0.12            # 이보다 짧은 구간은 소음으로 버린다
MIN_GAP = 0.08            # 이보다 짧은 골은 간섭 딥 — 이웃과 합친다
                          # (진짜 경계 골은 GAP=0.13s 이상이다)
NOTE_FLOOR = 0.20         # 구간 최강음 대비 이 아래면 음이 아니다
HARMONIC_MARGIN = 2.2     # 배음 예측치의 몇 배를 넘어야 진짜 음인가


def _freq(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def load_wav(path: Path | str) -> tuple[list[float], int]:
    """모노 실수 표본과 표본율."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        width = w.getsampwidth()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError(f"16비트 PCM 만 읽는다 (이 파일은 {width*8}비트)")
    total = len(raw) // 2
    out = []
    step = ch
    for i in range(0, total, step):
        v = int.from_bytes(raw[2 * i:2 * i + 2], "little", signed=True)
        out.append(v / 32768.0)
    return out, sr


def _segments(samples: list[float], sr: int) -> list[tuple[int, int]]:
    """무음으로 가른 (시작, 끝) 표본 구간."""
    win = max(1, sr // 200)          # 5ms 창
    n = len(samples) // win
    rms = []
    for i in range(n):
        s = samples[i * win:(i + 1) * win]
        rms.append(math.sqrt(sum(x * x for x in s) / len(s)))
    peak = max(rms, default=0.0)
    if peak <= 0:
        return []
    thr = peak * SILENCE_RATIO

    segs = []
    start = None
    for i, v in enumerate(rms):
        if v >= thr and start is None:
            start = i
        elif v < thr and start is not None:
            segs.append((start * win, i * win))
            start = None
    if start is not None:
        segs.append((start * win, n * win))

    # 간섭으로 생긴 짧은 골은 이어붙인다 — 여러 음이 함께 울리면 위상
    # 상쇄로 순간 진폭이 문턱 아래로 꺼질 수 있다.
    merged: list[tuple[int, int]] = []
    for a, b in segs:
        if merged and (a - merged[-1][1]) / sr < MIN_GAP:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return [(a, b) for a, b in merged if (b - a) / sr >= MIN_SEG]


def _goertzel(samples: list[float], sr: int, freq: float) -> float:
    """한 주파수의 힘. 한 창으로 잰다."""
    n = len(samples)
    k = 2.0 * math.cos(2 * math.pi * freq / sr)
    s0 = s1 = 0.0
    for i, x in enumerate(samples):
        # 한 겹 해닝 창 — 이웃 반음의 새어듦을 줄인다
        w = 0.5 - 0.5 * math.cos(2 * math.pi * i / n)
        s0, s1 = x * w + k * s0 - s1, s0
    return (s1 * s1 + s0 * s0 - k * s0 * s1) / n


def _pitches_of(samples: list[float], sr: int) -> tuple[int, ...]:
    """구간 하나에서 2~3개 음을 뽑는다."""
    # 구간 가운데를 쓴다 — 들머리와 여운을 피한다
    n = len(samples)
    a, b = int(n * 0.15), int(n * 0.85)
    body = samples[a:b]
    if len(body) < 256:
        body = samples

    power = {m: _goertzel(body, sr, _freq(m))
             for m in range(pitch.LOWEST, pitch.HIGHEST + 1)}
    strongest = max(power.values())
    if strongest <= 0:
        return ()

    chosen: list[int] = []
    for m in sorted(power, key=lambda x: x):          # 낮은 음부터
        p = power[m]
        if p < strongest * NOTE_FLOOR:
            continue
        # 이미 고른 음의 배음으로 설명되는가
        expected = 0.0
        for c in chosen:
            d = _freq(m) / _freq(c)
            k = round(d)
            if k in PARTIAL_GAIN and abs(d - k) < 0.03:
                expected += power[c] * PARTIAL_GAIN[k] ** 2
        if expected > 0 and p < expected * HARMONIC_MARGIN:
            continue
        chosen.append(m)
        if len(chosen) == 3:
            break
    return tuple(chosen)


def chords(path: Path | str) -> list[tuple[int, ...]]:
    """WAV 파일을 화음의 차례로. 되읽기에 그대로 넣을 수 있다."""
    samples, sr = load_wav(path)
    out = []
    for a, b in _segments(samples, sr):
        ps = _pitches_of(samples[a:b], sr)
        if ps:
            out.append(ps)
    return out
