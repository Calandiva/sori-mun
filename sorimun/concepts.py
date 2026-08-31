"""개념 — 두 말을 잇는 층.

'사랑' 과 'love' 는 같은 개념 번호를 갖는다. 소리에는 그 번호만 적히므로
어느 말로도 읽어 낼 수 있다. 소리 자체가 하나의 말이 되는 셈이다.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from pathlib import Path

from .core.harmony import Quality

PATH = Path(__file__).resolve().parent.parent / "data" / "concepts.tsv.gz"
APPROX_PATH = Path(__file__).resolve().parent.parent / "data" / "approx.tsv.gz"


@dataclass(frozen=True, slots=True)
class Concept:
    index: int
    ko_form: str
    ko_tag: str
    en_form: str
    en_tag: str
    freq: int
    polarity: int
    tier: int

    @property
    def quality(self) -> Quality:
        if self.polarity > 0:
            return Quality.MAJOR
        if self.polarity < 0:
            return Quality.MINOR
        return Quality.NEUTRAL

    def form(self, lang: str) -> tuple[str, str]:
        return (self.ko_form, self.ko_tag) if lang == "ko" \
            else (self.en_form, self.en_tag)

    def __str__(self) -> str:
        return f"{self.ko_form}↔{self.en_form}"


# 개념도 낱말과 같은 잣대로 등급을 매긴다 — 흔할수록 순한 화음.
TIER_BANDS = (300, 1_500, 6_000, 25_000, 100_000)


def _tier(rank: int) -> int:
    for i, b in enumerate(TIER_BANDS):
        if rank <= b:
            return i
    return len(TIER_BANDS)


class Concepts:
    _one: "Concepts | None" = None

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATH
        self._by_index: list[Concept] = []
        self._by_ko: dict[tuple[str, str], Concept] = {}
        self._by_en: dict[tuple[str, str], Concept] = {}
        # 근사 — 개념이 되지 못한 낱말을 가장 가까운 개념에 잇는다.
        # 소리에는 낱말의 정확한 번호가 적히므로 같은 말로는 그대로
        # 돌아오고, 다른 말로 읽을 때만 이 표가 쓰인다.
        self._approx: dict[tuple[str, str, str], int] = {}
        if self.path.exists():
            self._load()
        if APPROX_PATH.exists():
            self._load_approx()

    def _load_approx(self) -> None:
        with gzip.open(APPROX_PATH, "rt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t")
            next(rd)
            for lang, form, tag, ci in rd:
                self._approx[(lang, form, tag)] = int(ci)

    @classmethod
    def load(cls) -> "Concepts":
        if cls._one is None:
            cls._one = cls()
        return cls._one

    def _load(self) -> None:
        with gzip.open(self.path, "rt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t")
            next(rd)
            for i, (idx, ko, ko_tag, en, en_tag, freq, pol) in enumerate(rd):
                c = Concept(int(idx), ko, ko_tag, en, en_tag,
                            int(freq), int(pol), _tier(i + 1))
                self._by_index.append(c)
                self._by_ko[(ko, ko_tag)] = c
                self._by_en[(en, en_tag)] = c

    # ── 낱말 → 개념 ─────────────────────────────────────────────────
    def of(self, lang: str, form: str, tag: str) -> Concept | None:
        table = self._by_ko if lang == "ko" else self._by_en
        return table.get((form, tag))

    def approx(self, lang: str, form: str, tag: str) -> Concept | None:
        """가장 가까운 개념. 정확한 개념이 있으면 그쪽을 먼저 낸다."""
        c = self.of(lang, form, tag)
        if c is not None:
            return c
        ci = self._approx.get((lang, form, tag))
        return self.at(ci) if ci is not None else None

    # ── 번호 → 개념 ─────────────────────────────────────────────────
    def at(self, index: int) -> Concept | None:
        return self._by_index[index] if 0 <= index < len(self._by_index) else None

    def __len__(self) -> int:
        return len(self._by_index)

    @property
    def all(self) -> list[Concept]:
        return list(self._by_index)
