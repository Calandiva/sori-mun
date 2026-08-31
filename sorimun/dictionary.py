"""사전 — 낱말과 (등급, 성질, 번호) 사이를 오간다.

앞으로도 뒤로도 간다. 적을 때는 낱말에서 번호를, 되읽을 때는 번호에서
낱말을 얻는다. 이 두 길이 정확히 서로의 역이라는 것이 이 프로젝트의
약속이다.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from pathlib import Path

from .core.harmony import Quality

DATA = Path(__file__).resolve().parent.parent / "data"

TIER_LABEL = ("아주 흔함", "흔함", "보통", "드묾", "아주 드묾", "희귀·미등재")
TIER_LABEL_EN = ("very common", "common", "ordinary", "uncommon",
                 "rare", "very rare")


@dataclass(frozen=True, slots=True)
class Entry:
    form: str
    tag: str
    freq: int
    rank: int
    tier: int
    polarity: int
    quality: Quality
    index: int
    lang: str

    @property
    def cell(self) -> tuple[int, Quality]:
        return (self.tier, self.quality)

    @property
    def tier_label(self) -> str:
        return TIER_LABEL[self.tier]

    def __str__(self) -> str:
        return f"{self.form}/{self.tag}"


class Dictionary:
    """한 언어의 사전."""

    _cache: dict[str, "Dictionary"] = {}

    def __init__(self, lang: str, path: Path | None = None) -> None:
        self.lang = lang
        self.path = path or (DATA / f"dictionary_{lang}.tsv.gz")
        if not self.path.exists():
            raise FileNotFoundError(
                f"{lang} 사전이 없다: {self.path}\n"
                "  tools/build_dictionary.py 로 지어라."
            )
        self._by_key: dict[tuple[str, str], Entry] = {}
        self._by_form: dict[str, list[Entry]] = {}
        self._by_cell: dict[tuple[int, Quality], list[Entry]] = {}
        self._load()

    @classmethod
    def load(cls, lang: str) -> "Dictionary":
        if lang not in cls._cache:
            cls._cache[lang] = cls(lang)
        return cls._cache[lang]

    def _load(self) -> None:
        with gzip.open(self.path, "rt", encoding="utf-8", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t")
            next(rd)
            for form, tag, freq, rank, tier, pol, qual, index in rd:
                e = Entry(
                    form=form, tag=tag, freq=int(freq), rank=int(rank),
                    tier=int(tier), polarity=int(pol), quality=Quality(qual),
                    index=int(index), lang=self.lang,
                )
                self._by_key[(form, tag)] = e
                self._by_form.setdefault(form, []).append(e)
                cell = self._by_cell.setdefault(e.cell, [])
                assert len(cell) == e.index, (
                    f"칸 {e.cell} 의 번호가 이가 빠졌다: {len(cell)} ≠ {e.index}"
                )
                cell.append(e)

    # ── 앞으로: 낱말 → 번호 ─────────────────────────────────────────
    def get(self, form: str, tag: str) -> Entry | None:
        return self._by_key.get((form, tag))

    def find(self, form: str) -> list[Entry]:
        return sorted(self._by_form.get(form, []), key=lambda e: -e.freq)

    # ── 뒤로: 번호 → 낱말 ───────────────────────────────────────────
    def at(self, tier: int, quality: Quality, index: int) -> Entry | None:
        cell = self._by_cell.get((tier, quality))
        if cell is None or not 0 <= index < len(cell):
            return None
        return cell[index]

    def cell_size(self, tier: int, quality: Quality) -> int:
        return len(self._by_cell.get((tier, quality), ()))

    def __contains__(self, key) -> bool:
        return tuple(key) in self._by_key

    def __len__(self) -> int:
        return len(self._by_key)

    @property
    def entries(self):
        return self._by_key.values()
