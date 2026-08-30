#!/usr/bin/env python3
"""mecab-ko-dic CSV 를 표제어 목록으로 간추린다.

내는 것: data/build/lexicon.tsv.gz
    표제어 <TAB> 품사 <TAB> mecab비용

mecab 의 '비용(cost)' 은 말뭉치 통계에서 나온 값으로 낮을수록 흔하다.
말뭉치 빈도가 없는 표제어의 대체 빈도로 쓴다.
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

RAW = ROOT / "data" / "raw" / "mecab"
OUT = ROOT / "data" / "build" / "lexicon.tsv.gz"

# 한 글자짜리 자모 조각은 표제어로 치지 않는다 (ㄱ, ㅣㅆ 같은 것들).
BARE_JAMO = set("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")


def usable(form: str, tag: str) -> bool:
    if not form:
        return False
    # 자모 한 글자만인 표제어는 버린다.
    if len(form) == 1 and form in BARE_JAMO:
        return False
    # 결합형 자모(ᆫ, ᆯ …)로 시작하는 것은 조사·어미에서만 유효한 이형태다.
    if form[0] in "ᆨᆩᆪᆫᆬᆭᆮᆯᆰᆱᆲᆳᆴᆵᆶᆷᆸᆹᆺᆻᆼᆽᆾᆿᇀᇁᇂ":
        return tag in T.GRAMMATICAL
    return True


def main() -> int:
    best: dict[tuple[str, str], int] = {}
    seen_files = 0
    for path in sorted(RAW.glob("*.csv")):
        seen_files += 1
        with path.open(encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if len(row) < 5:
                    continue
                form, cost, tag = row[0], row[3], T.normalize(row[4])
                if not usable(form, tag):
                    continue
                try:
                    c = int(cost)
                except ValueError:
                    continue
                k = (form, tag)
                # 같은 (표제어, 품사)가 문맥ID별로 여러 줄 있다. 가장 낮은
                # 비용 = 가장 흔한 쓰임을 대표값으로 삼는다.
                if k not in best or c < best[k]:
                    best[k] = c

    OUT.parent.mkdir(parents=True, exist_ok=True)
    by_tag: defaultdict[str, int] = defaultdict(int)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        for (form, tag), cost in sorted(best.items()):
            w.writerow([form, tag, cost])
            by_tag[tag] += 1

    print(f"CSV {seen_files}개 → 표제어 {len(best):,}개")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print("\n품사별:")
    for tag, n in sorted(by_tag.items(), key=lambda kv: -kv[1]):
        print(f"  {tag:<6} {T.KOREAN_NAME.get(tag,'?'):<12} {n:>8,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
