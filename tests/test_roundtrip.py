"""문장이 소리를 거쳐 그대로 돌아오는가."""

import random

import pytest

from conftest import EN_SENTENCES, KO_SENTENCES
from sorimun.compose import Composer
from sorimun.decompose import read, render


def trip(lang, analyzer, text):
    p = Composer(lang, analyzer=analyzer).compose(analyzer.analyze(text))
    return p, read(p.chords)


@pytest.mark.parametrize("text", KO_SENTENCES)
def test_한국어_왕복(ko, text):
    p, r = trip("ko", ko, text)
    assert render(r, "ko", ko) == text


@pytest.mark.parametrize("text", EN_SENTENCES)
def test_영어_왕복(en, text):
    p, r = trip("en", en, text)
    assert render(r, "en", en) == text


@pytest.mark.parametrize("text", KO_SENTENCES[:8] + EN_SENTENCES[:8])
def test_길이를_흔들어도_같다(ko, en, text):
    from sorimun.lang import detect
    lang = detect(text)
    an = ko if lang == "ko" else en
    p, _ = trip(lang, an, text)
    base = render(read(p.chords), lang, an)
    rng = random.Random(len(text))
    for _ in range(3):
        for n in p.notes:
            n.duration = rng.randint(1, 30)
            n.velocity = rng.randint(20, 127)
        assert render(read(p.chords), lang, an) == base


@pytest.mark.parametrize("text", KO_SENTENCES[:10] + EN_SENTENCES[:10])
def test_2옥타브(ko, en, text):
    from sorimun.core import pitch
    from sorimun.lang import detect
    lang = detect(text)
    p, _ = trip(lang, ko if lang == "ko" else en, text)
    for n in p.notes:
        for x in n.pitches:
            assert pitch.LOWEST <= x <= pitch.HIGHEST


def test_사전에_없는_말도_돌아온다(ko, en):
    for lang, an, text in (("ko", ko, "쀍뿕뿅이 우두두두 쏟아졌다."),
                           ("en", en, "Zxqwv frobnicates the widget.")):
        p, r = trip(lang, an, text)
        assert render(r, lang, an) == text
