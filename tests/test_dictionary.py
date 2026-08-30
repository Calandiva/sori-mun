"""사전 조회."""

import pytest

from sorimun.core.markers import GESTURE


def test_은는이가가_기능별로_들어_있다(dictionary):
    """요구사항: 은/는/이/가 같은 것도 사전으로 존재해야 한다."""
    for form in ("은", "는", "이", "가"):
        entries = [e for e in dictionary.find(form) if e.is_marker]
        assert entries, f"{form} 의 표지 항목이 없다"
    # 같은 '이' 라도 기능이 갈려 있어야 한다
    tags = {e.tag for e in dictionary.find("이") if e.is_marker}
    assert {"JKS", "JKC"} <= tags


def test_같은_글자_다른_기능은_다른_음형(dictionary):
    entries = [e for e in dictionary.find("이") if e.is_marker]
    keys = {e.phrase.key() for e in entries}
    assert len(keys) == len(entries)


def test_표지의_첫_음정이_격을_말한다(dictionary):
    for e in dictionary.entries:
        if not e.is_marker:
            continue
        ph = e.phrase
        assert ph.events[1].root - ph.events[0].root == GESTURE[e.tag]


def test_극성이_성질을_정한다(dictionary):
    for e in dictionary.entries:
        if e.is_marker:
            continue
        want = "major" if e.polarity > 0 else "minor" if e.polarity < 0 else "neutral"
        assert e.quality == want


@pytest.mark.parametrize(
    "form,tag,want",
    [("사랑", "NNG", "major"), ("슬프", "VA", "minor"),
     ("아름답", "VA", "major"), ("고통", "NNG", "minor")],
)
def test_감정이_장단을_가른다(dictionary, form, tag, want):
    assert dictionary.get(form, tag).quality == want


def test_흔한_낱말이_더_협화롭다(dictionary):
    a = dictionary.get("사람", "NNG")
    b = dictionary.get("괴괴", "XR")
    assert a.tier < b.tier


def test_미등재어(dictionary):
    e = dictionary.get("쀍뿕뿅", "NNG")
    assert not e.known
    assert e.tier == 5
    assert e.phrase.n_events == 4      # 사전 항목은 최대 3개


def test_미등재어는_사전과_겹치지_않는다(dictionary):
    """음형 개수만으로 이미 갈린다."""
    for e in dictionary.entries:
        assert e.phrase.n_events <= 3
    oov = dictionary.get("없는말이야", "NNG")
    assert oov.phrase.n_events == 4


def test_불규칙_태그_정규화(dictionary):
    assert dictionary.get("아름답", "VA-I").form == "아름답"
    assert dictionary.get("아름답", "VA-I").quality == "major"
