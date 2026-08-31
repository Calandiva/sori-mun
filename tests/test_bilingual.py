"""하나의 소리, 두 개의 말."""

import pytest

from sorimun.compose import Composer
from sorimun.decompose import read, render

PAIRS = [
    ("en", "The spring came.", "ko", "봄이 왔다."),
    ("ko", "봄이 왔다.", "en", "The spring came."),
    ("en", "The child laughed quietly.", "ko", "아이가 조용히 웃었다."),
    ("ko", "아이가 조용히 웃었다.", "en", "The child laughed quietly."),
    ("ko", "물이 어두웠다.", "en", "The water was dark."),
    ("en", "The water was dark.", "ko", "물이 어두웠다."),
    ("ko", "밤이 깊다.", "en", "The night is deep."),
    ("en", "The night is deep.", "ko", "밤이 깊다."),
]


@pytest.mark.parametrize("src,text,dst,want", PAIRS)
def test_다른_말로_읽어_낸다(ko, en, src, text, dst, want):
    sa = ko if src == "ko" else en
    da = ko if dst == "ko" else en
    p = Composer(src, analyzer=sa).compose(sa.analyze(text))
    assert render(read(p.chords), dst, da) == want


def test_소리에는_말이_담기지_않는다(ko, en):
    """같은 뜻이면 어느 말로 적었든 개념 번호가 같아야 한다."""
    pk = Composer("ko", analyzer=ko).compose(ko.analyze("봄이 왔다."))
    pe = Composer("en", analyzer=en).compose(en.analyze("The spring came."))
    a = [(g.role, g.index) for g in pk.glyphs if g.kind.value == "개념"]
    b = [(g.role, g.index) for g in pe.glyphs if g.kind.value == "개념"]
    assert a == b


def test_한바퀴_돌아_제자리(ko, en):
    text = "The child laughed quietly."
    r1 = read(Composer("en", analyzer=en).compose(en.analyze(text)).chords)
    korean = render(r1, "ko", ko)
    r2 = read(Composer("ko", analyzer=ko).compose(ko.analyze(korean)).chords)
    assert render(r2, "en", en) == text


def test_개념은_양방향(concepts):
    for c in concepts.all:
        assert concepts.at(c.index) is c
        assert concepts.of("en", c.en_form, c.en_tag) is c
        if c.ko_tag != "∅":
            assert concepts.of("ko", c.ko_form, c.ko_tag) is c
