"""프레이즈 생성과 겹침 없음."""

import itertools

import pytest

from sorimun.core import pitch
from sorimun.core.harmony import Quality, shape_table
from sorimun.core.phrase import (
    CONTENT_DURATIONS, MARKER_DURATION, OOV_EVENTS, PhraseAllocator,
    _stream_for_group, decode, encode, phrase_at_index,
)


def test_직렬화_왕복():
    a = PhraseAllocator()
    for _ in range(200):
        ph = a.take(2, Quality.MINOR)
        assert decode(encode(ph)).key() == ph.key()


def test_한_칸_안에서_겹치지_않는다():
    a = PhraseAllocator()
    seen = set()
    for _ in range(3000):
        k = a.take(3, Quality.NEUTRAL).key()
        assert k not in seen
        seen.add(k)


def test_칸이_다르면_반드시_다르다():
    """서로 다른 (등급, 성질) 은 화음 모양부터 다르다."""
    a = PhraseAllocator()
    seen = {}
    for tier in range(6):
        for q in Quality:
            for _ in range(60):
                k = a.take(tier, q).key()
                assert k not in seen, f"{seen.get(k)} 와 {(tier, q)} 가 겹친다"
                seen[k] = (tier, q)


def test_내용어에는_16분음표가_없다():
    assert MARKER_DURATION not in CONTENT_DURATIONS
    a = PhraseAllocator()
    for tier in range(6):
        for q in Quality:
            for _ in range(50):
                ph = a.take(tier, q)
                for e in ph.events:
                    assert e.duration != MARKER_DURATION


def test_폭_제약():
    a = PhraseAllocator()
    for tier in range(6):
        for q in Quality:
            for _ in range(100):
                assert a.take(tier, q).ambitus <= pitch.MAX_PHRASE_AMBITUS


def test_흔할수록_짧다():
    """스트림 앞쪽이 뒤쪽보다 화음 개수가 적거나 같아야 한다."""
    shapes = shape_table()[(0, Quality.NEUTRAL)]
    counts = [
        ph.n_events
        for ph in itertools.islice(_stream_for_group(shapes, CONTENT_DURATIONS), 4000)
    ]
    assert counts == sorted(counts)


def test_어떤_자리에_놓아도_2옥타브_안():
    a = PhraseAllocator()
    for tier in range(6):
        for q in Quality:
            for _ in range(40):
                ph = a.take(tier, q)
                lo, hi = pitch.placement_window(ph.ambitus)
                for bottom in (lo, (lo + hi) // 2, hi):
                    for ps, _d, _r in ph.render(bottom):
                        for p in ps:
                            assert pitch.LOWEST <= p <= pitch.HIGHEST


def test_미등재어는_음형이_네_개():
    shapes = shape_table()[(5, Quality.NEUTRAL)]
    for i in (0, 7, 1234, 10**12):
        ph = phrase_at_index(shapes, CONTENT_DURATIONS, OOV_EVENTS, i)
        assert ph.n_events == OOV_EVENTS
        assert ph.ambitus <= pitch.MAX_PHRASE_AMBITUS


def test_색인이_다르면_대체로_다르다():
    shapes = shape_table()[(5, Quality.NEUTRAL)]
    keys = {
        phrase_at_index(shapes, CONTENT_DURATIONS, OOV_EVENTS, i).key()
        for i in range(500)
    }
    assert len(keys) == 500
