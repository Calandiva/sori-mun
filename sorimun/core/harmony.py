"""화성 어휘.

두 개의 축이 직교한다.

  협화도 축 (tier 0~5)  ← 단어의 사용 빈도
      흔한 말일수록 협화롭고, 드문 말일수록 난해하다.

  성질 축 (major / minor / neutral) ← 단어의 감정 극성
      긍정어는 장(長) 관계, 부정어는 단(短) 관계, 중립어는 어느 쪽도 아닌
      빈 5도·4도쌓기·2도 계열.

화음은 '보이싱(voicing)' 으로 표현한다. 근음을 0 으로 둔 반음 오프셋
튜플이며, 요구사항대로 언제나 2음 또는 3음이다.
    (0, 7)      완전5도
    (0, 4, 7)   장3화음
    (0, 1, 6)   난해한 3음 집합
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations

from . import pitch


class Quality(str, Enum):
    """감정 극성이 결정하는 화음의 성질."""

    MAJOR = "major"      # 긍정: 장3도 관계
    MINOR = "minor"      # 부정: 단3도 관계
    NEUTRAL = "neutral"  # 중립: 3도가 없는 화음 (5도·4도·2도 계열)


# ── 불협화도 ─────────────────────────────────────────────────────────
# 음정류(interval class 0~6)별 거칠기. 0=동음/옥타브 … 6=삼전음
_IC_ROUGHNESS = {
    0: 0.05,  # 완전1도 / 옥타브
    1: 1.00,  # 단2도 / 장7도
    2: 0.62,  # 장2도 / 단7도
    3: 0.28,  # 단3도 / 장6도
    4: 0.24,  # 장3도 / 단6도
    5: 0.12,  # 완전4도 / 완전5도
    6: 0.78,  # 삼전음
}


def _interval_class(semitones: int) -> int:
    ic = abs(semitones) % 12
    return 12 - ic if ic > 6 else ic


def dissonance(voicing: tuple[int, ...]) -> float:
    """보이싱의 불협화도. 낮을수록 협화롭다.

    쌍별 음정의 거칠기 평균에, 좁은 간격은 더 거칠고 넓은 간격은
    덜 거칠다는 간격 보정을 곱한다.
    """
    pairs = list(combinations(voicing, 2))
    total = 0.0
    for a, b in pairs:
        d = abs(a - b)
        r = _IC_ROUGHNESS[_interval_class(d)]
        if d <= 2:
            r *= 1.15   # 좁게 붙은 음은 더 거칠게 들린다
        elif d > 12:
            r *= 0.75   # 옥타브 너머로 벌리면 거칢이 완화된다
        total += r
    return total / len(pairs)


# ── 성질 판별 ────────────────────────────────────────────────────────
# 3음: 어느 회전에서 '3도 쌓기'가 되는지로 판별한다.
_TERTIAN_MAJOR = {(4, 7), (4, 10), (4, 11)}   # 장3화음 / 属7·장7 생략형
_TERTIAN_MINOR = {(3, 7), (3, 10), (3, 11), (3, 6)}  # 단3화음 / 단7 / 감3화음


def quality(voicing: tuple[int, ...]) -> Quality:
    """보이싱의 성질을 판별한다. 전위(inversion)도 같은 성질로 본다."""
    pcs = sorted({v % 12 for v in voicing})

    if len(pcs) == 2:
        ic = _interval_class(pcs[1] - pcs[0])
        if ic == 4:
            return Quality.MAJOR   # 장3도 / 단6도
        if ic == 3:
            return Quality.MINOR   # 단3도 / 장6도
        return Quality.NEUTRAL

    if len(pcs) == 3:
        for i in range(3):
            root = pcs[i]
            x = (pcs[(i + 1) % 3] - root) % 12
            y = (pcs[(i + 2) % 3] - root) % 12
            if x > y:
                x, y = y, x
            if (x, y) in _TERTIAN_MAJOR:
                return Quality.MAJOR
            if (x, y) in _TERTIAN_MINOR:
                return Quality.MINOR

    return Quality.NEUTRAL


# ── 등급(tier) ───────────────────────────────────────────────────────
# 등급은 성질(major/minor/neutral)별 분위수로 매긴다.
#
# 절대 불협화도로 자르면 "긍정 + 최빈어" 칸이 영원히 빈다. 장3화음은
# 구조적으로 완전5도만큼 협화로울 수 없기 때문이다. 그래서 각 성질
# 안에서 상대적으로 나눈다. tier 0 장조 = 가장 순한 장화음,
# tier 5 장조 = 가장 뒤틀린 장화음. 듣는 쪽에서는
# "긍정적이지만 낯설다" 가 제대로 들린다.
N_TIERS = 6


@dataclass(frozen=True, slots=True)
class Shape:
    """구체적인 화음 모양 하나."""

    voicing: tuple[int, ...]
    quality: Quality
    dissonance: float
    tier: int

    @property
    def span(self) -> int:
        return self.voicing[-1]

    @property
    def size(self) -> int:
        return len(self.voicing)

    def at(self, root: int) -> tuple[int, ...]:
        """근음을 주면 실제 MIDI 음높이 튜플을 낸다."""
        return tuple(root + v for v in self.voicing)


def _raw_shapes(max_span: int) -> list[tuple[tuple[int, ...], Quality, float]]:
    out = []
    for b in range(1, max_span + 1):
        v = (0, b)
        out.append((v, quality(v), dissonance(v)))
    for a, b in combinations(range(1, max_span + 1), 2):
        v = (0, a, b)
        if len({x % 12 for x in v}) < 2:
            continue  # 같은 음만 겹치는 보이싱은 화음이 아니다
        out.append((v, quality(v), dissonance(v)))
    return out


def enumerate_shapes(max_span: int = pitch.MAX_CHORD_SPAN) -> list[Shape]:
    """2음·3음 보이싱을 남김없이 만들고 성질과 등급을 매긴다."""
    raw = _raw_shapes(max_span)
    by_q: dict[Quality, list] = {}
    for v, q, d in raw:
        by_q.setdefault(q, []).append((v, d))

    shapes: list[Shape] = []
    for q, items in by_q.items():
        items.sort(key=lambda it: (it[1], it[0]))  # 불협화도 오름차순, 결정적
        n = len(items)
        for i, (v, d) in enumerate(items):
            tier = min(N_TIERS - 1, i * N_TIERS // n)
            shapes.append(Shape(voicing=v, quality=q, dissonance=d, tier=tier))
    shapes.sort(key=lambda s: (s.tier, s.quality.value, s.dissonance, s.voicing))
    return shapes


def shape_table() -> dict[tuple[int, Quality], list[Shape]]:
    """(등급, 성질) 칸마다 쓸 수 있는 모양들. 불협화도 순으로 정렬."""
    table: dict[tuple[int, Quality], list[Shape]] = {}
    for s in enumerate_shapes():
        table.setdefault((s.tier, s.quality), []).append(s)
    for v in table.values():
        v.sort(key=lambda s: (s.dissonance, s.voicing))
    return table
