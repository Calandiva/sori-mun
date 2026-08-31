"""글리프 — 낱말 하나를 적고 되읽는다.

    [역할 화음] [머리 화음] [자릿 화음 × k] [맺음 화음]

되읽기는 **화음의 차례만** 본다. 음가도 쉼표도 보지 않는다. 그러므로
연주하는 사람이 길이를 마음대로 흔들어도 뜻은 그대로다.

세 갈래의 머리 화음
    의미 화음     (등급, 성질). 어느 말에도 매이지 않는 개념을 가리킨다.
                  영어로 적은 소리를 한국어로 읽어 낼 수 있는 까닭이다.
    언어 화음     그 언어에만 있는 낱말이 뒤따른다. 다음이 의미 화음이다.
    받아적기 화음 사전에 없는 낱말을 글자로 하나씩 적는다.

되읽을 수 있는 까닭
    1. 은행이 서로소라 화음 하나만 보아도 어느 자리인지 안다.
    2. 역할 화음이 먼저 오므로 음역대 바닥을 알게 되고, 그래야 자릿
       화음의 근음에서 자릿값을 뽑을 수 있다.
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
    CONCEPT = "개념"   # 언어에 매이지 않는다
    WORD = "낱말"      # 그 언어에만 있다
    LETTER = "글자"    # 받아 적는다


# ── 되찾기표 ─────────────────────────────────────────────────────────
_ROLE_BY_V = {BANKS.role[ROLE_INDEX[r]].voicing: r for r in ROLE_ORDER}
_MEANING_BY_V = {sh.voicing: cell for cell, sh in BANKS.meaning.items()}
_LANG_BY_V = {sh.voicing: lg for lg, sh in BANKS.language.items()}
_LETTER_BY_V = {sh.voicing: lg for lg, sh in BANKS.letter.items()}
_DIGIT_BY_V = {q: {sh.voicing: i for i, sh in enumerate(v)}
               for q, v in BANKS.digit.items()}
_CLOSE_BY_V = {BANKS.close[i].voicing: i for i in (0, 1)}
_TERM_BY_V = {BANKS.term[i].voicing: t for i, t in enumerate(C.TERMINATORS)}


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
    slot: str
    rest_after: int = 0


@dataclass(frozen=True, slots=True)
class Glyph:
    role: Role
    kind: Kind
    lang: str | None       # 개념이면 None
    tier: int
    quality: Quality
    index: int
    close: int             # 이어짐 / 끊김
    events: tuple[Event, ...]
    flag: int = 0          # 덤 한 자리 — 영어의 첫 글자 대문자 여부

    @property
    def chords(self) -> list[Chord]:
        return [e.pitches for e in self.events]

    @property
    def n_digits(self) -> int:
        return len(C.digits_of(self.index))


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

    accent = C.POLARITY_ACCENT * abs(polarity)
    ev: list[Event] = []

    def put(shape, root, dur, vel, slot, rest=0, exact=False):
        # 역할 화음의 근음은 부호(대문자 표시)를 담으므로 눌러 맞추지
        # 않는다. 나머지 머리·맺음 화음은 근음이 뜻을 담지 않으므로
        # 음역 안으로 눌러도 상관없다.
        ps = shape.at(root if exact else min(root, pitch.HIGHEST - shape.span))
        pitch.assert_in_range(ps)
        ev.append(Event(ps, C.scaled(dur, role), min(127, vel), slot, rest))

    # 1. 역할 — 모양이 자리를 말하고 근음이 음역대를 그린다
    put(BANKS.role[ROLE_INDEX[role]],
        C.ROLE_PITCH[role] + C.FLAG_OFFSETS[flag],
        C.DUR_ROLE, C.VEL_ROLE + accent, "역할", exact=True)

    # 2. 머리
    if kind is Kind.WORD:
        put(BANKS.language[lang], C.HEAD_PITCH, C.DUR_ROLE,
            C.VEL_HEAD + accent, "언어")
    if kind is Kind.LETTER:
        put(BANKS.letter[lang], C.HEAD_PITCH, C.DUR_HEAD,
            C.VEL_HEAD, "받아적기")
    else:
        put(BANKS.meaning[(tier, quality)], C.HEAD_PITCH, C.DUR_HEAD,
            C.VEL_HEAD + accent, "의미")

    # 3. 자릿 화음 — 낱말의 성질 색을 그대로 쓴다
    band = C.BAND[role]
    shapes = BANKS.digit[quality]
    for d in C.digits_of(index):
        off_i, sh_i = divmod(d, len(shapes))
        put(shapes[sh_i], band + C.DIGIT_OFFSETS[off_i],
            C.DUR_DIGIT, C.VEL_DIGIT + accent, "자리")

    # 4. 맺음 — 글리프의 끝, 그리고 어절이 이어지는지 끊기는지
    put(BANKS.close[close], C.HEAD_PITCH, C.DUR_CLOSE, C.VEL_CLOSE,
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
    return _TERM_BY_V.get(voicing_of(chord))


def decode(chords: list[Chord], start: int = 0) -> tuple[Glyph, int]:
    n = len(chords)
    if start >= n:
        raise DecodeError("읽을 것이 없다")

    role = _ROLE_BY_V.get(voicing_of(chords[start]))
    if role is None:
        raise DecodeError(f"{start}번째 화음 {chords[start]} 는 역할 화음이 아니다")
    off = root_of(chords[start]) - C.ROLE_PITCH[role]
    if off not in C.FLAG_OFFSETS:
        raise DecodeError(f"역할 화음의 근음 어긋남 {off} 이 옳지 않다")
    flag = C.FLAG_OFFSETS.index(off)
    i = start + 1
    if i >= n:
        raise DecodeError("머리 화음이 없다")

    kind = Kind.CONCEPT
    lang: str | None = None
    v = voicing_of(chords[i])

    if v in _LANG_BY_V:
        kind, lang = Kind.WORD, _LANG_BY_V[v]
        i += 1
        if i >= n:
            raise DecodeError("언어 화음 뒤에 의미 화음이 없다")
        v = voicing_of(chords[i])
    elif v in _LETTER_BY_V:
        kind, lang = Kind.LETTER, _LETTER_BY_V[v]
        tier, quality = -1, Quality.NEUTRAL
        i += 1

    if kind is not Kind.LETTER:
        cell = _MEANING_BY_V.get(v)
        if cell is None:
            raise DecodeError(f"{i}번째 화음 {chords[i]} 는 의미 화음이 아니다")
        tier, quality = cell
        i += 1

    band = C.BAND[role]
    table = _DIGIT_BY_V[quality]
    nshapes = len(BANKS.digit[quality])
    digits: list[int] = []
    close: int | None = None

    while i < n:
        cv = voicing_of(chords[i])
        if cv in _CLOSE_BY_V:
            close = _CLOSE_BY_V[cv]
            i += 1
            break
        sh_i = table.get(cv)
        if sh_i is None:
            raise DecodeError(
                f"{i}번째 화음 {chords[i]} 는 {quality.value} 자릿 화음이 아니다")
        off = root_of(chords[i]) - band
        if off not in C.DIGIT_OFFSETS:
            raise DecodeError(f"{i}번째 화음의 근음 어긋남 {off} 은 자릿값이 아니다")
        digits.append(C.DIGIT_OFFSETS.index(off) * nshapes + sh_i)
        i += 1

    if close is None:
        raise DecodeError("맺음 화음이 없다")
    if not digits:
        raise DecodeError("자릿 화음이 하나도 없다")

    return (
        Glyph(role, kind, lang, tier, quality, C.index_of(digits), close,
              (), flag),
        i,
    )
