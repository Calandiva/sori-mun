"""문장을 소리로 놓는 층."""

import pytest

from sorimun.compose import ROLE_RULES
from sorimun.core import pitch
from sorimun.core.tags import Role

SENTENCES = [
    "아름다운 노래가 어두운 밤을 천천히 어루만졌다.",
    "나는 밥을 먹었다.",
    "밥은 내가 먹었다.",
    "철수야, 물이 얼음이 되었다.",
    "그는 슬픔의 노래를 부른다.",
    "아, 봄이 왔구나!",
    "너는 어디로 가니?",
    "사랑은 죽음보다 강하다.",
    "겨울이 지나면 반드시 봄이 온다.",
    "쀍뿕뿅이 우두두두 쏟아졌다.",
]


@pytest.mark.parametrize("text", SENTENCES)
def test_2옥타브를_벗어나지_않는다(analyzer, composer, text):
    for s in analyzer.sentences(text):
        sc = composer.compose(s)
        assert sc.notes
        for n in sc.notes:
            for p in n.pitches:
                assert pitch.LOWEST <= p <= pitch.HIGHEST, f"{text}: {p}"


@pytest.mark.parametrize("text", SENTENCES)
def test_모든_형태소가_소리로_남는다(analyzer, composer, text):
    for s in analyzer.sentences(text):
        sc = composer.compose(s)
        sounded = {n.source for n in sc.notes}
        for m in s.morphs:
            assert f"{m.form}/{m.tag}" in sounded


@pytest.mark.parametrize("text", SENTENCES)
def test_화음은_두세_음_또는_홑음(analyzer, composer, text):
    for s in analyzer.sentences(text):
        for n in composer.compose(s).notes:
            assert 1 <= len(n.pitches) <= 3
            if n.kind == "내용":
                assert 2 <= len(n.pitches) <= 3   # 내용어는 반드시 화음


@pytest.mark.parametrize("text", SENTENCES)
def test_소리가_겹치지_않고_이어진다(analyzer, composer, text):
    for s in analyzer.sentences(text):
        notes = sorted(composer.compose(s).notes, key=lambda n: n.start)
        for a, b in zip(notes, notes[1:]):
            assert b.start >= a.end, f"{text}: {a.source} 와 {b.source} 가 겹친다"


def test_서술어가_가장_길게_울린다(analyzer, composer):
    sc = composer.compose(analyzer.analyze("노래가 밤을 어루만졌다."))
    content = [n for n in sc.notes if n.kind == "내용"]
    longest = max(content, key=lambda n: n.duration)
    assert longest.role == Role.PREDICATE.value


def test_표지는_모두_16분음표(analyzer, composer):
    for text in SENTENCES:
        for s in analyzer.sentences(text):
            for n in composer.compose(s).notes:
                if n.kind == "표지" and n.role != "맺음":
                    assert n.duration == 1


def test_같은_낱말이_자리에_따라_높이가_달라진다(analyzer, composer):
    """'밤' 의 음정 구조는 같고 높이만 달라야 한다."""
    a = composer.compose(analyzer.analyze("밤이 왔다."))
    b = composer.compose(analyzer.analyze("밤을 새웠다."))
    na = next(n for n in a.notes if n.source == "밤/NNG")
    nb = next(n for n in b.notes if n.source == "밤/NNG")
    ia = [p - na.pitches[0] for p in na.pitches]
    ib = [p - nb.pitches[0] for p in nb.pitches]
    assert ia == ib, "음정 구조(정체성)가 달라졌다"
    assert na.pitches[0] < nb.pitches[0], "주어가 목적어보다 낮아야 한다"


def test_의문문은_말끝을_올린다(analyzer, composer):
    sc = composer.compose(analyzer.analyze("너는 어디로 가니?"))
    assert sc.notes[-1].role == "맺음"


def test_성분_규칙표가_모든_성분을_덮는다():
    for role in Role:
        assert role in ROLE_RULES
