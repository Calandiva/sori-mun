#!/usr/bin/env python3
"""영어 표제어와 품사를 간추린다.

    Moby Part-of-Speech (public domain)   표제어와 품사
    FrequencyWords / OpenSubtitles        빈도

영어는 낱말이 곧 표면형이다. 한국어처럼 형태소로 쪼개지 않고 나타난
꼴 그대로 사전에 싣는다. 그래야 되읽을 때 원문이 정확히 돌아온다
(love / loves / loved 는 각각 다른 항목이다).

내는 것: data/build/lexicon_en.tsv.gz   낱말 <TAB> 품사 <TAB> 빈도
"""

from __future__ import annotations

import csv
import gzip
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.lang import tags_en as E  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "build" / "lexicon_en.tsv.gz"

WORD = re.compile(r"^[a-z][a-z'\-]*$")
MIN_FREQ = 3          # 말뭉치에 이보다 적게 나온 낱말은 싣지 않는다
MAX_ENTRIES = 260_000  # 한국어 사전과 규모를 맞춘다


def load_moby() -> dict[str, set[str]]:
    tags: dict[str, set[str]] = defaultdict(set)
    with (RAW / "pos_en.txt").open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "\t" not in line:
                continue
            word, codes = line.rstrip("\n").split("\t", 1)
            word = word.strip().lower()
            if not WORD.match(word):
                continue      # 여러 낱말로 된 표제어와 기호는 뺀다
            for c in codes:
                t = E.MOBY.get(c)
                if t:
                    tags[word].add(t)
    return tags


def load_freq() -> dict[str, int]:
    freq: dict[str, int] = {}
    with (RAW / "frequency_en.txt").open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 2:
                continue
            w = parts[0].lower()
            if not WORD.match(w):
                continue
            try:
                n = int(parts[1])
            except ValueError:
                continue
            if n >= MIN_FREQ:
                freq[w] = freq.get(w, 0) + n
    return freq


def main() -> int:
    moby = load_moby()
    freq = load_freq()
    print(f"Moby 표제어 {len(moby):,} / 말뭉치 낱말 {len(freq):,}")

    def known(stem: str) -> set[str]:
        return moby.get(stem, set())

    rows: list[tuple[str, str, int]] = []
    for word in set(moby) | set(freq):
        n = freq.get(word, 0)
        closed = E.CLOSED.get(word)
        if closed:
            tags = {closed}
            # 'there' 처럼 두 얼굴을 가진 낱말은 열린 품사도 함께 남긴다
            if word in ("there", "that", "as", "since", "like", "no", "so"):
                tags |= moby.get(word, set())
        else:
            tags = set(moby.get(word, set()))
            # 굴절형의 잃어버린 읽기를 되살린다 (touched 는 동사이기도 하다)
            tags |= E.derive(word, known)
            if not tags:
                tags = {_guess(word)}
        for t in tags:
            rows.append((word, t, n))

    # 빈도가 높은 쪽부터 남긴다
    rows.sort(key=lambda r: (-r[2], r[0], r[1]))
    if len(rows) > MAX_ENTRIES:
        print(f"  {len(rows):,} → 상위 {MAX_ENTRIES:,} 만 남긴다")
        rows = rows[:MAX_ENTRIES]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)

    by_tag: defaultdict[str, int] = defaultdict(int)
    for _w, t, _n in rows:
        by_tag[t] += 1
    print(f"항목 {len(rows):,} → {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    for t, c in sorted(by_tag.items(), key=lambda kv: -kv[1]):
        print(f"  {t:<5}{E.KOREAN_NAME.get(t,'?'):<10}{c:>8,}")
    return 0


def _guess(word: str) -> str:
    for suf, tag in E.SUFFIX:
        if word.endswith(suf) and len(word) > len(suf) + 2:
            return tag
    return E.NN


if __name__ == "__main__":
    sys.exit(main())
