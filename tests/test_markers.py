"""조사·어미 표지."""

from sorimun.core.markers import GESTURE, MARKER_TAGS, MarkerAllocator
from sorimun.core.phrase import MARKER_DURATION


def test_격마다_음정이_다르다():
    assert len(set(GESTURE.values())) == len(GESTURE)


def test_표지는_모두_16분음표():
    a = MarkerAllocator()
    for tag in MARKER_TAGS:
        for _ in range(30):
            ph = a.take(tag)
            assert ph.is_marker
            for e in ph.events:
                assert e.duration == MARKER_DURATION


def test_첫_음정이_그_격의_정체다():
    a = MarkerAllocator()
    for tag, g in GESTURE.items():
        for _ in range(20):
            ph = a.take(tag)
            assert ph.events[1].root - ph.events[0].root == g


def test_표지끼리_겹치지_않는다():
    a = MarkerAllocator()
    seen = {}
    for tag in MARKER_TAGS:
        for _ in range(200):
            k = a.take(tag).key()
            assert k not in seen, f"{seen.get(k)} 와 {tag} 가 겹친다"
            seen[k] = tag
