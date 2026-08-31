"""글리프 — 낱말 하나를 적고 되읽는다.

    [역할 화음] ([언어·받아적기 화음]) [이름 멜로디 2~10음] [맺음 화음]

두 층이 갈린다. 저음의 **화음**은 구조를 묘사하고(문장 성분·갈래·경계),
고음의 **홑음 멜로디**는 낱말 그 자체다. 모든 은행 화음이 2~3음이므로
홑음은 언제나 멜로디다 — 화음이면 구조, 홑음이면 이름.

이름 멜로디가 익숙함과 감정을 직접 나른다.

    서명1  성질   기준음 위 장3도=장, 단3도=단, 삼전음=중성
    서명2  등급   서명1에서 뛰는 음정의 거칢 6단계 (완전4도…단2도)
    자릿음 번호   그 성질의 음계 위 계단이 전단사 진법의 한 자리

되읽을 수 있는 까닭
    1. 은행이 서로소라 화음 하나만 보아도 어느 자리인지 안다.
    2. 홑음은 언제나 멜로디이고, 자리(서명1→서명2→자릿음)는 차례가
       정한다. 서명이 성질과 등급을 밝히므로 자릿음의 음계도 정해진다.
    3. 맺음 화음이 글리프의 끝을 말한다. 길이를 재지 않아도 끊긴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import codes as C
from . import pitch
from .banks import BANKS
from .harmony import Quality
from .roles import INDEX as ROLE_INDEX
from .roles import ORDER as ROLE_ORDER
from .roles import Role

Voicing = tuple[int, ...]
Chord = tuple[int, ...]


class Kind(str, Enum):
    CONCEPT = "개념"   # 언어에 매이지 않는다 — 표시 화음 없음
    WORD = "낱말"      # 그 언어에만 있다 — 언어 화음이 앞선다
    LETTER = "글자"    # 받아 적는다 — 받아적기 화음이 앞선다


# ── 되찾기표 ─────────────────────────────────────────────────────────
_ROLE_BY_V = {BANKS.role[ROLE_INDEX[r]].voicing: r for r in ROLE_ORDER}
_LANG_BY_V = {sh.voicing: lg for lg, sh in BANKS.language.items()}
_LETTER_BY_V = {sh.voicing: lg for lg, sh in BANKS.letter.items()}
_CLOSE_BY_V = {BANKS.close[i].voicing: i for i in (0, 1)}
_TERM_BY_V = {BANKS.term[i].voicing: t for i, t in enumerate(C.TERMINATORS)}
_QUALITY_BY_SIG = {v: q for q, v in C.QUALITY_SIG.items()}
_TIER_BY_LEAP = {v: t for t, v in enumerate(C.TIER_LEAP)}
_DEGREE_BY_OFFSET = {
    q: {off: i for i, off in enumerate(scale)} for q, scale in C.SCALE.items()
}


def voicing_of(pitches) -> Voicing:
    ps = sorted(pitches)
    return tuple(p - ps[0] for p in ps)


def root_of(pitches) -> int:
    return min(pitches)


@dataclass(frozen=True, slots=True)
class Event:
    """울리는 소리 하나. 길이와 세기는 표현일 뿐 뜻을 담지 않는다."""

    pitches: Chord
    duration: int
    velocity: int
    slot: str          # 역할/언어/받아적기/서명/이름/맺음/종결
    rest_after: int = 0


@dataclass(frozen=True, slots=True)
class Glyph:
    role: Role
    kind: Kind
    lang: str | None       # 개념이면 None
    tier: int
    quality: Quality
    index: int
    close: int
    events: tuple[Event, ...]
    flag: int = 0

    @property
    def chords(self) -> list[Chord]:
        return [e.pitches for e in self.events]

    @property
    def melody(self) -> list[int]:
        return [e.pitches[0] for e in self.events if len(e.pitches) == 1]

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
    close: int = C.CLOSE_BREAK,
    polarity: int = 0,
    flag: int = 0,
) -> Glyph:
    if kind is not Kind.CONCEPT and lang is None:
        raise ValueError(f"{kind.value} 글리프에는 언어가 있어야 한다")
    if kind is Kind.LETTER:
        tier, quality = C.LETTER_TIER, C.LETTER_QUALITY

    accent = C.POLARITY_ACCENT * abs(polarity)
    ev: list[Event] = []

    def chord(shape, root, dur, vel, slot, rest=0, exact=False):
        r = root if exact else min(root, pitch.HIGHEST - shape.span)
        ps = shape.at(r)
        pitch.assert_in_range(ps)
        ev.append(Event(ps, C.scaled(dur, role), min(127, vel), slot, rest))

    def single(p, dur, vel, slot):
        pitch.assert_in_range((p,))
        ev.append(Event((p,), C.scaled(dur, role), min(127, vel), slot))

    # 1. 역할 — 구조의 저음. 근음 어긋남 한 칸이 대문자 표시다.
    chord(BANKS.role[ROLE_INDEX[role]],
          C.ROLE_PITCH[role] + C.FLAG_OFFSETS[flag],
          C.DUR_ROLE, C.VEL_ROLE + accent, "역할", exact=True)

    # 2. 갈래 화음 (개념이면 없다)
    if kind is Kind.WORD:
        chord(BANKS.language[lang], C.HEAD_PITCH, C.DUR_HEAD,
              C.VEL_HEAD, "언어")
    elif kind is Kind.LETTER:
        chord(BANKS.letter[lang], C.HEAD_PITCH, C.DUR_HEAD,
              C.VEL_HEAD, "받아적기")

    # 3. 이름 멜로디
    sig1 = C.MEL_BASE + C.QUALITY_SIG[quality]
    single(sig1, C.DUR_SIG, C.VEL_SIG + accent, "서명")
    single(sig1 + C.TIER_LEAP[tier], C.DUR_SIG, C.VEL_SIG + accent, "서명")

    base = C.base_of(quality)
    digits = C.digits_of(index, base)
    if len(digits) > C.MELODY_MAX_DIGITS:
        raise ValueError(f"번호 {index:,} 는 멜로디 {C.MELODY_MAX_DIGITS}자리를 넘는다")
    scale = C.SCALE[quality]
    for d in digits:
        single(C.MEL_BASE + scale[d], C.DUR_DIGIT, C.VEL_DIGIT + accent, "이름")

    # 4. 맺음
    chord(BANKS.close[close], C.HEAD_PITCH, C.DUR_CLOSE, C.VEL_CLOSE,
          "맺음", C.REST_AFTER_CLOSE[close])

    return Glyph(role, kind, lang, tier, quality, index, close,
                 tuple(ev), flag)


def terminator(mark: str) -> Event:
    if mark not in C.TERMINATORS:
        mark = "."
    sh = BANKS.term[C.TERMINATORS.index(mark)]
    ps = sh.at(min(C.HEAD_PITCH, pitch.HIGHEST - sh.span))
    pitch.assert_in_range(ps)
    return Event(ps, C.DUR_TERM, C.VEL_TERM, "종결", C.REST_SENTENCE)


# ── 되읽기 — 화음의 차례만 본다 ──────────────────────────────────────
def read_terminator(chord: Chord) -> str | None:
    if len(chord) == 1:
        return None
    return _TERM_BY_V.get(voicing_of(chord))


def decode(chords: list[Chord], start: int = 0) -> tuple[Glyph, int]:
    n = len(chords)
    if start >= n:
        raise DecodeError("읽을 것이 없다")

    if len(chords[start]) == 1:
        raise DecodeError(f"{start}번째는 홑음이다 — 글리프는 역할 화음으로 시작한다")
    role = _ROLE_BY_V.get(voicing_of(chords[start]))
    if role is None:
        raise DecodeError(f"{start}번째 화음 {chords[start]} 는 역할 화음이 아니다")
    off = root_of(chords[start]) - C.ROLE_PITCH[role]
    if off not in C.FLAG_OFFSETS:
        raise DecodeError(f"역할 화음의 근음 어긋남 {off} 이 옳지 않다")
    flag = C.FLAG_OFFSETS.index(off)
    i = start + 1

    kind = Kind.CONCEPT
    lang: str | None = None
    if i < n and len(chords[i]) > 1:
        v = voicing_of(chords[i])
        if v in _LANG_BY_V:
            kind, lang = Kind.WORD, _LANG_BY_V[v]
            i += 1
        elif v in _LETTER_BY_V:
            kind, lang = Kind.LETTER, _LETTER_BY_V[v]
            i += 1
        else:
            raise DecodeError(f"{i}번째 화음 {chords[i]} 는 갈래 화음이 아니다")

    # 서명 두 음
    if i + 1 >= n or len(chords[i]) != 1 or len(chords[i + 1]) != 1:
        raise DecodeError(f"{i}번째부터 서명 홑음 두 개가 와야 한다")
    q_off = chords[i][0] - C.MEL_BASE
    quality = _QUALITY_BY_SIG.get(q_off)
    if quality is None:
        raise DecodeError(f"서명1 어긋남 {q_off} 은 성질이 아니다")
    leap = chords[i + 1][0] - chords[i][0]
    tier = _TIER_BY_LEAP.get(leap)
    if tier is None:
        raise DecodeError(f"서명2 도약 {leap} 은 등급이 아니다")
    i += 2

    # 자릿음들
    base = C.base_of(quality)
    table = _DEGREE_BY_OFFSET[quality]
    digits: list[int] = []
    close: int | None = None
    while i < n:
        if len(chords[i]) == 1:
            d = table.get(chords[i][0] - C.MEL_BASE)
            if d is None:
                raise DecodeError(
                    f"{i}번째 홑음 {chords[i][0]} 은 {quality.value} 음계에 없다")
            digits.append(d)
            i += 1
            continue
        cv = voicing_of(chords[i])
        if cv in _CLOSE_BY_V:
            close = _CLOSE_BY_V[cv]
            i += 1
            break
        raise DecodeError(f"{i}번째 화음 {chords[i]} 는 맺음 화음이 아니다")

    if close is None:
        raise DecodeError("맺음 화음이 없다")
    if not digits:
        raise DecodeError("이름 자릿음이 하나도 없다")
    if kind is Kind.LETTER:
        if (quality, tier) != (C.LETTER_QUALITY, C.LETTER_TIER):
            raise DecodeError("받아적기의 서명이 어긋난다")

    return (
        Glyph(role, kind, lang, tier, quality,
              C.index_of(digits, base), close, (), flag),
        i,
    )
