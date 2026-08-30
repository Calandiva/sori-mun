"""화성 어휘가 규칙대로 갈리는지."""

from itertools import combinations

import pytest

from sorimun.core import pitch
from sorimun.core.harmony import (
    N_TIERS, Quality, dissonance, enumerate_shapes, quality, shape_table,
)


@pytest.mark.parametrize(
    "voicing,want",
    [
        ((0, 4, 7), Quality.MAJOR),    # 장3화음
        ((0, 3, 8), Quality.MAJOR),    # 장3화음 1전위
        ((0, 5, 9), Quality.MAJOR),    # 장3화음 2전위
        ((0, 4, 11), Quality.MAJOR),   # 장7화음 (5음 생략)
        ((0, 4), Quality.MAJOR),       # 장3도
        ((0, 8), Quality.MAJOR),       # 단6도 = 장3도의 자리바꿈
        ((0, 3, 7), Quality.MINOR),    # 단3화음
        ((0, 3, 6), Quality.MINOR),    # 감3화음
        ((0, 3, 10), Quality.MINOR),   # 단7화음
        ((0, 3), Quality.MINOR),       # 단3도
        ((0, 9), Quality.MINOR),       # 장6도 = 단3도의 자리바꿈
        ((0, 7), Quality.NEUTRAL),     # 완전5도
        ((0, 5), Quality.NEUTRAL),     # 완전4도
        ((0, 2, 7), Quality.NEUTRAL),  # sus2
        ((0, 5, 7), Quality.NEUTRAL),  # sus4
        ((0, 5, 10), Quality.NEUTRAL), # 4도쌓기
        ((0, 4, 8), Quality.NEUTRAL),  # 증3화음 — 어느 쪽도 아니다
        ((0, 1, 2), Quality.NEUTRAL),  # 반음 뭉치
    ],
)
def test_성질_판별(voicing, want):
    assert quality(voicing) is want


def test_협화도_순서():
    """귀에 들리는 순서대로 값이 매겨져야 한다."""
    assert dissonance((0, 12)) < dissonance((0, 7)) < dissonance((0, 4, 7))
    assert dissonance((0, 4, 7)) < dissonance((0, 1, 2))
    assert dissonance((0, 7)) < dissonance((0, 6))     # 5도가 삼전음보다 순하다
    assert dissonance((0, 4, 7)) == pytest.approx(dissonance((0, 3, 7)), abs=1e-9)


def test_모양은_한_칸에만_속한다():
    """겹침 없음의 근거. 한 보이싱이 두 칸에 있으면 안 된다."""
    shapes = enumerate_shapes()
    seen = {}
    for s in shapes:
        assert s.voicing not in seen, f"{s.voicing} 가 두 번 나온다"
        seen[s.voicing] = (s.tier, s.quality)
    table = shape_table()
    for cell_a, cell_b in combinations(table, 2):
        va = {s.voicing for s in table[cell_a]}
        vb = {s.voicing for s in table[cell_b]}
        assert not (va & vb), f"{cell_a} 와 {cell_b} 가 모양을 공유한다"


def test_모든_칸이_차_있다():
    table = shape_table()
    for tier in range(N_TIERS):
        for q in Quality:
            cell = table.get((tier, q), [])
            assert len(cell) >= 2, f"칸 {tier}/{q.value} 이 너무 얇다: {len(cell)}"


def test_화음은_두세_음뿐():
    for s in enumerate_shapes():
        assert 2 <= s.size <= 3
        assert s.span <= pitch.MAX_CHORD_SPAN
