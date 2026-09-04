"""글리프 — 낱말 하나를 적고 되읽는다.

멜로디만 들으면 낱말이고, 함께 울리는 화성을 들으면 역할이다.

    [첫 자릿음+화성] [자릿음 …] [종지1(+표지 내성)] [종지2]

낱말을 여는 화음이 따로 없다 — 낱말의 첫 자릿음이 곧 첫 소리이고,
베이스 C3 과 역할 내성은 그 아래에 깔릴 뿐이다. 그래서 낱말마다 다른
음으로 문을 연다. 화성의 규칙은 셋뿐이다 — 베이스는 언제나 C3 페달,
역할 내성은 베이스 위 몇 반음(흔한 역할일수록 협화), 표지 내성은
종지1 아래 49~56 창의 절대음(갈래·대문자·이음).

되읽을 수 있는 까닭
    1. 베이스 C3 이 울리면 새 낱말이다 — 다른 어떤 소리도 48 을 품지
       않는다. 홑음의 연속은 언제나 한 글리프의 몸통이다.
    2. 마지막 두 멜로디 음이 종지 — 종지1 의 절대음이 (성질, 으뜸음) 을
       유일하게 밝히고(여덟 닻이 서로소), 하행 도약이 등급이다.
    3. 으뜸음은 낱말의 정체에서 다시 계산해 대조한다 — 조가 어긋난
       소리는 거부된다.
    4. 멜로디 없는 저음 이중음은 문장의 끝이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import codes as C
from . import pitch
from .harmony import Quality
from .roles import Role

Chord = tuple[int, ...]

_QUALITIES = list(Quality)


class Kind(str, Enum):
    CONCEPT = "개념"
    WORD = "낱말"
    LETTER = "글자"


_ROLE_BY_INNER = {v: r for r, v in C.ROLE_INNER.items()}
_QUALITY_BY_SIG = {v: q for q, v in C.QUALITY_SIG.items()}
_TIER_BY_LEAP = {v: t for t, v in enumerate(C.TIER_LEAP)}
_KIND_BY_MARK = {v: k for k, v in C.KIND_MARK.items()}
_TERM_BY_SET = {frozenset(v): k for k, v in C.TERM_SET.items()}
_DIGIT_BY_OFFSET = {
    q: {C.SCALE[q][C.DIGIT_ORDER[q][d]]: d
        for d in range(len(C.SCALE[q]))}
    for q in Quality
}


@dataclass(frozen=True, slots=True)
class Event:
    pitches: Chord     # 정렬됨. 꼭대기가 멜로디다 (종결만 예외).
    duration: int
    velocity: int
    slot: str          # 으뜸/이름/종지/종결
    rest_after: int = 0


@dataclass(frozen=True, slots=True)
class Glyph:
    role: Role
    kind: Kind
    lang: str | None
    tier: int
    quality: Quality
    index: int
    events: tuple[Event, ...]
    flag: int = 0
    join: bool = False      # 같은 낱말이 다음 글리프로 이어지는가

    @property
    def chords(self) -> list[Chord]:
        return [e.pitches for e in self.events]

    @property
    def melody(self) -> list[int]:
        return [e.pitches[-1] for e in self.events]

    @property
    def n_digits(self) -> int:
        return len(C.digits_of(self.index, C.base_of(self.quality)))


class DecodeError(ValueError):
    pass


# ── 적기 ─────────────────────────────────────────────────────────────
def encode(
    role: Role,
    kind: Kind,
    tier: int,
    quality: Quality,
    index: int,
    *,
    lang: str | None = None,
    polarity: int = 0,
    flag: int = 0,
    join: bool = False,
) -> Glyph:
    if kind is not Kind.CONCEPT and lang is None:
        raise ValueError(f"{kind.value} 글리프에는 언어가 있어야 한다")
    if kind is Kind.LETTER:
        tier, quality = C.LETTER_TIER, C.LETTER_QUALITY

    accent = C.POLARITY_ACCENT * abs(polarity)
    tonic = C.tonic_of(quality, tier, index)
    ev: list[Event] = []

    def put(pitches, dur, vel, slot):
        ps = tuple(sorted(pitches))
        pitch.assert_in_range(ps)
        ev.append(Event(ps, C.scaled(dur, role), min(127, vel), slot))

    # 1~2. 자릿음 — 지그재그 계단, 자릿값이 리듬을 만든다. 첫 자릿음이
    #      낱말의 첫 소리이고, 베이스와 역할 내성이 그 아래에 깔린다.
    base = C.base_of(quality)
    digits = C.digits_of(index, base)
    if len(digits) > C.MELODY_MAX_DIGITS:
        raise ValueError(f"번호 {index:,} 는 자릿음 {C.MELODY_MAX_DIGITS}개를 넘는다")
    scale, order = C.SCALE[quality], C.DIGIT_ORDER[quality]
    for j, d in enumerate(digits):
        mel = tonic + scale[order[d]]
        if j == 0:
            put((C.PEDAL, C.PEDAL + C.ROLE_INNER[role], mel),
                C.DUR_TONIC + d % 3, C.VEL_SIG + accent, "머리")
        else:
            put((mel,), C.DUR_DIGIT + d % 3,
                C.VEL_DIGIT + accent, "이름")

    # 3. 종지1 — 3도 위. 표지 내성(갈래·대문자·이음)이 이 아래 선다.
    sig1 = tonic + C.QUALITY_SIG[quality]
    marks = []
    if kind is not Kind.CONCEPT:
        marks.append(C.KIND_MARK[(kind.name, lang)])
    if flag:
        marks.append(C.FLAG_MARK)
    if join:
        marks.append(C.JOIN_MARK)
    put(tuple(marks) + (sig1,), C.DUR_SIG, C.VEL_SIG + accent, "종지")

    # 4. 종지2 — 아래로 해결. 도약의 거칢이 등급이다.
    put((sig1 - C.TIER_LEAP[tier],), C.DUR_SIG_END,
        C.VEL_SIG + accent, "종지")

    return Glyph(role, kind, lang, tier, quality, index, tuple(ev),
                 flag, join)


def terminator(mark: str) -> Event:
    if mark not in C.TERM_SET:
        mark = "."
    ps = C.TERM_SET[mark]
    pitch.assert_in_range(ps)
    return Event(ps, C.DUR_TERM, C.VEL_TERM, "종결", C.REST_SENTENCE)


# ── 되읽기 ───────────────────────────────────────────────────────────
def read_terminator(chord: Chord) -> str | None:
    if len(chord) < 2 or max(chord) > 56:
        return None
    return _TERM_BY_SET.get(frozenset(chord))


def is_start(chord: Chord) -> bool:
    """베이스 C3 을 품으면 새 낱말의 머리다 — C3 은 머리에만 운다."""
    return (len(chord) >= 2 and min(chord) == C.PEDAL
            and max(chord) > 56)


def decode(chords: list[Chord], start: int = 0) -> tuple[Glyph, int]:
    n = len(chords)
    if start >= n:
        raise DecodeError("읽을 것이 없다")
    head = tuple(sorted(chords[start]))
    if not is_start(head):
        raise DecodeError(
            f"{start}번째 소리 {head} 는 낱말의 머리(베이스 C3)가 아니다")
    first_mel = head[-1]
    inners = [p - C.PEDAL for p in head[1:-1]]
    if len(inners) != 1 or inners[0] not in _ROLE_BY_INNER:
        raise DecodeError(f"역할 내성이 어긋난다: {head}")
    role = _ROLE_BY_INNER[inners[0]]

    # 몸통 — 다음 머리/종결/끝까지. 첫 자릿음(머리의 꼭대기)도 몸통이다.
    j = start + 1
    body: list[Chord] = [(first_mel,)]
    while j < n:
        c = tuple(sorted(chords[j]))
        if is_start(c) or read_terminator(c) is not None:
            break
        body.append(c)
        j += 1
    if len(body) < C.MELODY_MIN - 1:
        raise DecodeError(f"멜로디가 짧다 — 자릿음 하나와 종지 둘은 있어야 한다")

    # 종지: 마지막 둘. 종지1 에만 표지 내성이 붙을 수 있다.
    for k, c in enumerate(body):
        if len(c) > 1 and k != len(body) - 2:
            raise DecodeError(f"표지 내성은 종지1 에만 선다: {c}")
        if len(c) == 1 and not (48 <= c[0] <= 72):
            raise DecodeError(f"음역 밖: {c}")
    sig1_ev = body[-2]
    sig1, marks = sig1_ev[-1], sig1_ev[:-1]
    anchor = C.SIG_ANCHOR.get(sig1)
    if anchor is None:
        raise DecodeError(f"종지1 {sig1} 이 여덟 닻의 하나가 아니다")
    quality, tonic = anchor
    leap = sig1 - body[-1][0]
    tier = _TIER_BY_LEAP.get(leap)
    if tier is None:
        raise DecodeError(f"종지 하행 {leap} 이 등급이 아니다")

    kind, lang, flag, join = Kind.CONCEPT, None, 0, False
    for m in marks:
        if m in _KIND_BY_MARK:
            kname, lang = _KIND_BY_MARK[m]
            kind = Kind[kname]
        elif m == C.FLAG_MARK:
            flag = 1
        elif m == C.JOIN_MARK:
            join = True
        else:
            raise DecodeError(f"모르는 표지 내성 {m}")
    if kind is Kind.LETTER:
        tier = C.LETTER_TIER
        if quality is not C.LETTER_QUALITY:
            raise DecodeError("받아적기의 종지가 어긋난다")

    table = _DIGIT_BY_OFFSET[quality]
    base = C.base_of(quality)
    digits: list[int] = []
    for c in body[:-2]:
        d = table.get(c[0] - tonic)
        if d is None:
            raise DecodeError(f"홑음 {c[0]} 은 이 조의 {quality.value} 음계에 없다")
        digits.append(d)
    if not digits:
        raise DecodeError("자릿음이 없다")
    idx = C.index_of(digits, base)
    if C.tonic_of(quality, tier, idx) != tonic:
        raise DecodeError("으뜸음이 낱말의 정체와 맞지 않는다")

    return Glyph(role, kind, lang, tier, quality, idx, (), flag, join), j
