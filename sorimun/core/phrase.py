"""프레이즈 — 한 낱말의 음악적 지문.

프레이즈는 '정체성' 만 담는다. 음정 구조, 리듬, 쉼표. 절대 음높이는
담지 않는다. 절대 높이는 문장 안에서의 역할(문장 성분)이 정한다.
그래서 "사랑이" 의 사랑과 "사랑을" 의 사랑은 높이가 다르되 같은
모티프로 들린다.

겹침 없음(injectivity)의 근거
────────────────────────────
1. `harmony.shape_table()` 은 120개 화음 모양을 (등급, 성질) 칸으로
   완전 분할한다. 한 모양은 정확히 한 칸에만 속한다.
2. 프레이즈는 자기 칸의 모양만 쓴다.
3. 따라서 서로 다른 칸의 프레이즈는 첫 화음부터 이미 다르다.
4. 같은 칸 안에서는 결정적 스트림에서 하나씩 꺼내 쓰므로 재사용이 없다.
   ⇒ 사전 전체에서 프레이즈는 유일하다. 사후 검사가 아니라 구성상 보장.

내용어와 문법 표지의 분리
────────────────────────
가장 짧은 음가(16분음표, 단위 1)는 조사·어미 전용으로 예약한다.
내용어 프레이즈에는 단위 1 이 절대 나타나지 않는다. 그래서 16분음표가
섞인 프레이즈는 언제나 문법 표지이고, 둘은 결코 겹치지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import gcd
from typing import Iterator

from . import pitch
from .harmony import Quality, Shape, shape_table

# ── 음가 단위: 1 = 16분음표, 4 = 4분음표 ─────────────────────────────
UNIT_PER_QUARTER = 4

# 내용어가 쓰는 음가. '자연스러운' 순서로 둔다 — 흔한 낱말일수록
# 스트림 앞쪽을 받으므로 평범한 리듬을 갖는다.
CONTENT_DURATIONS = (4, 2, 8, 3, 6)      # ♩ ♪ 𝅗𝅥 ♪. ♩.
# 조사·어미 전용 음가.
MARKER_DURATION = 1                       # 𝅘𝅥𝅯

# 화음 뒤에 오는 쉼표. 0 은 쉼표 없음.
RESTS = (0, 1, 2, 4)

# 화음과 화음 사이 근음의 이동(반음). 순한 것부터.
ROOT_MOTIONS = (0, 2, -2, -5, 5, 7, -7, 4, -4, 3, -3, 1, -1)

MAX_EVENTS = 3


@dataclass(frozen=True, slots=True)
class Event:
    """화음 하나와 그 길이, 그리고 뒤따르는 쉼표."""

    voicing: tuple[int, ...]   # 근음 기준 반음 오프셋 (2음 또는 3음)
    root: int                  # 프레이즈 기준점에 대한 근음 위치
    duration: int              # 16분음표 단위
    rest_after: int = 0        # 16분음표 단위, 0 이면 쉼표 없음

    @property
    def offsets(self) -> tuple[int, ...]:
        """프레이즈 기준점에 대한 각 음의 오프셋."""
        return tuple(self.root + v for v in self.voicing)

    def shifted(self, shift: int) -> tuple[int, ...]:
        """오프셋 전체를 `shift` 만큼 옮긴 실제 MIDI 음높이."""
        return tuple(shift + o for o in self.offsets)

    @property
    def total(self) -> int:
        return self.duration + self.rest_after


@dataclass(frozen=True, slots=True)
class Phrase:
    """한 사전 표제어에 대응하는 음형."""

    events: tuple[Event, ...]
    is_marker: bool = False

    # ── 파생 속성 ────────────────────────────────────────────────
    @property
    def low(self) -> int:
        return min(min(e.offsets) for e in self.events)

    @property
    def high(self) -> int:
        return max(max(e.offsets) for e in self.events)

    @property
    def ambitus(self) -> int:
        return self.high - self.low

    @property
    def length(self) -> int:
        """쉼표까지 포함한 전체 길이(16분음표 단위)."""
        return sum(e.total for e in self.events)

    @property
    def n_events(self) -> int:
        return len(self.events)

    def normalized(self) -> "Phrase":
        """최저음이 0 이 되도록 통째로 내린다. 정규형."""
        d = self.low
        if d == 0:
            return self
        return Phrase(
            tuple(
                Event(e.voicing, e.root - d, e.duration, e.rest_after)
                for e in self.events
            ),
            self.is_marker,
        )

    def key(self) -> tuple:
        """동일성 판정용 정규 키. 이 값이 같으면 같은 프레이즈다."""
        n = self.normalized()
        return tuple(
            (e.voicing, e.root, e.duration, e.rest_after) for e in n.events
        )

    def fit_shift(self, desired: int) -> int:
        """원하는 이동량을, 음역 안에 들어오도록 눌러 맞춘다.

        통째 조옮김이므로 음정 구조(= 낱말의 정체성)는 그대로다.
        """
        lo = pitch.LOWEST - self.low
        hi = pitch.HIGHEST - self.high
        if hi < lo:
            raise ValueError(f"폭 {self.ambitus} 는 2옥타브 안에 들어갈 수 없다")
        return max(lo, min(hi, desired))

    def render_at(self, shift: int) -> list[tuple[tuple[int, ...], int, int]]:
        """이동량을 직접 주어 (음높이들, 음가, 뒤쉼표) 목록을 낸다."""
        out = []
        for e in self.events:
            ps = e.shifted(shift)
            pitch.assert_in_range(ps)
            out.append((ps, e.duration, e.rest_after))
        return out

    def render(self, bottom: int) -> list[tuple[tuple[int, ...], int, int]]:
        """프레이즈의 '가장 낮은 음' 이 `bottom` 에 놓이도록 통째로 옮긴 뒤
        (음높이들, 음가, 뒤쉼표) 목록을 낸다.

        근음 이동이 아래로 갈 수 있으므로 오프셋은 음수일 수 있다.
        그래서 기준점이 아니라 실제 최저음을 맞춘다.

        2옥타브 불변식을 여기서 검사한다. 조용히 눌러 맞추지 않고
        어긋나면 바로 실패한다.
        """
        shift = bottom - self.low
        out = []
        for e in self.events:
            ps = e.shifted(shift)
            pitch.assert_in_range(ps)
            out.append((ps, e.duration, e.rest_after))
        return out


# ── 프레이즈 스트림 ──────────────────────────────────────────────────
# 축 순서가 중요하다. 스트림 앞쪽은 빈도가 높은 낱말이 가져가고, 그런
# 낱말일수록 자주 들리므로 서로 잘 구별돼야 한다. 그래서 '화음 모양'을
# 가장 빨리 바뀌는 축에 둔다. 쉼표는 가장 느리게 바뀌어서, 맨 앞
# 구간에는 쉼표 없는 깔끔한 음형만 나온다.


def _stream_for_group(
    shapes: list[Shape],
    durations: tuple[int, ...],
    max_events: int = MAX_EVENTS,
) -> Iterator[Phrase]:
    """한 칸(등급×성질)이 쓸 수 있는 프레이즈를 순서대로 낳는다.

    앞쪽일수록 짧고 단순하다.
    """
    if not shapes:
        return
    for k in range(1, max_events + 1):
        yield from _stream_k(shapes, durations, k)


def _stream_k(
    shapes: list[Shape], durations: tuple[int, ...], k: int
) -> Iterator[Phrase]:
    """정확히 k개의 화음을 갖는 프레이즈들.

    itertools.product 는 마지막 인자가 가장 빨리 바뀐다. 그래서
    (쉼표들, 음가들, 근음이동들, 모양들) 순으로 넘긴다.
    """
    rest_axes = [RESTS] * k
    dur_axes = [durations] * k
    motion_axes = [ROOT_MOTIONS] * (k - 1)
    shape_axes = [shapes] * k

    for combo in product(*rest_axes, *dur_axes, *motion_axes, *shape_axes):
        i = 0
        rests = combo[i:i + k]; i += k
        durs = combo[i:i + k]; i += k
        motions = combo[i:i + k - 1]; i += k - 1
        shs = combo[i:i + k]

        events = []
        root = 0
        for j in range(k):
            if j:
                root += motions[j - 1]
            events.append(Event(shs[j].voicing, root, durs[j], rests[j]))
        ph = Phrase(tuple(events))
        if ph.ambitus <= pitch.MAX_PHRASE_AMBITUS:
            yield ph


class PhraseAllocator:
    """(등급, 성질) 칸마다 프레이즈를 하나씩 떼어 준다.

    같은 프레이즈를 두 번 주지 않는다. 칸이 서로소이므로 전역에서도
    겹치지 않는다.
    """

    def __init__(self, max_events: int = MAX_EVENTS) -> None:
        self._table = shape_table()
        self._streams: dict[tuple[int, Quality], Iterator[Phrase]] = {}
        self._issued: dict[tuple[int, Quality], int] = {}
        self._max_events = max_events

    def take(self, tier: int, quality: Quality) -> Phrase:
        cell = (tier, quality)
        st = self._streams.get(cell)
        if st is None:
            shapes = self._table.get(cell, [])
            if not shapes:
                raise KeyError(f"빈 칸: tier={tier} quality={quality}")
            st = _stream_for_group(shapes, CONTENT_DURATIONS, self._max_events)
            self._streams[cell] = st
        try:
            ph = next(st)
        except StopIteration as exc:  # pragma: no cover - 용량 초과
            raise RuntimeError(
                f"칸 {cell} 의 프레이즈가 고갈됐다 "
                f"({self._issued.get(cell, 0)}개 발급). MAX_EVENTS 를 늘려라."
            ) from exc
        self._issued[cell] = self._issued.get(cell, 0) + 1
        return ph

    @property
    def issued(self) -> dict[tuple[int, Quality], int]:
        return dict(self._issued)


# ── 색인으로 바로 뽑기 ───────────────────────────────────────────────
# 사전에 없는 낱말(미등재어)에 쓴다. 스트림을 처음부터 돌리지 않고
# 정수 하나로 프레이즈를 정한다.
#
# 미등재어는 언제나 OOV_EVENTS(=4)개의 화음을 쓴다. 사전에 실린 낱말은
# 최대 MAX_EVENTS(=3)개까지만 쓰므로, 둘은 음형 개수만으로 이미 갈린다.
# 사전 항목과 미등재어가 겹칠 일이 없다.
OOV_EVENTS = 4


# 폭 제약에 걸렸을 때 옆자리를 볼 보폭 후보. 공간 크기와 서로소인
# 것을 골라 쓰면 훑다가 제자리를 맴돌지 않고 공간 전체를 돈다.
_PROBE_STRIDES = (1_000_003, 999_983, 104_729, 7_919, 97, 1)


def phrase_at_index(
    shapes: list[Shape],
    durations: tuple[int, ...],
    k: int,
    index: int,
    max_probe: int = 100_000,
) -> Phrase:
    """k음형 조합 공간의 `index` 번째 프레이즈.

    폭 제약을 어기는 자리는 건너뛰고 다음 자리를 본다. 같은 index 는
    언제나 같은 프레이즈를 낸다.

    옆자리를 1씩 옮겨 보면 가장 빨리 바뀌는 자리(마지막 화음 모양)만
    달라진다. 근음 이동이 이미 폭을 넘겨 버린 구역에서는 모양을 아무리
    바꿔도 소용이 없어 갇힌다. 그래서 공간 크기와 서로소인 보폭으로
    건너뛴다. 그러면 이동·음가·쉼표 자리까지 골고루 바뀐다.
    """
    ns, nd, nr = len(shapes), len(durations), len(RESTS)
    nm = len(ROOT_MOTIONS)
    # product 와 같은 자리 순서: 쉼표들, 음가들, 이동들, 모양들
    radices = [nr] * k + [nd] * k + [nm] * (k - 1) + [ns] * k
    total = 1
    for r in radices:
        total *= r

    stride = next(s for s in _PROBE_STRIDES if gcd(s, total) == 1)

    for probe in range(max_probe):
        i = (index + probe * stride) % total
        digits = []
        for r in reversed(radices):
            digits.append(i % r)
            i //= r
        digits.reverse()

        p = 0
        rests = [RESTS[d] for d in digits[p:p + k]]; p += k
        durs = [durations[d] for d in digits[p:p + k]]; p += k
        motions = [ROOT_MOTIONS[d] for d in digits[p:p + k - 1]]; p += k - 1
        shs = [shapes[d] for d in digits[p:p + k]]

        events = []
        root = 0
        for j in range(k):
            if j:
                root += motions[j - 1]
            events.append(Event(shs[j].voicing, root, durs[j], rests[j]))
        ph = Phrase(tuple(events))
        if ph.ambitus <= pitch.MAX_PHRASE_AMBITUS:
            return ph

    raise RuntimeError("유효한 프레이즈를 찾지 못했다")


# ── 직렬화 ───────────────────────────────────────────────────────────
def encode(ph: Phrase) -> str:
    """프레이즈를 한 줄 문자열로. 예: '0,4,7;0;4;0|0,7;2;2;1'"""
    return "|".join(
        f"{','.join(map(str, e.voicing))};{e.root};{e.duration};{e.rest_after}"
        for e in ph.events
    )


def decode(code: str, is_marker: bool = False) -> Phrase:
    events = []
    for part in code.split("|"):
        v, root, dur, rest = part.split(";")
        events.append(
            Event(
                tuple(int(x) for x in v.split(",")),
                int(root), int(dur), int(rest),
            )
        )
    return Phrase(tuple(events), is_marker)
