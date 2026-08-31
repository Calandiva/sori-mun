"""화음 은행 — 자리마다 쓰는 화음을 갈라 둔다.

부호를 나르는 것은 **음높이와 화성뿐**이다. 음가와 쉼표는 표현일 뿐
뜻을 담지 않는다. 사람이 연주하면 길이는 흔들리기 마련이므로, 흔들려도
뜻이 상하지 않아야 하기 때문이다.

    역할 은행    8개   문장 성분
    언어 은행    2개   그 언어에만 있는 낱말이 따라온다는 표시
    받아적기     2개   사전에 없는 낱말을 글자로 적는다는 표시
    맺음 은행    2개   이어짐 / 끊김 — 쉼표 대신 경계를 말한다
    종결 은행    4개   . ? ! …

은행은 **구조의 층**이다 — 저음에 깔리는 화음. 낱말 그 자체(등급·성질·
번호)는 은행을 쓰지 않고 **홑음 멜로디**가 나른다. 모든 은행 화음이
2~3음이므로 홑음은 언제나 멜로디다. 화음이면 구조, 홑음이면 이름.
등급과 성질도 멜로디의 서명이 직접 노래하므로 의미 화음은 없다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import pitch
from .harmony import N_TIERS, Quality, Shape, enumerate_shapes

WIDE_MAX_SPAN = pitch.MAX_CHORD_SPAN
ROLE_MAX_SPAN = 10      # 근음이 음역대를 그릴 자리를 남긴다

LANGUAGES = ("ko", "en")


@dataclass(frozen=True, slots=True)
class Banks:
    role: tuple[Shape, ...]                                # 8
    language: dict[str, Shape]                             # 2
    letter: dict[str, Shape]                               # 2
    close: tuple[Shape, Shape]                             # 이어짐 / 끊김
    term: tuple[Shape, ...]                                # 4

    def all_shapes(self) -> list[Shape]:
        out = list(self.role) + list(self.close) + list(self.term)
        out += list(self.language.values()) + list(self.letter.values())
        return out


def _pick(pool: list[Shape], n: int, *, quality=None, tier=None,
          max_span: int, spread: bool = False) -> list[Shape]:
    cand = [
        s for s in pool
        if s.span <= max_span
        and (quality is None or s.quality is quality)
        and (tier is None or s.tier == tier)
    ]
    cand.sort(key=lambda s: (s.dissonance, s.voicing))
    if len(cand) < n:
        raise RuntimeError(
            f"모양이 모자라다: 성질={quality} 등급={tier} 폭≤{max_span} "
            f"— {n}개 필요, {len(cand)}개 있음")
    if spread and n > 1:
        taken, seen = [], set()
        for i in range(n):
            s = cand[round(i * (len(cand) - 1) / (n - 1))]
            while s.voicing in seen:
                s = cand[(cand.index(s) + 1) % len(cand)]
            seen.add(s.voicing)
            taken.append(s)
    else:
        taken = cand[:n]
    for s in taken:
        pool.remove(s)
    return taken


def build() -> Banks:
    pool = enumerate_shapes(pitch.MAX_CHORD_SPAN)

    # 1. 그 언어에만 있는 낱말 / 글자 받아적기
    language = {lang: _pick(pool, 1, max_span=WIDE_MAX_SPAN)[0]
                for lang in LANGUAGES}
    letter = {lang: _pick(pool, 1, max_span=WIDE_MAX_SPAN)[0]
              for lang in LANGUAGES}

    # 4. 맺음 — 이어짐 / 끊김. 쉼표가 하던 일을 화음이 맡는다.
    close = tuple(_pick(pool, 2, max_span=WIDE_MAX_SPAN, spread=True))

    # 5. 종결과 역할
    term = tuple(_pick(pool, 4, max_span=WIDE_MAX_SPAN, spread=True))
    role = tuple(_pick(pool, 8, max_span=ROLE_MAX_SPAN, spread=True))

    banks = Banks(role=role, language=language,
                  letter=letter, close=close, term=term)
    v = [s.voicing for s in banks.all_shapes()]
    if len(set(v)) != len(v):
        raise RuntimeError("은행끼리 모양이 겹친다")
    return banks


BANKS = build()
