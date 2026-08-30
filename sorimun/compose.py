"""작곡 — 분석된 문장을 소리로 놓는다.

사전은 낱말의 '정체성'(음정 구조·리듬·쉼표)만 준다. 그것을 2옥타브
어디에, 얼마나 길게, 어떤 세기로 놓을지는 문장 성분이 정한다.

    독립어   가장 높이, 앞뒤로 긴 쉼표를 두르고 홀로     A4 언저리
    관형어   높고 짧게. 뒤 체언에 곧바로 달라붙는다      E4 언저리
    목적어   중고음역. 대상을 밝게 내건다                C4 언저리
    보어     중음역. 주어 곁에 선다                      A3 언저리
    주어     중저음역. 문장을 떠받친다                    G3 언저리
    부사어   낮고 짧게. 색을 입힐 뿐 자리를 차지하지 않는다 E3 언저리
    서술어   가장 낮고 가장 길게. 문장을 내려놓는다        C3 언저리

높이를 옮기는 것은 통째 조옮김이므로 낱말의 정체성은 상하지 않는다.
같은 '밤' 이 주어 자리에서는 낮게, 목적어 자리에서는 높게 울릴 뿐
음정 구조는 같다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .core import pitch
from .core.analyze import Eojeol, Sentence
from .core.tags import Role
from .dictionary import Dictionary, Entry

UNITS_PER_QUARTER = 4


@dataclass(frozen=True, slots=True)
class RoleRule:
    """문장 성분 하나가 소리에 거는 조건."""

    register: int      # 목표 최저음 (MIDI)
    dur_num: int       # 음가 배율
    dur_den: int
    rest_before: int   # 16분음표 단위
    rest_after: int
    velocity: int
    note: str          # 사람이 읽을 설명


ROLE_RULES: dict[Role, RoleRule] = {
    Role.INDEPENDENT: RoleRule(67, 1, 1, 4, 4, 92, "가장 높이, 앞뒤로 긴 쉼표를 두르고 홀로"),
    Role.ADNOMINAL:   RoleRule(64, 1, 2, 0, 0, 62, "높고 짧게, 뒤 체언에 곧바로 붙는다"),
    Role.OBJECT:      RoleRule(60, 1, 1, 0, 2, 80, "중고음역, 대상을 밝게 내건다"),
    Role.COMPLEMENT:  RoleRule(57, 1, 1, 0, 2, 78, "중음역, 주어 곁에 선다"),
    Role.SUBJECT:     RoleRule(55, 1, 1, 0, 2, 82, "중저음역, 문장을 떠받친다"),
    Role.ADVERBIAL:   RoleRule(52, 3, 4, 0, 1, 70, "낮고 짧게, 색을 입힌다"),
    Role.PREDICATE:   RoleRule(48, 2, 1, 1, 6, 88, "가장 낮고 가장 길게, 문장을 내려놓는다"),
    Role.MARKER:      RoleRule(60, 1, 1, 0, 0, 55, "앞말이 끝난 자리에서 짧게 스친다"),
}

MIN_CONTENT_DURATION = 2   # 16분음표는 조사·어미 전용이므로 내용어는 8분 이상
MARKER_VELOCITY = 55
POLARITY_ACCENT = 8        # 극성이 셀수록 또렷하게

# 문장 끝맺음
TERMINATOR_TAIL = {
    "?": +2,    # 의문: 상행 장2도를 하나 덧붙여 말끝을 올린다
    "!": None,  # 감탄: 덧붙이지 않고 세기로 맺는다
    ".": None,
}
TERMINATOR_REST = {".": 8, "?": 8, "!": 6, "…": 12}
TERMINATOR_ACCENT = {"!": 14, "?": 4}


@dataclass(slots=True)
class Note:
    """실제로 울리는 소리 하나. 화음이면 pitches 가 2~3개다."""

    pitches: tuple[int, ...]
    start: int         # 16분음표 단위
    duration: int
    velocity: int
    source: str        # '사랑/NNG'
    role: str
    kind: str          # '내용' / '표지'

    @property
    def end(self) -> int:
        return self.start + self.duration

    @property
    def names(self) -> str:
        return "+".join(pitch.name(p) for p in self.pitches)


@dataclass(slots=True)
class Score:
    """한 문장을 옮긴 악보."""

    notes: list[Note] = field(default_factory=list)
    sentence: Sentence | None = None
    tempo: int = 66
    entries: list[tuple[str, Entry, Role]] = field(default_factory=list)

    @property
    def length(self) -> int:
        return max((n.end for n in self.notes), default=0)

    @property
    def ambitus(self) -> tuple[int, int]:
        if not self.notes:
            return (pitch.LOWEST, pitch.LOWEST)
        lo = min(min(n.pitches) for n in self.notes)
        hi = max(max(n.pitches) for n in self.notes)
        return (lo, hi)


def _scale(d: int, num: int, den: int, floor: int) -> int:
    return max(floor, (d * num) // den)


class Composer:
    """문장을 악보로 옮긴다."""

    def __init__(self, dictionary: Dictionary, tempo: int = 66) -> None:
        self.dict = dictionary
        self.tempo = tempo

    def compose(self, sentence: Sentence) -> Score:
        score = Score(sentence=sentence, tempo=self.tempo)
        cursor = 0
        anchor = 60   # 표지가 매달릴 자리. 앞말의 마지막 근음.

        for e in sentence.eojeols:
            rule = ROLE_RULES[e.role]
            cursor += rule.rest_before
            cursor, anchor = self._place_eojeol(score, e, rule, cursor, anchor)
            cursor += rule.rest_after

        self._finish(score, sentence, cursor, anchor)
        return score

    # ── 어절 하나 놓기 ──────────────────────────────────────────────
    def _place_eojeol(
        self, score: Score, e: Eojeol, rule: RoleRule, cursor: int, anchor: int
    ) -> tuple[int, int]:
        for m in e.morphs:
            entry = self.dict.get(m.form, m.tag)
            ph = entry.phrase
            score.entries.append((str(m), entry, e.role))

            if entry.is_marker:
                # 표지는 앞말이 끝난 높이에서 출발해 제 몸짓을 그린다.
                shift = ph.fit_shift(anchor - ph.events[0].root)
                vel = MARKER_VELOCITY
                num = den = 1
                floor = 1
            else:
                shift = ph.fit_shift(rule.register - ph.low)
                vel = min(127, rule.velocity + POLARITY_ACCENT * abs(entry.polarity))
                num, den = rule.dur_num, rule.dur_den
                floor = MIN_CONTENT_DURATION

            for ev in ph.events:
                ps = ev.shifted(shift)
                pitch.assert_in_range(ps)
                dur = _scale(ev.duration, num, den, floor)
                score.notes.append(
                    Note(
                        pitches=ps, start=cursor, duration=dur, velocity=vel,
                        source=f"{m.form}/{m.tag}", role=e.role.value,
                        kind=entry.kind,
                    )
                )
                cursor += dur + _scale(ev.rest_after, num, den, 0)
                anchor = ps[0]

        return cursor, anchor

    # ── 맺음 ────────────────────────────────────────────────────────
    def _finish(
        self, score: Score, sentence: Sentence, cursor: int, anchor: int
    ) -> None:
        term = sentence.terminator
        if not score.notes:
            return

        # 감탄·의문은 마지막 서술어를 더 또렷하게 한다.
        accent = TERMINATOR_ACCENT.get(term, 0)
        if accent:
            for n in reversed(score.notes):
                if n.role == Role.PREDICATE.value:
                    n.velocity = min(127, n.velocity + accent)
                else:
                    break

        # 의문문은 말끝을 올린다.
        tail = TERMINATOR_TAIL.get(term)
        if tail:
            p = anchor + tail
            if not pitch.in_range(p):
                p = anchor - (12 - tail)
            if pitch.in_range(p):
                score.notes.append(
                    Note(
                        pitches=(p,), start=cursor + 1, duration=2,
                        velocity=MARKER_VELOCITY + 10,
                        source=f"종결{term}", role="맺음", kind="표지",
                    )
                )


def compose_text(analyzer, dictionary: Dictionary, text: str, tempo: int = 66) -> list[Score]:
    """글 전체를 문장마다 악보로 옮긴다."""
    c = Composer(dictionary, tempo)
    return [c.compose(s) for s in analyzer.sentences(text)]
