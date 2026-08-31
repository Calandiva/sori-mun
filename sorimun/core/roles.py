"""문장 성분 — 두 언어가 함께 쓰는 여덟 자리.

한국어와 영어는 자리를 드러내는 방식이 다르다. 한국어는 조사가,
영어는 어순과 기능어가 한다. 그러나 '무엇이 무엇을 어찌한다' 는 뼈대
자체는 같으므로, 같은 여덟 자리를 함께 쓴다. 그래서 두 언어가 같은
규칙으로 소리 난다.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    PREDICATE = "서술어"      # verb — 문장을 끝맺는 자리
    ADVERBIAL = "부사어"      # adverbial — 색을 입히는 자리
    MARKER = "표지"           # 조사·어미 / article·preposition·auxiliary
    SUBJECT = "주어"          # subject
    COMPLEMENT = "보어"       # complement
    OBJECT = "목적어"         # object
    ADNOMINAL = "관형어"      # adjectival — 체언을 꾸미는 자리
    INDEPENDENT = "독립어"    # interjection·vocative


ENGLISH_NAME = {
    Role.PREDICATE: "predicate",
    Role.ADVERBIAL: "adverbial",
    Role.MARKER: "marker",
    Role.SUBJECT: "subject",
    Role.COMPLEMENT: "complement",
    Role.OBJECT: "object",
    Role.ADNOMINAL: "adnominal",
    Role.INDEPENDENT: "independent",
}

# 은행에서 몇 번째 화음을 쓰는가. 순서를 바꾸면 사전이 달라진다.
ORDER: tuple[Role, ...] = (
    Role.PREDICATE, Role.ADVERBIAL, Role.MARKER, Role.SUBJECT,
    Role.COMPLEMENT, Role.OBJECT, Role.ADNOMINAL, Role.INDEPENDENT,
)
INDEX = {r: i for i, r in enumerate(ORDER)}
