#!/usr/bin/env python3
"""낱말 사전을 짓는다 — 한국어와 영어.

한 낱말은 (등급, 성질) 칸 안의 번호 하나로 줄어든다. 글리프는 그 셋을
적고, 되읽기는 그 셋으로 낱말을 되찾는다.

    등급 ← 사용 빈도    흔할수록 순한 화음, 드물수록 난해한 화음
    성질 ← 감정 극성    긍정은 장, 부정은 단, 나머지는 중성
    번호 ← 칸 안의 순위 흔한 낱말이 앞 번호를 받아 이름이 짧아진다

겹치지 않음
    (언어, 등급, 성질, 번호) → 낱말 이 일대일이고, 글리프는 그 넷을
    고스란히 적는다. 그러므로 서로 다른 낱말은 반드시 다른 글리프를
    갖는다. 검사로 얻는 성질이 아니라 구성상 따라 나온다.

내는 것
    data/dictionary_ko.tsv.gz
    data/dictionary_en.tsv.gz
    data/dictionary.meta.json
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import codes as C  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data"

# 등급 경계 — 순위 기준. 지프 분포에 맞춰 대수적으로 벌린다.
# 두 언어가 같은 잣대를 쓰므로 '아주 흔함' 이 양쪽에서 같은 뜻이다.
TIER_BANDS = (300, 1_500, 6_000, 25_000, 100_000)
TIER_LABEL = ("아주 흔함", "흔함", "보통", "드묾", "아주 드묾", "희귀·미등재")
TIER_LABEL_EN = ("very common", "common", "ordinary", "uncommon",
                 "rare", "very rare")

HEADER = ["표제어", "품사", "빈도", "순위", "등급", "극성", "성질", "번호"]


def tier_of_rank(rank: int) -> int:
    for i, b in enumerate(TIER_BANDS):
        if rank <= b:
            return i
    return len(TIER_BANDS)


def quality_of(p: int) -> Quality:
    return Quality.MAJOR if p > 0 else Quality.MINOR if p < 0 else Quality.NEUTRAL


def read_tsv_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        yield from csv.reader(fh, delimiter="\t")


# ── 언어별 재료 모으기 ───────────────────────────────────────────────
def gather_ko() -> list[tuple[str, str, int, int]]:
    """(표제어, 품사, 빈도, 극성)"""
    cost = {(f, t): int(c) for f, t, c in read_tsv_gz(BUILD / "lexicon.tsv.gz")}
    freq = {(f, t): int(n) for f, t, n in read_tsv_gz(BUILD / "frequency.tsv.gz")}
    pol = {(f, t): int(p) for f, t, p, _w, _s in read_tsv_gz(BUILD / "sentiment.tsv.gz")}

    keys = set(cost) | set(freq)
    ordered = sorted(keys, key=lambda k: (-freq.get(k, 0), cost.get(k, 9999), k))
    return [(f, t, freq.get((f, t), 0), pol.get((f, t), 0)) for f, t in ordered]


def gather_en() -> list[tuple[str, str, int, int]]:
    lex = [(w, t, int(n)) for w, t, n in read_tsv_gz(BUILD / "lexicon_en.tsv.gz")]
    pol = {w: int(p) for w, p, _s in read_tsv_gz(BUILD / "sentiment_en.tsv.gz")}
    ordered = sorted(lex, key=lambda r: (-r[2], r[0], r[1]))
    return [(w, t, n, pol.get(w, 0)) for w, t, n in ordered]


def build(lang: str, rows: list[tuple[str, str, int, int]]) -> dict:
    """순위를 매기고, 칸마다 번호를 붙인다."""
    counter: defaultdict[tuple[int, str], int] = defaultdict(int)
    out = []
    tier_count = [0] * (len(TIER_BANDS) + 1)
    qual_count: defaultdict[str, int] = defaultdict(int)
    max_index = 0

    for rank, (form, tag, freq, pol) in enumerate(rows, start=1):
        tier = tier_of_rank(rank)
        q = quality_of(pol)
        cell = (tier, q.value)
        index = counter[cell]
        counter[cell] += 1
        max_index = max(max_index, index)
        out.append([form, tag, freq, rank, tier, pol, q.value, index])
        tier_count[tier] += 1
        qual_count[q.value] += 1

    # 자릿수는 위로 열려 있다 (전단사 32진법). 4자리면 백만이 넘는다.
    limit = C.capacity(4)
    if max_index >= limit:
        raise RuntimeError(
            f"{lang}: 최대 번호 {max_index:,} 가 4자리 한계 {limit:,} 를 넘었다")

    path = OUT / f"dictionary_{lang}.tsv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(out)

    # 이름이 몇 자리가 되는지
    digit_hist: defaultdict[int, int] = defaultdict(int)
    for r in out:
        digit_hist[len(C.digits_of(r[7]))] += 1

    print(f"\n[{lang}] 항목 {len(out):,}  최대 번호 {max_index:,} "
          f"(한계 {limit:,})")
    print(f"  → {path.relative_to(ROOT)} ({path.stat().st_size:,}B)")
    print("  등급별: " + "  ".join(
        f"{i}:{n:,}" for i, n in enumerate(tier_count)))
    print("  성질별: " + "  ".join(f"{k}:{v:,}" for k, v in qual_count.items()))
    print("  이름 자릿수: " + "  ".join(
        f"{k}자리 {v:,}" for k, v in sorted(digit_hist.items())))
    print("  글리프 길이(화음 수): " + "  ".join(
        f"{k+2}개 {v:,}" for k, v in sorted(digit_hist.items())))
    return {
        "항목수": len(out), "최대번호": max_index,
        "등급별": tier_count, "성질별": dict(qual_count),
        "자릿수별": {str(k): v for k, v in sorted(digit_hist.items())},
    }


def main() -> int:
    meta = {
        "판": 2,
        "진법": C.BASE,
        "담을수있는번호_4자리": C.capacity(4),
        "등급경계": list(TIER_BANDS),
        "등급이름": list(TIER_LABEL),
        "등급이름_en": list(TIER_LABEL_EN),
        "언어": {},
    }
    meta["언어"]["ko"] = build("ko", gather_ko())
    meta["언어"]["en"] = build("en", gather_en())
    (OUT / "dictionary.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {(OUT / 'dictionary.meta.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
