"""부호의 자리와 값.

한 낱말은 글리프 하나로 적힌다. 부호를 나르는 것은 **음높이와 화성뿐**
이다.

    [역할 화음] [머리 화음] [자릿 화음 × k] [맺음 화음]

    역할 화음   문장에서 맡은 자리. 모양이 자리를 말하고, 근음이
                그 자리의 음역대를 그린다.
    머리 화음   세 갈래 중 하나.
                  의미 화음     (등급, 성질) — 언어에 매이지 않는 개념
                  언어 화음     그 언어에만 있는 낱말이 온다는 표시
                  받아적기 화음 글자를 하나씩 적는다는 표시
    자릿 화음   번호를 적어 나간다. 근음이 음역대 바닥에서 얼마나
                올라갔는가와 화음 모양, 이 둘이 한 자릿수를 이룬다.
    맺음 화음   글리프 끝. 두 가지가 있어 어절이 이어지는지 끊기는지도
                함께 말한다.

음가와 쉼표는 부호에 쓰이지 않는다. 사람이 연주하면 길이는 흔들리기
마련이므로, 흔들려도 뜻이 상하지 않아야 한다. 길이는 오로지 표현이다.
"""

from __future__ import annotations

from .roles import Role

# ── 자리별 음역 ──────────────────────────────────────────────────────
ROLE_PITCH: dict[Role, int] = {
    Role.PREDICATE: 48,     # C3  — 가장 낮게 착지한다
    Role.ADVERBIAL: 51,
    Role.MARKER: 53,
    Role.SUBJECT: 55,       # G3  — 문장을 떠받친다
    Role.COMPLEMENT: 57,
    Role.OBJECT: 59,
    Role.ADNOMINAL: 61,
    Role.INDEPENDENT: 61,   # C#4 — 가장 높이, 홀로
}

# 자릿 화음이 놓이는 음역대의 바닥.
# 바닥 + 최대 어긋남(7) + 자릿 화음 최대 폭(7) ≤ 72 이어야 한다.
BAND: dict[Role, int] = {
    Role.PREDICATE: 48,
    Role.ADVERBIAL: 50,
    Role.MARKER: 51,
    Role.SUBJECT: 52,
    Role.COMPLEMENT: 54,
    Role.OBJECT: 55,
    Role.ADNOMINAL: 57,
    Role.INDEPENDENT: 58,
}

HEAD_PITCH = 48    # 머리·맺음·종결 화음의 근음. 부호를 담지 않는다.

# 역할 화음의 근음에 한 자리를 더 싣는다. 음높이이므로 길이가 흔들려도
# 살아남는다. 영어의 첫 글자 대문자 여부를 여기에 담는다.
FLAG_OFFSETS = (0, 1)

# ── 자릿수 ───────────────────────────────────────────────────────────
DIGIT_OFFSETS = (0, 1, 2, 3, 4, 5, 6, 7)   # 음역대 바닥에서 올라간 반음
DIGIT_SHAPES_PER_QUALITY = 4
BASE = len(DIGIT_OFFSETS) * DIGIT_SHAPES_PER_QUALITY   # 8 × 4 = 32

# ── 맺음 ─────────────────────────────────────────────────────────────
CLOSE_CONTINUE = 0   # 같은 어절이 이어진다
CLOSE_BREAK = 1      # 어절이 끝난다

TERMINATORS = (".", "?", "!", "…")

# ── 표현 (부호가 아니다) ─────────────────────────────────────────────
# 길이와 세기는 뜻을 담지 않는다. 오로지 듣기 좋으라고 있다.
DUR_ROLE = 4
DUR_HEAD = 8
DUR_DIGIT = 3
DUR_CLOSE = 2
DUR_TERM = 12

REST_AFTER_CLOSE = {CLOSE_CONTINUE: 1, CLOSE_BREAK: 3}
REST_SENTENCE = 8

# 자리마다 길이를 조금씩 달리해 문장이 숨을 쉬게 한다. 부호가 아니므로
# 마음대로 바꾸어도 뜻은 그대로다.
ROLE_DURATION_SCALE: dict[Role, tuple[int, int]] = {
    Role.PREDICATE: (3, 2),
    Role.ADVERBIAL: (3, 4),
    Role.MARKER: (1, 2),
    Role.SUBJECT: (1, 1),
    Role.COMPLEMENT: (1, 1),
    Role.OBJECT: (1, 1),
    Role.ADNOMINAL: (3, 4),
    Role.INDEPENDENT: (3, 2),
}

VEL_ROLE = 84
VEL_HEAD = 98
VEL_DIGIT = 72
VEL_CLOSE = 60
VEL_TERM = 90
POLARITY_ACCENT = 9


def scaled(duration: int, role: Role, floor: int = 1) -> int:
    num, den = ROLE_DURATION_SCALE[role]
    return max(floor, duration * num // den)


# ── 번호 적기 (전단사 32진법) ────────────────────────────────────────
def digits_of(index: int) -> list[int]:
    """번호를 자릿수 목록으로. 앞자리 0 이 생기지 않아 길이가 달라도
    헷갈리지 않는다. 맺음 화음이 끝을 말하므로 길이를 따로 적을 필요가 없다."""
    if index < 0:
        raise ValueError("번호는 0 이상이어야 한다")
    out: list[int] = []
    m = index + 1
    while m > 0:
        r = m % BASE or BASE
        out.append(r - 1)
        m = (m - r) // BASE
    out.reverse()
    return out


def index_of(digits: list[int]) -> int:
    m = 0
    for d in digits:
        m = m * BASE + (d + 1)
    return m - 1


def capacity(n_digits: int) -> int:
    return sum(BASE ** k for k in range(1, n_digits + 1))
