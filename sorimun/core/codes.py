"""부호의 자리와 값.

한 낱말은 글리프 하나로 적힌다. 부호를 나르는 것은 **음높이와 화성뿐**
이다.

    [역할 화음] ([언어·받아적기 화음]) [자릿음 1~8] [종지 2음]

두 층이 갈린다.

    저음의 화음   구조를 묘사한다 — 문장 성분(역할), 갈래(언어 전용·
                  받아적기), 낱말 안 글리프 사이의 이음, 문장의 끝(종결).
                  전부 2~3음 화음이고 짧고 조용하게 깔린다.
    홑음의 멜로디 낱말 그 자체다. 길고 또렷하게 노래한다.

낱말의 가락이 먼저 나온다 — 그래야 낱말마다 다르게 들린다.

    자릿음 (1~8음)  번호. 그 성질의 음계 위 계단인데, 계단을 순서대로
                    밟지 않고 지그재그 순열로 밟는다. 이웃한 번호가
                    전혀 다른 윤곽의 가락이 되도록.
    종지 (마지막 2음) 성질과 등급. 첫 음이 3도(장3도=장, 단3도=단,
                    삼전음=중성), 둘째 음이 도약 — 익숙한 낱말은 순하게
                    맺고(완전4도) 생소한 낱말은 긴장으로 맺는다(단2도).
                    음악의 종지가 그 낱말의 성격을 요약한다.

글리프의 끝은 다음 화음이 말한다 — 맺음 화음이 따로 없다. 한 낱말이
여러 글리프로 이어질 때만 사이에 작은 이음 화음을 둔다.

음가와 쉼표는 부호에 쓰이지 않는다. 길이는 오로지 표현이다.
"""

from __future__ import annotations

from .harmony import Quality
from .roles import Role

# ── 구조 화음의 음역 (저음) ──────────────────────────────────────────
# 역할 화음의 근음. 서술어가 가장 낮고 독립어가 가장 높다.
ROLE_PITCH: dict[Role, int] = {
    Role.PREDICATE: 48,
    Role.ADVERBIAL: 49,
    Role.MARKER: 50,
    Role.SUBJECT: 51,
    Role.COMPLEMENT: 52,
    Role.OBJECT: 53,
    Role.ADNOMINAL: 54,
    Role.INDEPENDENT: 55,
}

HEAD_PITCH = 48    # 언어·받아적기·맺음·종결 화음의 근음. 부호를 담지 않는다.

# 역할 화음의 근음에 한 자리를 더 싣는다 (영어 첫 글자 대문자).
FLAG_OFFSETS = (0, 1)

# ── 이름 멜로디 (고음) ───────────────────────────────────────────────
MEL_BASE = 55                      # 멜로디의 기준음 (G3)
MEL_TOP = 72                       # 상한 C5 — 기준음 + 17 이내

# 서명1 — 성질. 기준음에서 몇 반음 위인가.
QUALITY_SIG: dict[Quality, int] = {
    Quality.MAJOR: 4,      # 장3도
    Quality.MINOR: 3,      # 단3도
    Quality.NEUTRAL: 6,    # 삼전음 — 어느 쪽도 아니다
}

# 서명2 — 등급. 서명1에서 몇 반음 뛰는가. 거칢이 단조 증가한다.
#   +5 완전4도(0.12) +8 단6도(0.24) +9 장6도(0.28)
#   +10 단7도(0.62) +6 삼전음(0.78) +1 단2도(1.00)
TIER_LEAP = (5, 8, 9, 10, 6, 1)

# 자릿음 — 성질마다의 음계 (기준음 위 반음). 계단 하나가 진법 한 값이다.
SCALE: dict[Quality, tuple[int, ...]] = {
    Quality.MAJOR: (0, 2, 4, 5, 7, 9, 11, 12, 14, 16),      # 장음계
    Quality.MINOR: (0, 2, 3, 5, 7, 8, 10, 12, 14, 15),      # 자연단음계
    Quality.NEUTRAL: (0, 2, 4, 6, 8, 10, 12, 14, 16),       # 온음계
}

# 지그재그 순열 — 자릿값이 계단을 밟는 차례. 순서대로 밟으면 이웃한
# 번호끼리 거의 같은 가락이 되므로, 이웃 값이 멀리 뛰도록 섞는다.
# 되읽기는 이 표를 거꾸로 볼 뿐이라 아무 순열이어도 정확하다.
DIGIT_ORDER: dict[Quality, tuple[int, ...]] = {
    Quality.MAJOR: (0, 6, 3, 9, 1, 7, 4, 8, 2, 5),
    Quality.MINOR: (0, 6, 3, 9, 1, 7, 4, 8, 2, 5),
    Quality.NEUTRAL: (0, 5, 2, 7, 4, 8, 1, 6, 3),
}

MELODY_MAX_DIGITS = 8              # 자릿 8 + 종지 2 = 최대 10음
MELODY_MIN = 3                     # 자릿 1 + 종지 2

# 받아적기(글자)의 고정 서명 — 글자에는 등급도 감정도 없다.
LETTER_QUALITY = Quality.NEUTRAL
LETTER_TIER = 0

TERMINATORS = (".", "?", "!", "…")

# ── 표현 (부호가 아니다) ─────────────────────────────────────────────
# 구조는 짧고 조용하게, 멜로디는 길고 또렷하게 — 낱말이 주인공이다.
DUR_ROLE = 2
DUR_HEAD = 2
DUR_DIGIT = 3          # 자릿음 — 길게 노래한다 (홀수 번째는 2, 리듬감)
DUR_DIGIT_OFF = 2
DUR_SIG = 3            # 종지 첫 음
DUR_SIG_END = 5        # 종지 끝 음 — 길게 해결한다
DUR_JOIN = 1
DUR_TERM = 10

REST_WORD = 3          # 어절 사이 숨
REST_GLYPH = 1
REST_SENTENCE = 8

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

VEL_ROLE = 58
VEL_HEAD = 52
VEL_SIG = 96
VEL_DIGIT = 92
VEL_JOIN = 44
VEL_TERM = 84
POLARITY_ACCENT = 9


def scaled(duration: int, role: Role, floor: int = 1) -> int:
    num, den = ROLE_DURATION_SCALE[role]
    return max(floor, duration * num // den)


# ── 번호 적기 (성질별 전단사 진법) ───────────────────────────────────
def base_of(quality: Quality) -> int:
    return len(SCALE[quality])


def digits_of(index: int, base: int) -> list[int]:
    """번호를 자릿수 목록으로. 전단사 표기라 앞자리 0 이 없다."""
    if index < 0:
        raise ValueError("번호는 0 이상이어야 한다")
    out: list[int] = []
    m = index + 1
    while m > 0:
        r = m % base or base
        out.append(r - 1)
        m = (m - r) // base
    out.reverse()
    return out


def index_of(digits: list[int], base: int) -> int:
    m = 0
    for d in digits:
        m = m * base + (d + 1)
    return m - 1


def capacity(n_digits: int, base: int) -> int:
    return sum(base ** k for k in range(1, n_digits + 1))
