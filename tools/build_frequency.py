#!/usr/bin/env python3
"""어절 빈도 목록을 형태소 빈도로 다시 집계한다.

원본(FrequencyWords/OpenSubtitles)은 '내가 39801' 처럼 어절 단위다.
이 상태로는 '내'(대명사)와 '가'(주격조사)의 빈도를 알 수 없다.
그래서 각 어절을 형태소로 쪼갠 뒤 그 어절의 출현수를 구성 형태소
모두에 더한다.

내는 것: data/build/frequency.tsv.gz
    표제어 <TAB> 품사 <TAB> 말뭉치빈도
"""

from __future__ import annotations

import csv
import gzip
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import tags as T  # noqa: E402

SRC = ROOT / "data" / "raw" / "frequency_ko.txt"
OUT = ROOT / "data" / "build" / "frequency.tsv.gz"

BATCH = 20000


def read_pairs(path: Path) -> list[tuple[str, int]]:
    pairs = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 2:
                continue
            try:
                pairs.append((parts[0], int(parts[1])))
            except ValueError:
                continue
    return pairs


def main() -> int:
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("kiwipiepy 가 필요하다:  pip install kiwipiepy", file=sys.stderr)
        return 1

    pairs = read_pairs(SRC)
    print(f"어절 {len(pairs):,}개 읽음")

    kiwi = Kiwi(num_workers=-1)
    freq: defaultdict[tuple[str, str], int] = defaultdict(int)

    done = 0
    for start in range(0, len(pairs), BATCH):
        chunk = pairs[start:start + BATCH]
        for (surface, count), tokens in zip(chunk, kiwi.tokenize(w for w, _ in chunk)):
            for tok in tokens:
                tag = T.normalize(tok.tag)
                if tag in T.SYMBOL:
                    continue
                freq[(tok.form, tag)] += count
        done += len(chunk)
        print(f"\r  분석 {done:,}/{len(pairs):,}", end="", flush=True)
    print()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        for (form, tag), n in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])):
            w.writerow([form, tag, n])

    print(f"형태소 {len(freq):,}종 → {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print("\n최빈 20:")
    top = sorted(freq.items(), key=lambda kv: -kv[1])[:20]
    for (form, tag), n in top:
        print(f"  {form:<6} {tag:<5} {T.KOREAN_NAME.get(tag,'?'):<10} {n:>10,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
