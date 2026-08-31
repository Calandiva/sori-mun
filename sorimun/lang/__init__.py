"""언어 계층 — 문장을 형태소·낱말과 문장 성분으로 푼다.

두 언어가 같은 여덟 자리(sorimun.core.roles.Role)를 공유한다. 자리를
드러내는 방식만 다르다 — 한국어는 조사와 어미가, 영어는 어순과
기능어가 한다.
"""

from __future__ import annotations

from .base import Analysis, Analyzer, Token

_REGISTRY: dict[str, type] = {}


def register(code: str, cls: type) -> None:
    _REGISTRY[code] = cls


def get(code: str) -> Analyzer:
    """언어 코드로 분석기를 얻는다. 'ko' 또는 'en'."""
    if code not in _REGISTRY:
        # 늦게 불러들인다 — 한국어 쪽은 무거운 짐을 질 수 있다
        if code == "ko":
            from . import korean  # noqa: F401
        elif code == "en":
            from . import english  # noqa: F401
    if code not in _REGISTRY:
        raise KeyError(f"모르는 언어: {code} (쓸 수 있는 것: ko, en)")
    return _REGISTRY[code]()


def detect(text: str) -> str:
    """글에서 언어를 가늠한다. 한글이 하나라도 있으면 한국어로 본다."""
    for ch in text:
        if "가" <= ch <= "힣" or "ᄀ" <= ch <= "ᇿ":
            return "ko"
    return "en"


__all__ = ["Analysis", "Analyzer", "Token", "get", "detect", "register"]
