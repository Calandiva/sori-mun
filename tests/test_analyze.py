"""문장 성분 판별."""

import pytest

from sorimun.core.tags import Role


def roles(analyzer, text):
    return [(e.surface, e.role) for e in analyzer.analyze(text).eojeols]


@pytest.mark.parametrize(
    "text,want",
    [
        # 조사가 성분을 분명히 말해 주는 경우
        ("물이 얼음이 되었다.",
         [("물이", Role.SUBJECT), ("얼음이", Role.COMPLEMENT),
          ("되었다", Role.PREDICATE)]),
        ("아름다운 노래가 밤을 어루만졌다.",
         [("아름다운", Role.ADNOMINAL), ("노래가", Role.SUBJECT),
          ("밤을", Role.OBJECT), ("어루만졌다", Role.PREDICATE)]),
        ("그는 슬픔의 노래를 부른다.",
         [("그는", Role.SUBJECT), ("슬픔의", Role.ADNOMINAL),
          ("노래를", Role.OBJECT), ("부른다", Role.PREDICATE)]),
        ("철수야, 이리 오너라.",
         [("철수야", Role.INDEPENDENT), ("이리", Role.ADVERBIAL),
          ("오너라", Role.PREDICATE)]),
    ],
)
def test_성분_판별(analyzer, text, want):
    assert roles(analyzer, text) == want


def test_보격과_주격을_가른다(analyzer):
    """둘 다 '이/가' 지만 자리가 다르다."""
    e = analyzer.analyze("물이 얼음이 되었다.").eojeols
    assert e[0].morphs[-1].tag == "JKS" and e[0].role is Role.SUBJECT
    assert e[1].morphs[-1].tag == "JKC" and e[1].role is Role.COMPLEMENT


def test_주제화된_목적어(analyzer):
    """'은/는' 뒤에 진짜 주어가 따로 있으면 그쪽이 주어다."""
    a = dict(roles(analyzer, "나는 밥을 먹었다."))
    assert a["나는"] is Role.SUBJECT
    b = dict(roles(analyzer, "밥은 내가 먹었다."))
    assert b["밥은"] is Role.OBJECT
    assert b["내가"] is Role.SUBJECT


def test_관형어는_뒤를_꾸민다(analyzer):
    s = analyzer.analyze("아름다운 노래가 좋다.")
    assert s.eojeols[0].role is Role.ADNOMINAL
    assert s.eojeols[0].modifies == 1


def test_종결부호(analyzer):
    assert analyzer.analyze("봄이 왔다.").terminator == "."
    assert analyzer.analyze("봄이 왔니?").terminator == "?"
    assert analyzer.analyze("봄이 왔구나!").terminator == "!"


def test_감탄사는_독립어(analyzer):
    s = analyzer.analyze("아, 봄이 왔구나!")
    assert s.eojeols[0].role is Role.INDEPENDENT
