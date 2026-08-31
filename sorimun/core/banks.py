"""화음 은행 — 자리마다 쓰는 화음을 갈라 둔다.

부호를 나르는 것은 **음높이와 화성뿐**이다. 음가와 쉼표는 표현일 뿐
뜻을 담지 않는다. 사람이 연주하면 길이는 흔들리기 마련이므로, 흔들려도
뜻이 상하지 않아야 하기 때문이다.

    역할 은행    8개   문장 성분
    의미 은행   18개   (등급 × 성질). 언어 중립 — 개념의 성격
    언어 은행    2개   그 언어에만 있는 낱말이 따라온다는 표시
    받아적기     2개   사전에 없는 낱말을 글자로 적는다는 표시
    자릿 은행    성질마다 4개. 개념 번호를 적어 나가는 화음
    맺음 은행    2개   이어짐 / 끊김 — 쉼표 대신 경계를 말한다
    종결 은행    4개   . ? ! …

은행끼리 서로소이므로 화음 하나만 들어도 그것이 어느 자리인지 안다.
그래서 길이를 몰라도, 순서만 알면 풀린다.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import pitch
from .harmony import N_TIERS, Quality, Shape, enumerate_shapes

# 자릿 화음만 근음이 부호를 나르므로 좁게 묶는다. 나머지는 모양만으로
# 가려지므로 근음을 아무 데나 놓아도 된다.
DIGIT_MAX_SPAN = 7
DIGIT_PER_QUALITY = 4
WIDE_MAX_SPAN = pitch.MAX_CHORD_SPAN
ROLE_MAX_SPAN = 10      # 근음이 음역대를 그릴 자리를 남긴다

LANGUAGES = ("ko", "en")


@dataclass(frozen=True, slots=True)
class Banks:
    role: tuple[Shape, ...]                                # 8
    meaning: dict[tuple[int, Quality], Shape]              # 18, 언어 중립
    language: dict[str, Shape]                             # 2
    letter: dict[str, Shape]                               # 2
    digit: dict[Quality, tuple[Shape, ...]]                # 성질마다 4개
    close: tuple[Shape, Shape]                             # 이어짐 / 끊김
    term: tuple[Shape, ...]                                # 4

    def all_shapes(self) -> list[Shape]:
        out = list(self.role) + list(self.close) + list(self.term)
        out += list(self.meaning.values())
        out += list(self.language.values()) + list(self.letter.values())
        for v in self.digit.values():
            out += list(v)
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

    # 1. 자릿 은행 — 제약이 가장 빡빡하다. 낱말의 성질 색을 이름을
    #    적는 내내 유지한다.
    digit = {
        q: tuple(_pick(pool, DIGIT_PER_QUALITY, quality=q,
                       max_span=DIGIT_MAX_SPAN))
        for q in Quality
    }

    # 2. 의미 은행 — (등급 × 성질). 언어를 담지 않는다. 소리가 뜻을
    #    담되 어느 말인지는 담지 않아야, 영어로 적은 것을 한국어로
    #    읽어 낼 수 있다.
    meaning = {
        (tier, q): _pick(pool, 1, quality=q, tier=tier,
                         max_span=WIDE_MAX_SPAN)[0]
        for tier in range(N_TIERS) for q in Quality
    }

    # 3. 그 언어에만 있는 낱말 / 글자 받아적기
    language = {lang: _pick(pool, 1, max_span=WIDE_MAX_SPAN)[0]
                for lang in LANGUAGES}
    letter = {lang: _pick(pool, 1, max_span=WIDE_MAX_SPAN)[0]
              for lang in LANGUAGES}

    # 4. 맺음 — 이어짐 / 끊김. 쉼표가 하던 일을 화음이 맡는다.
    close = tuple(_pick(pool, 2, max_span=WIDE_MAX_SPAN, spread=True))

    # 5. 종결과 역할
    term = tuple(_pick(pool, 4, max_span=WIDE_MAX_SPAN, spread=True))
    role = tuple(_pick(pool, 8, max_span=ROLE_MAX_SPAN, spread=True))

    banks = Banks(role=role, meaning=meaning, language=language,
                  letter=letter, digit=digit, close=close, term=term)
    v = [s.voicing for s in banks.all_shapes()]
    if len(set(v)) != len(v):
        raise RuntimeError("은행끼리 모양이 겹친다")
    return banks


BANKS = build()
