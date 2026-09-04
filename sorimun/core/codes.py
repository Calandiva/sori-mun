"""부호의 자리와 값.

멜로디만 들으면 낱말이고, 함께 울리는 화성을 들으면 그 낱말의 역할이다.

    낱말 = [으뜸음 + 화성] [자릿음 …] [종지1 (+표지 내성)] [종지2]

모든 소리의 꼭대기가 멜로디다. 화성은 멜로디 아래에만 깔리고, 규칙은
셋뿐이다.

    베이스   언제나 C3 페달 — 낱말이 시작될 때 으뜸음과 함께 울린다.
    역할 내성 베이스 위 몇 반음인가가 문장 성분이다. 흔한 역할일수록
             협화로운 음정을 받는다:
                 표지 +7(완전5도)  주어 +5(완전4도)  목적어 +4(장3도)
                 서술어 +3(단3도)  부사어 +8(단6도)  보어 +6(삼전음)
                 관형어 +2(장2도)  독립어 +1(단2도)
    표지 내성 종지 첫 음 아래 49~56 창에 갈래(언어·받아적기)·대문자·
             이음 표지가 선다. 개념이고 소문자고 낱말이 끝나면 아무
             내성도 없다 — 종지1 은 홑음이다.

멜로디의 짜임 — 낱말은 첫 음부터 제 소리로 시작한다.

    시작     따로 여는 화음이 없다. 낱말의 첫 자릿음이 곧 첫 소리이고,
             베이스와 역할 내성은 그 아래에 깔려 함께 울릴 뿐이다 —
             그래서 낱말마다 다른 음으로 문을 연다.
    으뜸음   성질마다의 조 집합(장 3조 · 단 3조 · 중성 2조)에서 낱말의
             정체가 고른다. 으뜸음 자체는 울리지 않고 종지가 말해 준다.
    자릿음   으뜸음 위 그 성질의 음계를 지그재그 순열로 밟는 홑음들.
             자릿값이 리듬(3~5)까지 만든다.
    종지     으뜸음 위 3도(장3도=장, 단3도=단, 삼전음=중성)로 올라섰다가
             아래로 해결한다. 종지1 의 절대 음높이가 (성질, 으뜸음) 을
             유일하게 밝힌다 — 여덟 닻이 서로 겹치지 않으므로. 하행
             도약의 거칢이 등급이다.

문장의 끝은 멜로디 없는 저음 이중음이다.

음가와 쉼표는 부호에 쓰이지 않는다. 길이는 오로지 표현이다.
"""

from __future__ import annotations

from .harmony import Quality
from .roles import Role

# ── 화성(반주) — 전부 멜로디 아래 ────────────────────────────────────
PEDAL = 48                          # 베이스 C3 — 낱말의 첫 울림

# 역할 내성: 베이스 위 몇 반음인가. 흔한 역할일수록 협화롭게.
ROLE_INNER: dict[Role, int] = {
    Role.MARKER: 7,        # 완전5도 — 가장 잦은 자리, 가장 순하게
    Role.SUBJECT: 5,       # 완전4도
    Role.OBJECT: 4,        # 장3도
    Role.PREDICATE: 3,     # 단3도
    Role.ADVERBIAL: 8,     # 단6도
    Role.COMPLEMENT: 6,    # 삼전음
    Role.ADNOMINAL: 2,     # 장2도
    Role.INDEPENDENT: 1,   # 단2도 — 가장 드문 자리
}

# 표지 내성 (종지1 아래): 갈래·대문자·이음. 절대 음높이라 서로 겹치지
# 않고, 있으면 읽고 없으면 없는 것이다.
KIND_MARK = {("WORD", "ko"): 49, ("WORD", "en"): 50,
             ("LETTER", "ko"): 51, ("LETTER", "en"): 52}
FLAG_MARK = 54                      # 영어 첫 글자 대문자
JOIN_MARK = 56                      # 같은 낱말이 다음 글리프로 이어진다

# 종결 — 멜로디 없는 저음 이중음
TERM_SET = {".": (48, 55), "?": (48, 53), "!": (48, 51), "…": (48, 49)}
TERMINATORS = (".", "?", "!", "…")

