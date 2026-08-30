"""겹침 없음 — 사전 전체 검사.

이 프로젝트의 핵심 약속이다. 28만 항목 어느 둘도 같은 프레이즈를
갖지 않는다.
"""

from sorimun.core.phrase import CONTENT_DURATIONS, MARKER_DURATION


def test_사전_전체에서_프레이즈가_유일하다(dictionary):
    seen: dict[tuple, tuple[str, str]] = {}
    for e in dictionary.entries:
        k = e.phrase.key()
        assert k not in seen, (
            f"{seen.get(k)} 와 ({e.form}, {e.tag}) 가 같은 프레이즈를 쓴다"
        )
        seen[k] = (e.form, e.tag)
    assert len(seen) == len(dictionary)


def test_내용어와_표지는_음가로_갈린다(dictionary):
    for e in dictionary.entries:
        durs = {ev.duration for ev in e.phrase.events}
        if e.is_marker:
            assert durs == {MARKER_DURATION}
        else:
            assert MARKER_DURATION not in durs
            assert durs <= set(CONTENT_DURATIONS)


def test_모든_항목이_2옥타브_안에_놓인다(dictionary):
    from sorimun.core import pitch

    for e in dictionary.entries:
        ph = e.phrase
        lo, hi = pitch.placement_window(ph.ambitus)
        assert hi >= lo
        for bottom in (lo, hi):
            for ps, _d, _r in ph.render(bottom):
                for p in ps:
                    assert pitch.LOWEST <= p <= pitch.HIGHEST
