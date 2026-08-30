"""문법 표지 — 조사와 어미의 음형.

조사와 어미는 뜻을 나르지 않는다. 앞말이 문장에서 무슨 자리를 맡는지
표시할 뿐이다. 그래서 화성이 아니라 '몸짓' 으로 옮긴다. 각 격(格)마다
고유한 음정 방향을 주고, 언제나 가장 짧은 음가로 스치듯 지나간다.

    주격 이/가      상행 완전4도    앞말을 들어올려 내세운다
    목적격 을/를    하행 장2도      대상 쪽으로 기운다
    관형격 의       상행 단2도      바로 뒤에 매달린다
    부사격 에/에서  동음            움직이지 않고 자리만 표시한다
    호격 아/야      상행 옥타브     멀리 던지는 부름
    보조사 은/는    하행 완전5도    눌러서 한정한다
    종결어미 다/까  하행 완전4도    문장을 내려놓는다
    …

내용어와 겹치지 않는 근거
────────────────────────
표지는 16분음표(단위 1)만 쓰고, 내용어 음가 목록에는 16분음표가 없다.
그래서 둘은 절대 같은 프레이즈가 될 수 없다.

표지끼리 겹치지 않는 근거
────────────────────────
첫 음에서 둘째 음으로 가는 음정이 곧 그 조사·어미의 기능이며,
14개 기능에 서로 다른 음정을 배정했다. 같은 기능 안에서는 결정적
스트림에서 하나씩 떼어 쓰므로 재사용이 없다.
"""

from __future__ import annotations

from itertools import product
from typing import Iterator

from .phrase import MARKER_DURATION, Event, Phrase

# ── 기능별 기본 음정 (반음). 전부 서로 다르다. ──────────────────────
GESTURE: dict[str, int] = {
    # 조사
    "JKS": +5,   # 주격   이/가/께서   — 들어올려 내세움
    "JKC": +4,   # 보격   이/가        — 다른 것으로 건너감
    "JKG": +1,   # 관형격 의           — 바로 뒤에 매달림
    "JKO": -2,   # 목적격 을/를        — 대상으로 기욺
    "JKB": 0,    # 부사격 에/에서/으로  — 배경, 움직이지 않음
    "JKV": +12,  # 호격   아/야/여      — 멀리 던지는 부름
    "JKQ": +7,   # 인용격 라고/고       — 남의 말을 옮김
    "JX": -7,    # 보조사 은/는/도/만   — 눌러 한정함
    "JC": +2,    # 접속   와/과/하고    — 옆으로 이어붙임
    # 어미
    "EP": -1,    # 선어말 었/겠/시      — 서술어 안쪽에 스밈
    "EF": -5,    # 종결   다/까/요      — 문장을 내려놓음
    "EC": +3,    # 연결   고/며/지만    — 다음 절로 넘김
    "ETM": -3,   # 관형형 은/는/을      — 뒤 체언에 기댐
    "ETN": -4,   # 명사형 음/기         — 용언을 체언으로 굳힘
}

GESTURE_NAME: dict[str, str] = {
    "JKS": "상행 완전4도", "JKC": "상행 장3도", "JKG": "상행 단2도",
    "JKO": "하행 장2도", "JKB": "동음", "JKV": "상행 옥타브",
    "JKQ": "상행 완전5도", "JX": "하행 완전5도", "JC": "상행 장2도",
    "EP": "하행 단2도", "EF": "하행 완전4도", "EC": "상행 단3도",
    "ETM": "하행 단3도", "ETN": "하행 장3도",
}

MARKER_TAGS = frozenset(GESTURE)

# 표지가 쓰는 음. 홑음이거나 좁은 겹음이다. 화성이 아니라 몸짓이므로
# 두껍게 울리지 않는다.
MARKER_VOICINGS: tuple[tuple[int, ...], ...] = (
    (0,), (0, 7), (0, 5), (0, 4), (0, 3), (0, 2),
)
# 표지 뒤에 오는 짧은 숨.
MARKER_RESTS = (0, 1)
# 셋째 음이 붙을 때의 이동.
TAIL_MOTIONS = (0, 2, -2, 5, -5, 7, -7, 3, -3, 4, -4, 1, -1)


def _stream(gesture: int) -> Iterator[Phrase]:
    """한 기능이 쓸 수 있는 표지 음형을 순서대로 낳는다.

    둘째 음의 위치는 언제나 `gesture` 다. 그것이 이 기능의 정체다.
    """
    # 두 음짜리부터. 흔한 조사가 앞을 가져간다.
    for r0, r1, v0, v1 in product(
        MARKER_RESTS, MARKER_RESTS, MARKER_VOICINGS, MARKER_VOICINGS
    ):
        yield Phrase(
            (
                Event(v0, 0, MARKER_DURATION, r0),
                Event(v1, gesture, MARKER_DURATION, r1),
            ),
            is_marker=True,
        )
    # 세 음짜리.
    for r0, r1, r2, m, v0, v1, v2 in product(
        MARKER_RESTS, MARKER_RESTS, MARKER_RESTS, TAIL_MOTIONS,
        MARKER_VOICINGS, MARKER_VOICINGS, MARKER_VOICINGS,
    ):
        yield Phrase(
            (
                Event(v0, 0, MARKER_DURATION, r0),
                Event(v1, gesture, MARKER_DURATION, r1),
                Event(v2, gesture + m, MARKER_DURATION, r2),
            ),
            is_marker=True,
        )


class MarkerAllocator:
    """기능(품사)마다 표지 음형을 하나씩 떼어 준다."""

    def __init__(self) -> None:
        self._streams: dict[str, Iterator[Phrase]] = {}
        self._issued: dict[str, int] = {}

    def take(self, tag: str) -> Phrase:
        if tag not in GESTURE:
            raise KeyError(f"표지가 아닌 품사: {tag}")
        st = self._streams.get(tag)
        if st is None:
            st = _stream(GESTURE[tag])
            self._streams[tag] = st
        try:
            ph = next(st)
        except StopIteration as exc:  # pragma: no cover
            raise RuntimeError(f"{tag} 표지 음형이 고갈됐다") from exc
        self._issued[tag] = self._issued.get(tag, 0) + 1
        return ph

    @property
    def issued(self) -> dict[str, int]:
        return dict(self._issued)