# ── 이름 멜로디 ──────────────────────────────────────────────────────
# 성질마다의 조 집합. 종지1 = 으뜸음 + 3도가 성질마다 서로 다른 창에
# 떨어지도록 골랐다 — 종지1 하나로 (성질, 으뜸음) 이 유일하게 풀린다.
#   장   57 59 61 + 4 → 61 63 65
#   단   57 59 61 + 3 → 60 62 64
#   중성 60 61    + 6 → 66 67
TONIC_SET: dict[Quality, tuple[int, ...]] = {
    Quality.MAJOR: (57, 59, 61),
    Quality.MINOR: (57, 59, 61),
    Quality.NEUTRAL: (60, 61),
}
MEL_BASE = 57                       # (안내·표시용)


def tonic_of(quality: Quality, tier: int, index: int) -> int:
    """낱말의 으뜸음. 같은 낱말은 언제나 같은 조를 갖는다."""
    ts = TONIC_SET[quality]
    return ts[(index + 3 * max(0, tier)) % len(ts)]


QUALITY_SIG: dict[Quality, int] = {
    Quality.MAJOR: 4, Quality.MINOR: 3, Quality.NEUTRAL: 6,
}

# 종지1 의 절대음 → (성질, 으뜸음). 서로소가 규칙의 핵심이다.
SIG_ANCHOR: dict[int, tuple[Quality, int]] = {}
for _q, _ts in TONIC_SET.items():
    for _t in _ts:
        _s = _t + QUALITY_SIG[_q]
        assert _s not in SIG_ANCHOR, f"종지 닻 충돌: {_s}"
        SIG_ANCHOR[_s] = (_q, _t)

# 종지 하행 도약 — 거칢이 단조 증가한다.
#   -5 완전4도(0.12) -8 단6도(0.24) -9 장6도(0.28)
#   -10 단7도(0.62) -6 삼전음(0.78) -1 단2도(1.00)
TIER_LEAP = (5, 8, 9, 10, 6, 1)

# 자릿음 — 성질마다의 음계 (으뜸음 위 반음). 한 옥타브 남짓 안.
SCALE: dict[Quality, tuple[int, ...]] = {
    Quality.MAJOR: (0, 2, 4, 5, 7, 9, 11),       # 장음계
    Quality.MINOR: (0, 2, 3, 5, 7, 8, 10),       # 자연단음계
    Quality.NEUTRAL: (0, 2, 4, 6, 8, 10),        # 온음계
}

# 지그재그 순열 — 이웃한 번호가 전혀 다른 윤곽이 되도록.
DIGIT_ORDER: dict[Quality, tuple[int, ...]] = {
    Quality.MAJOR: (0, 4, 2, 6, 1, 5, 3),
    Quality.MINOR: (0, 4, 2, 6, 1, 5, 3),
    Quality.NEUTRAL: (0, 3, 1, 5, 2, 4),
}

MELODY_MAX_DIGITS = 8              # 으뜸 1 + 자릿 8 + 종지 2 = 최대 11음
MELODY_MIN = 4

LETTER_QUALITY = Quality.NEUTRAL
LETTER_TIER = 0

# ── 표현 (부호가 아니다) ─────────────────────────────────────────────
DUR_TONIC = 3          # 으뜸음 — 화성과 함께 낱말을 연다
DUR_DIGIT = 3          # 자릿음 기본 (자릿값 mod 3 을 더해 3~5)
DUR_SIG = 3
DUR_SIG_END = 6        # 해결음 — 길게
DUR_TERM = 8

REST_WORD = 3
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

VEL_SIG = 98
VEL_DIGIT = 92
VEL_ACC = 52           # 화성(베이스·내성)은 멜로디보다 한 걸음 뒤에
VEL_TERM = 80
POLARITY_ACCENT = 9


def scaled(duration: int, role: Role, floor: int = 1) -> int:
    num, den = ROLE_DURATION_SCALE[role]
    return max(floor, duration * num // den)


# ── 번호 적기 (성질별 전단사 진법) ───────────────────────────────────
def base_of(quality: Quality) -> int:
    return len(SCALE[quality])


def digits_of(index: int, base: int) -> list[int]:
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
