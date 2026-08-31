"""분석기가 지켜야 할 모양."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..core.roles import Role


@dataclass(frozen=True, slots=True)
class Token:
    """낱말 한 개 또는 형태소 한 개."""

    form: str        # 사전에서 찾을 꼴 (한국어는 기본형, 영어는 소문자 낱말)
    tag: str         # 품사
    role: Role       # 문장에서 맡은 자리
    group: int       # 몇 번째 어절/낱말 덩이에 속하는가
    surface: str = ""   # 원문에 나타난 꼴 (있으면)

    @property
    def key(self) -> tuple[str, str]:
        return (self.form, self.tag)

    def __str__(self) -> str:
        return f"{self.form}/{self.tag}"


@dataclass(slots=True)
class Analysis:
    """문장 하나를 푼 결과."""

    text: str
    tokens: list[Token] = field(default_factory=list)
    terminator: str = "."
    lang: str = "ko"

    @property
    def groups(self) -> list[list[Token]]:
        out: list[list[Token]] = []
        for t in self.tokens:
            if not out or out[-1][0].group != t.group:
                out.append([t])
            else:
                out[-1].append(t)
        return out


class Analyzer(Protocol):
    lang: str

    def sentences(self, text: str) -> list[Analysis]: ...

    def analyze(self, text: str) -> Analysis: ...

    def join(self, tokens: list[tuple[str, str]], groups: list[int]) -> str:
        """형태소에서 문장을 되짓는다. 되읽기의 마지막 걸음."""
        ...
