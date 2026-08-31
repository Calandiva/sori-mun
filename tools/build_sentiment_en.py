#!/usr/bin/env python3
"""영어 감정 극성.

    VADER (MIT)   7,520 낱말, -4 ~ +4
    AFINN-165     3,382 낱말, -5 ~ +5

둘을 각각 [-1,1] 로 고른 뒤 평균내고 -2 ~ +2 로 옮긴다. 두 사전이
어긋나면 평균이 0 쪽으로 당겨져 저절로 중립이 된다.

굴절형에도 물려준다 — loved / loving / loves 는 love 의 극성을 받는다.
영어 사전은 표면형을 싣기 때문에 이 걸음이 없으면 굴절형이 모두
중립이 되어 버린다.

내는 것: data/build/sentiment_en.tsv.gz   낱말 <TAB> 극성 <TAB> 출처
"""

from __future__ import annotations

import csv
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RAW = ROOT / "data" / "raw"
LEX = ROOT / "data" / "build" / "lexicon_en.tsv.gz"
OUT = ROOT / "data" / "build" / "sentiment_en.tsv.gz"

T1, T2 = 0.20, 0.55


def read_vader() -> dict[str, float]:
    out = {}
    with (RAW / "vader_lexicon.txt").open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            w = parts[0].strip().lower()
            if not w.isalpha():
                continue
            try:
                out[w] = float(parts[1]) / 4.0
            except ValueError:
                continue
    return out


def read_afinn() -> dict[str, float]:
    out = {}
    with (RAW / "afinn_165.txt").open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 2:
                continue
            w = parts[0].strip().lower()
            if not w.isalpha():
                continue
            try:
                out[w] = float(parts[1]) / 5.0
            except ValueError:
                continue
    return out


def bucket(x: float) -> int:
    if x >= T2:
        return 2
    if x >= T1:
        return 1
    if x <= -T2:
        return -2
    if x <= -T1:
        return -1
    return 0


# 굴절 되돌리기 — 사전에 있는 밑말을 찾는다.
def bases(word: str):
    w = word
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y"
    for suf, cut in (("s", 1), ("es", 2), ("ed", 2), ("ing", 3),
                     ("er", 2), ("est", 3), ("ly", 2)):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            stem = w[: -cut]
            yield stem
            if suf in ("ed", "ing", "er", "est"):
                yield stem + "e"                 # loved → love
                if len(stem) > 2 and stem[-1] == stem[-2]:
                    yield stem[:-1]              # stopped → stop


def main() -> int:
    v, a = read_vader(), read_afinn()
    direct: dict[str, float] = {}
    for w in set(v) | set(a):
        vals = [x[w] for x in (v, a) if w in x]
        direct[w] = sum(vals) / len(vals)
    print(f"VADER {len(v):,} + AFINN {len(a):,} → 밑말 {len(direct):,}")

    words = set()
    with gzip.open(LEX, "rt", encoding="utf-8") as fh:
        for w, _t, _n in csv.reader(fh, delimiter="\t"):
            words.add(w)

    rows, n_direct, n_infl = [], 0, 0
    for w in sorted(words):
        if w in direct:
            p = bucket(direct[w])
            if p:
                rows.append([w, p, "직접"])
                n_direct += 1
            continue
        for b in bases(w):
            if b in direct:
                p = bucket(direct[b])
                if p:
                    rows.append([w, p, f"굴절←{b}"])
                    n_infl += 1
                break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)

    from collections import Counter
    dist = Counter(r[1] for r in rows)
    print(f"극성 부여 {len(rows):,} (직접 {n_direct:,}, 굴절 {n_infl:,})")
    print(f"분포 {dict(sorted(dist.items()))} → {OUT.relative_to(ROOT)}")
    idx = {r[0]: r[1] for r in rows}
    print("\n표본:", {w: idx.get(w, 0) for w in
        ["love","loved","hate","hated","beautiful","dark","death","happy",
         "sings","song","night","the","is","slowly"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
