"""품사 태그와, 그것이 문장에서 맡는 자리.

세종 품사 체계를 쓴다. mecab-ko-dic 과 kiwi 가 모두 이 체계를 따르므로
사전(표제어)과 분석기(형태소)가 같은 열쇠로 맞물린다.
"""

from __future__ import annotations

# ── 대분류 ───────────────────────────────────────────────────────────
SUBSTANTIVE = {"NNG", "NNP", "NNB", "NNBC", "NP", "NR"}   # 체언
PREDICATE = {"VV", "VA", "VX", "VCP", "VCN"}              # 용언
MODIFIER = {"MM", "MAG", "MAJ"}                           # 수식언
INDEPENDENT = {"IC"}                                      # 독립언
PARTICLE = {"JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC"}  # 조사
ENDING = {"EP", "EF", "EC", "ETN", "ETM"}                 # 어미
AFFIX = {"XPN", "XSN", "XSV", "XSA", "XSM", "XR"}         # 접사·어근
SYMBOL = {"SF", "SP", "SS", "SE", "SO", "SW", "SL", "SH", "SN"}

CONTENT = SUBSTANTIVE | PREDICATE | MODIFIER | INDEPENDENT | AFFIX
GRAMMATICAL = PARTICLE | ENDING

KOREAN_NAME = {
    "NNG": "일반명사", "NNP": "고유명사", "NNB": "의존명사", "NNBC": "단위명사",
    "NP": "대명사", "NR": "수사",
    "VV": "동사", "VA": "형용사", "VX": "보조용언",
    "VCP": "긍정지정사", "VCN": "부정지정사",
    "MM": "관형사", "MAG": "부사", "MAJ": "접속부사", "IC": "감탄사",
    "JKS": "주격조사", "JKC": "보격조사", "JKG": "관형격조사",
    "JKO": "목적격조사", "JKB": "부사격조사", "JKV": "호격조사",
    "JKQ": "인용격조사", "JX": "보조사", "JC": "접속조사",
    "EP": "선어말어미", "EF": "종결어미", "EC": "연결어미",
    "ETN": "명사형어미", "ETM": "관형형어미",
    "XPN": "접두사", "XSN": "명사파생접미사", "XSV": "동사파생접미사",
    "XSA": "형용사파생접미사", "XSM": "부사파생접미사", "XR": "어근",
}


def normalize(tag: str) -> str:
    """kiwi 의 불규칙 표시(VA-I, VV-R …)를 떼어 낸다."""
    if "-" in tag:
        tag = tag.split("-", 1)[0]
    return tag
