"""코덱 — 음높이와 화성만으로 적고 되읽는다."""

import pytest

from sorimun.core import codes as C, pitch
from sorimun.core.glyph import (Kind, decode, encode, is_start,
                                read_terminator, terminator)
from sorimun.core.harmony import Quality
from sorimun.core.roles import ORDER as ROLES

SAMPLE = (0, 1, 6, 7, 55, 56, 391, 392, 19_607, 185_930)


def space():
    for role in ROLES:
        for flag in (0, 1):
            for join in (False, True):
                for kind, lang in ((Kind.CONCEPT, None), (Kind.WORD, "ko"),
                                   (Kind.WORD, "en")):
                    for tier in range(6):
                        for q in Quality:
                            for idx in SAMPLE:
                                yield role, flag, join, kind, lang, tier, q, idx


def test_화성_규칙이_서로소():
    """베이스는 늘 C3, 내성들은 겹치지 않는 창을 나눠 갖는다."""
    ri = list(C.ROLE_INNER.values())
    assert len(set(ri)) == len(ri)
    marks = set(C.KIND_MARK.values()) | {C.FLAG_MARK, C.JOIN_MARK}
    assert len(marks) == len(C.KIND_MARK) + 2
    assert all(C.PEDAL < m <= 56 for m in marks)      # 으뜸음(57~) 아래 창
    assert min(C.TONICS) > 56                          # 표지 창과 서로소
    terms = [frozenset(v) for v in C.TERM_SET.values()]
    assert len(set(terms)) == len(terms)
    assert all(max(v) <= 56 for v in C.TERM_SET.values())


def test_머리만_베이스를_품는다():
    """C3 페달은 낱말의 머리에만 울린다 — 그래서 경계를 오독할 수 없다."""
    for role, flag, join, kind, lang, tier, q, idx in list(space())[::173]:
        g = encode(role, kind, tier, q, idx, lang=lang, flag=flag, join=join)
        assert is_start(g.chords[0])
        for c in g.chords[1:]:
            assert C.PEDAL not in c
            assert not is_start(c)


def test_멜로디가_축을_노래한다():
    """모든 소리의 꼭대기가 멜로디다. 첫 음이 으뜸음, 마지막 두 음이
    성질(3도)과 등급(하행 도약)을 맺는다."""
    for q, sig in ((Quality.MAJOR, 4), (Quality.MINOR, 3),
                   (Quality.NEUTRAL, 6)):
        for tier in range(6):
            g = encode(ROLES[3], Kind.CONCEPT, tier, q, 42)
            mel = g.melody
            tonic = mel[0]
            assert tonic in C.TONICS
            assert mel[-2] - tonic == sig                     # 종지 = 성질
            assert mel[-2] - mel[-1] == C.TIER_LEAP[tier]     # 하행 = 등급
            for p in mel[1:-2]:                               # 자릿음 = 음계
                assert p - tonic in C.SCALE[q]


def test_역할은_내성이다():
    """멜로디만 들으면 낱말, 화성을 함께 들으면 역할이다 — 같은 낱말은
    역할이 달라도 같은 멜로디를 부른다."""
    mels = set()
    for role in ROLES:
        g = encode(role, Kind.CONCEPT, 0, Quality.MAJOR, 50)
        mels.add(tuple(g.melody))
        head = g.chords[0]
        assert head[0] == C.PEDAL
        assert head[1] - C.PEDAL == C.ROLE_INNER[role]
    assert len(mels) == 1


def test_으뜸음이_조를_옮긴다():
    """낱말의 정체가 조를 정한다 — 이웃 번호가 다른 조로 옮겨 간다."""
    tonics = {encode(ROLES[3], Kind.CONCEPT, 0, Quality.MAJOR, i).melody[0]
              for i in range(10)}
    assert len(tonics) == len(C.TONICS)


def test_이웃_번호는_다른_윤곽():
    """지그재그 순열 — 번호가 1 달라지면 가락이 눈에 띄게 달라진다."""
    mels = [tuple(encode(ROLES[3], Kind.CONCEPT, 0, Quality.MAJOR, i).melody)
            for i in range(30)]
    assert len(set(mels)) == 30


def test_멜로디_길이_경계():
    g = encode(ROLES[0], Kind.CONCEPT, 0, Quality.MAJOR, 0)
    assert len(g.melody) == 4          # 으뜸 1 + 자릿 1 + 종지 2
    big = C.capacity(C.MELODY_MAX_DIGITS, 7) - 1
    g = encode(ROLES[0], Kind.CONCEPT, 0, Quality.MAJOR, big)
    assert len(g.melody) == 11         # 으뜸 1 + 자릿 8 + 종지 2


def test_자릿음은_홑음이다():
    """화성은 머리(베이스+내성)와 종지1(표지)에만 선다."""
    g = encode(ROLES[3], Kind.WORD, 0, Quality.MAJOR, 50, lang="ko",
               flag=1, join=True)
    assert len(g.chords[0]) == 3                       # 머리
    for c in g.chords[1:-2]:
        assert len(c) == 1                             # 자릿음
    assert len(g.chords[-2]) == 4                      # 종지1 + 표지 셋
    assert len(g.chords[-1]) == 1                      # 종지2


def test_왕복_전수():
    n = 0
    for role, flag, join, kind, lang, tier, q, idx in space():
        g = encode(role, kind, tier, q, idx, lang=lang, flag=flag, join=join)
        b, nxt = decode(g.chords)
        n += 1
        assert (b.role, b.flag, b.join, b.kind, b.lang, b.tier, b.quality,
                b.index) == (role, flag, join, kind, lang, tier, q, idx)
        assert nxt == len(g.chords)
    assert n > 8_000


def test_겹치지_않는다():
    """되읽기가 값을 남김없이 되찾으므로 서로 다른 값은 서로 다른 소리다."""
    seen = {}
    for params in space():
        role, flag, join, kind, lang, tier, q, idx = params
        key = tuple(encode(role, kind, tier, q, idx, lang=lang, flag=flag,
                           join=join).chords)
        assert key not in seen, f"{seen.get(key)} 와 {params} 가 같은 소리다"
        seen[key] = params


def test_2옥타브를_벗어나지_않는다():
    for role, flag, join, kind, lang, tier, q, idx in space():
        g = encode(role, kind, tier, q, idx, lang=lang, flag=flag, join=join)
        for e in g.events:
            for p in e.pitches:
                assert pitch.LOWEST <= p <= pitch.HIGHEST


def test_길이는_부호가_아니다():
    """화음의 차례가 같으면 길이가 어떻든 같게 읽힌다."""
    for role, flag, join, kind, lang, tier, q, idx in list(space())[::97]:
        g = encode(role, kind, tier, q, idx, lang=lang, flag=flag, join=join)
        a, _ = decode(g.chords)
        b, _ = decode([tuple(c) for c in g.chords])
        assert (a.role, a.index, a.tier) == (b.role, b.index, b.tier)


@pytest.mark.parametrize("mark", C.TERMINATORS)
def test_종결(mark):
    assert read_terminator(terminator(mark).pitches) == mark


def test_자릿수_전단사():
    for base in (6, 7):
        for i in range(0, 300_000, 13):
            assert C.index_of(C.digits_of(i, base), base) == i


def test_받아적기():
    from sorimun.core import alphabet
    for lang in ("ko", "en"):
        for idx in (0, 5, alphabet.size(lang) - 1):
            g = encode(ROLES[0], Kind.LETTER, -1, Quality.NEUTRAL, idx,
                       lang=lang)
            b, _ = decode(g.chords)
            assert b.kind is Kind.LETTER and b.lang == lang and b.index == idx
