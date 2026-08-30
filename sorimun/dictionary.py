"""사전 — 낱말에서 프레이즈로.

data/dictionary.tsv 를 읽어 (표제어, 품사) 로 찾는다. 사전에 없는
낱말은 정해진 규칙으로 즉석에서 음형을 만든다.

미등재어
    등급 5(가장 난해), 성질 중립, 그리고 화음 4개짜리 긴 음형을 받는다.
    사전에 실린 낱말은 최대 3개까지만 쓰므로 음형 개수만으로 이미
    갈린다. 모르는 말은 길고 낯설게 울린다.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .core import tags as T
from .core.harmony import Quality, shape_table
from .core.phrase import (
    CONTENT_DURATIONS,
    OOV_EVENTS,
    Phrase,
    decode,
    encode,
    phrase_at_index,
)

_DATA = Path(__file__).resolve().parent.parent / "data"
# 저장소에는 눌러서 싣는다. 풀어 둔 것이 있으면 그쪽을 먼저 쓴다.
DEFAULT_CANDIDATES = (_DATA / "dictionary.tsv", _DATA / "dictionary.tsv.gz")


def default_path() -> Path:
    for p in DEFAULT_CANDIDATES:
        if p.exists():
            return p
    return DEFAULT_CANDIDATES[1]

OOV_TIER = 5


@dataclass(slots=True)
class Entry:
    """사전 항목 하나.

    프레이즈는 문자열로 들고 있다가 처음 쓸 때 푼다. 28만 항목을
    모두 풀어 두면 적재가 느려지는데, 한 문장이 건드리는 것은
    몇 개뿐이기 때문이다.
    """

    form: str
    tag: str
    kind: str          # '내용' 또는 '표지'
    freq: int
    rank: int
    tier: int          # 표지는 -1
    polarity: int      # -2 ~ +2
    quality: str       # major / minor / neutral, 표지는 ''
    code: str          # 직렬화된 프레이즈
    known: bool = True
    _phrase: Phrase | None = None

    @property
    def phrase(self) -> Phrase:
        if self._phrase is None:
            self._phrase = decode(self.code, self.kind == "표지")
        return self._phrase

    @property
    def tag_name(self) -> str:
        return T.KOREAN_NAME.get(self.tag, self.tag)

    @property
    def is_marker(self) -> bool:
        return self.kind == "표지"


class Dictionary:
    """낱말–프레이즈 사전."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_path()
        if not self.path.exists():
            raise FileNotFoundError(
                f"사전이 없다: {self.path}\n"
                "  tools/fetch_data.py → build_lexicon.py → build_frequency.py\n"
                "  → build_sentiment.py → build_dictionary.py 순으로 만들어라."
            )
        self._by_key: dict[tuple[str, str], Entry] = {}
        self._by_form: dict[str, list[Entry]] = {}
        self._load()

    def _load(self) -> None:
        opener = (
            (lambda: gzip.open(self.path, "rt", encoding="utf-8", newline=""))
            if self.path.suffix == ".gz"
            else (lambda: self.path.open(encoding="utf-8", newline=""))
        )
        with opener() as fh:
            rd = csv.reader(fh, delimiter="\t")
            header = next(rd)
            col = {name: i for i, name in enumerate(header)}
            iF, iT = col["표제어"], col["품사"]
            iK, iQ = col["갈래"], col["성질"]
            iN, iR, iL, iP = col["빈도"], col["순위"], col["등급"], col["극성"]
            iC = col["프레이즈"]
            for row in rd:
                e = Entry(
                    form=row[iF], tag=row[iT], kind=row[iK],
                    freq=int(row[iN]), rank=int(row[iR]),
                    tier=int(row[iL]), polarity=int(row[iP]),
                    quality=row[iQ], code=row[iC],
                )
                self._by_key[(e.form, e.tag)] = e
                self._by_form.setdefault(e.form, []).append(e)

    # ── 찾기 ────────────────────────────────────────────────────────
    def get(self, form: str, tag: str) -> Entry:
        """(표제어, 품사) 로 찾는다. 없으면 미등재어 규칙을 쓴다."""
        tag = T.normalize(tag)
        e = self._by_key.get((form, tag))
        if e is not None:
            return e
        return self._unknown(form, tag)

    def find(self, form: str) -> list[Entry]:
        """표제어로 찾는다. 품사가 여럿이면 모두 낸다 (빈도 순)."""
        return sorted(self._by_form.get(form, []), key=lambda e: -e.freq)

    def __contains__(self, key: tuple[str, str]) -> bool:
        return (key[0], T.normalize(key[1])) in self._by_key

    def __len__(self) -> int:
        return len(self._by_key)

    @property
    def entries(self):
        return self._by_key.values()

    # ── 미등재어 ────────────────────────────────────────────────────
    @staticmethod
    @lru_cache(maxsize=4096)
    def _oov_phrase(form: str, tag: str) -> Phrase:
        shapes = shape_table()[(OOV_TIER, Quality.NEUTRAL)]
        h = hashlib.blake2b(f"{form}/{tag}".encode(), digest_size=8).digest()
        return phrase_at_index(
            shapes, CONTENT_DURATIONS, OOV_EVENTS, int.from_bytes(h, "big")
        )

    def _unknown(self, form: str, tag: str) -> Entry:
        ph = self._oov_phrase(form, tag)
        return Entry(
            form=form, tag=tag, kind="내용", freq=0, rank=0,
            tier=OOV_TIER, polarity=0, quality=Quality.NEUTRAL.value,
            code=encode(ph), known=False, _phrase=ph,
        )
