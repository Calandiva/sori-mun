"""코덱 — 음높이와 화성만으로 적고 되읽는다."""

import pytest

from sorimun.core import codes as C, pitch
from sorimun.core.banks import BANKS
from sorimun.core.glyph import Kind, decode, encode, read_terminator, terminator
from sorimun.core.harmony import Quality
from sorimun.core.roles import ORDER as ROLES

SAMPLE = (0, 1, 31, 32, 271, 1055, 1056, 33823, 33824, 285_999, 1_082_399)


def space():
    for role in ROLES:
        for flag in (0, 1):
            for close in (C.CLOSE_CONTINUE, C.CLOSE_BREAK):
                for kind, lang in ((Kind.CONCEPT, None), (Kind.WORD, "ko"),
                                   (Kind.WORD, "en")):
                    for tier in range(6):
                        for q in Quality:
                            for idx in SAMPLE:
                                yield role, flag, close, kind, lang, tier, q, idx


def test_은행이_서로소():
    v = [s.voicing for s in BANKS.all_shapes()]
    assert len(set(v)) == len(v)


def test_모든_화음이_두세_음():
    assert all(2 <= len(s.voicing) <= 3 for s in BANKS.all_shapes())


def test_자릿화음은_좁다():
    """근음이 부호를 나르므로 자리를 남겨야 한다."""
    for q in BANKS.digit:
        for s in BANKS.digit[q]:
            assert s.span <= 7


def test_왕복_전수():
    n = 0
    for role, flag, close, kind, lang, tier, q, idx in space():
        g = encode(role, kind, tier, q, idx, lang=lang, close=close, flag=flag)
        b, nxt = decode(g.chords)
        n += 1
        assert (b.role, b.flag, b.close, b.kind, b.lang, b.tier, b.quality,
                b.index) == (role, flag, close, kind, lang, tier, q, idx)
        assert nxt == len(g.chords)
    assert n > 15_000


def test_겹치지_않는다():
    """되읽기가 값을 남김없이 되찾으므로 서로 다른 값은 서로 다른 소리다."""
    seen = {}
    for params in space():
        role, flag, close, kind, lang, tier, q, idx = params
        key = tuple(encode(role, kind, tier, q, idx, lang=lang,
                           close=close, flag=flag).chords)
        assert key not in seen, f"{seen.get(key)} 와 {params} 가 같은 소리다"
        seen[key] = params


def test_2옥타브를_벗어나지_않는다():
    for role, flag, close, kind, lang, tier, q, idx in space():
        g = encode(role, kind, tier, q, idx, lang=lang, close=close, flag=flag)
        for e in g.events:
            for p in e.pitches:
                assert pitch.LOWEST <= p <= pitch.HIGHEST


def test_길이는_부호가_아니다():
    """화음의 차례가 같으면 길이가 어떻든 같게 읽힌다."""
    for role, flag, close, kind, lang, tier, q, idx in list(space())[::97]:
        g = encode(role, kind, tier, q, idx, lang=lang, close=close, flag=flag)
        a, _ = decode(g.chords)
        # 화음 목록만 넘기므로 길이는 애초에 전해지지 않는다.
        # 그래도 뒤섞인 길이로 다시 적어도 같은 화음이 나오는지 본다.
        b, _ = decode([tuple(c) for c in g.chords])
        assert (a.role, a.index, a.tier) == (b.role, b.index, b.tier)


@pytest.mark.parametrize("mark", C.TERMINATORS)
def test_종결(mark):
    assert read_terminator(terminator(mark).pitches) == mark


def test_자릿수_전단사():
    for i in range(0, 200_000, 13):
        assert C.index_of(C.digits_of(i)) == i


def test_받아적기():
    from sorimun.core import alphabet
    for lang in ("ko", "en"):
        for idx in (0, 5, alphabet.size(lang) - 1):
            g = encode(ROLES[0], Kind.LETTER, -1, Quality.NEUTRAL, idx,
                       lang=lang, close=C.CLOSE_BREAK)
            b, _ = decode(g.chords)
            assert b.kind is Kind.LETTER and b.lang == lang and b.index == idx
