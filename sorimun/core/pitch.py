"""음역과 음이름.

이 시스템의 모든 소리는 예외 없이 2옥타브 안에 있다.
C3(MIDI 48) 부터 C5(MIDI 72) 까지, 반음 25개.
"""

from __future__ import annotations

# ── 절대 음역: 이 두 값이 시스템 전체의 불변식이다 ────────────────────
LOWEST = 48   # C3
HIGHEST = 72  # C5
SPAN = HIGHEST - LOWEST  # 24 반음 = 정확히 2옥타브

# ── 프레이즈 내부 제약 ───────────────────────────────────────────────
# 화음 하나가 벌릴 수 있는 최대 폭 (근음~최고음)
MAX_CHORD_SPAN = 21
# 프레이즈 하나(여러 화음)가 벌릴 수 있는 최대 폭.
# 24(2옥타브)보다 작아야 어느 프레이즈든 음역 안에 놓을 자리가 남는다.
MAX_PHRASE_AMBITUS = 21


def placement_window(ambitus: int) -> tuple[int, int]:
    """폭이 `ambitus` 인 프레이즈의 최저음이 놓일 수 있는 범위."""
    return LOWEST, HIGHEST - ambitus


def place(target_bottom: int, ambitus: int) -> int:
    """문장 성분이 원하는 높이를, 음역 안에 들어오도록 눌러 맞춘다.

    이동은 통째 조옮김이므로 음정 구조(= 단어의 정체성)는 보존된다.
    """
    lo, hi = placement_window(ambitus)
    if hi < lo:
        raise ValueError(f"폭 {ambitus} 는 2옥타브 안에 들어갈 수 없다")
    return max(lo, min(hi, target_bottom))

_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_NAMES_KO = ["도", "도#", "레", "레#", "미", "파", "파#", "솔", "솔#", "라", "라#", "시"]


def name(midi: int) -> str:
    """MIDI 번호를 음이름으로. 48 -> 'C3'"""
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def name_ko(midi: int) -> str:
    """MIDI 번호를 한국어 음이름으로. 48 -> '도3'"""
    return f"{_NAMES_KO[midi % 12]}{midi // 12 - 1}"


def in_range(midi: int) -> bool:
    return LOWEST <= midi <= HIGHEST


def assert_in_range(pitches) -> None:
    """2옥타브 불변식 검사. 위반하면 즉시 실패한다 (조용히 clamp 하지 않는다)."""
    for p in pitches:
        if not in_range(p):
            raise ValueError(
                f"음역 이탈: {p} ({name(p)}) 은 "
                f"[{LOWEST}({name(LOWEST)}), {HIGHEST}({name(HIGHEST)})] 밖이다"
            )
