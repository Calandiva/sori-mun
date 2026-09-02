"""글리프 — 낱말 하나를 적고 되읽는다.

    [역할 화음] ([언어·받아적기 화음]) [자릿음 1~8] [종지 2음]

낱말의 가락이 먼저 나온다. 자릿음들이 지그재그 순열로 계단을 밟아
번호마다 전혀 다른 윤곽을 그리고, 마지막 두 음의 **종지**가 성질(3도)과
등급(도약의 거칢)으로 그 낱말의 성격을 요약하며 맺는다.

글리프의 끝은 다음 화음이 말한다 — 홑음의 연속이 끊기는 곳이 곧
경계다. 한 낱말이 여러 글리프로 이어질 때만 사이에 이음 화음이 선다.

되읽을 수 있는 까닭
    1. 은행이 서로소라 화음 하나만 보아도 어느 자리인지 안다.
    2. 홑음의 연속에서 마지막 두 음이 종지, 앞이 자릿음이다 — 경계가
       화음으로 닫히므로 자리가 어긋날 길이 없다.
    3. 종지가 성질을 밝히므로 자릿음의 음계와 순열도 정해진다.
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
    CONCEPT = "개념"
    WORD = "낱말"
    LETTER = "글자"


# ── 되찾기표 ─────────────────────────────────────────────────────────
_ROLE_BY_V = {BANKS.role[ROLE_INDEX[r]].voicing: r for r in ROLE_ORDER}
_LANG_BY_V = {sh.voicing: lg for lg, sh in BANKS.language.items()}
_LETTER_BY_V = {sh.voicing: lg for lg, sh in BANKS.letter.items()}
_JOIN_V = BANKS.join.voicing
_TERM_BY_V = {BANKS.term[i].voicing: t for i, t in enumerate(C.TERMINATORS)}
_QUALITY_BY_SIG = {v: q for q, v in C.QUALITY_SIG.items()}
_TIER_BY_LEAP = {v: t for t, v in enumerate(C.TIER_LEAP)}
# 지그재그 순열의 역 — (성질, 음계어긋남) → 자릿값
_DIGIT_BY_OFFSET = {
    q: {C.SCALE[q][C.DIGIT_ORDER[q][d]]: d
        for d in range(len(C.SCALE[q]))}
    for q in Quality
}


def voicing_of(pitches) -> Voicing:
    ps = sorted(pitches)
    return tuple(p - ps[0] for p in ps)


def root_of(pitches) -> int:
    return min(pitches)


@dataclass(frozen=True, slots=True)
class Event:
    pitches: Chord
    duration: int
    velocity: int
    slot: str          # 역할/언어/받아적기/이름/종지/이음/종결
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
    polarity: int = 0,
    flag: int = 0,
) -> Glyph:
    if kind is not Kind.CONCEPT and lang is None:
        raise ValueError(f"{kind.value} 글리프에는 언어가 있어야 한다")
    if kind is Kind.LETTER:
        tier, quality = C.LETTER_TIER, C.LETTER_QUALITY

    accent = C.POLARITY_ACCENT * abs(polarity)
    ev: list[Event] = []

    def chord(shape, root, dur, vel, slot, exact=False):
        r = root if exact else min(root, pitch.HIGHEST - shape.span)
        ps = shape.at(r)
        pitch.assert_in_range(ps)
        ev.append(Event(ps, C.scaled(dur, role), min(127, vel), slot))

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

    # 3. 자릿음 — 낱말 고유의 가락이 먼저 나온다.
    base = C.base_of(quality)
    digits = C.digits_of(index, base)
    if len(digits) > C.MELODY_MAX_DIGITS:
        raise ValueError(f"번호 {index:,} 는 자릿음 {C.MELODY_MAX_DIGITS}개를 넘는다")
    scale, order = C.SCALE[quality], C.DIGIT_ORDER[quality]
    for i, d in enumerate(digits):
        dur = C.DUR_DIGIT if i % 2 == 0 else C.DUR_DIGIT_OFF
        single(C.MEL_BASE + scale[order[d]], dur,
               C.VEL_DIGIT + accent, "이름")

    # 4. 종지 — 성질과 등급으로 맺는다.
    sig1 = C.MEL_BASE + C.QUALITY_SIG[quality]
    single(sig1, C.DUR_SIG, C.VEL_SIG + accent, "종지")
    single(sig1 + C.TIER_LEAP[tier], C.DUR_SIG_END,
           C.VEL_SIG + accent, "종지")

    return Glyph(role, kind, lang, tier, quality, index, tuple(ev), flag)


def join_event(role: Role) -> Event:
    """한 낱말 안에서 글리프를 잇는 작은 다리."""
    sh = BANKS.join
    ps = sh.at(min(C.HEAD_PITCH, pitch.HIGHEST - sh.span))
    return Event(ps, C.scaled(C.DUR_JOIN, role), C.VEL_JOIN, "이음")


def terminator(mark: str) -> Event:
    if mark not in C.TERMINATORS:
        mark = "."
    sh = BANKS.term[C.TERMINATORS.index(mark)]
    ps = sh.at(min(C.HEAD_PITCH, pitch.HIGHEST - sh.span))
    pitch.assert_in_range(ps)
    return Event(ps, C.DUR_TERM, C.VEL_TERM, "종결", C.REST_SENTENCE)


# ── 되읽기 ───────────────────────────────────────────────────────────
def read_terminator(chord: Chord) -> str | None:
    if len(chord) == 1:
        return None
    return _TERM_BY_V.get(voicing_of(chord))


def is_join(chord: Chord) -> bool:
    return len(chord) > 1 and voicing_of(chord) == _JOIN_V


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

    # 홑음의 연속 — 다음 화음(또는 끝)까지가 이 글리프의 멜로디다.
    j = i
    while j < n and len(chords[j]) == 1:
        j += 1
    melody = [chords[k][0] for k in range(i, j)]
    if len(melody) < C.MELODY_MIN:
        raise DecodeError(f"멜로디가 {len(melody)}음뿐이다 — 자릿음 하나와 종지 둘은 있어야 한다")

    # 마지막 두 음이 종지: 성질과 등급
    quality = _QUALITY_BY_SIG.get(melody[-2] - C.MEL_BASE)
    if quality is None:
        raise DecodeError(f"종지 첫 음 {melody[-2]} 이 성질이 아니다")
    tier = _TIER_BY_LEAP.get(melody[-1] - melody[-2])
    if tier is None:
        raise DecodeError(f"종지 도약 {melody[-1] - melody[-2]} 이 등급이 아니다")

    table = _DIGIT_BY_OFFSET[quality]
    base = C.base_of(quality)
    digits: list[int] = []
    for p in melody[:-2]:
        d = table.get(p - C.MEL_BASE)
        if d is None:
            raise DecodeError(f"홑음 {p} 은 {quality.value} 음계에 없다")
        digits.append(d)

    if kind is Kind.LETTER and (quality, tier) != (C.LETTER_QUALITY, C.LETTER_TIER):
        raise DecodeError("받아적기의 종지가 어긋난다")

    return (
        Glyph(role, kind, lang, tier, quality,
              C.index_of(digits, base), (), flag),
        j,
    )
