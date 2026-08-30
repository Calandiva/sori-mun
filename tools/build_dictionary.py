#!/usr/bin/env python3
"""세 갈래 자료를 합쳐 낱말–프레이즈 사전을 만든다.

    표제어(mecab-ko-dic) + 빈도(말뭉치) + 극성(KNU)  →  프레이즈

축의 배정
────────
    협화도 = 빈도    흔한 낱말일수록 순한 화음, 드물수록 난해한 화음
    장·단  = 극성    긍정은 장(長) 관계, 부정은 단(短) 관계, 나머지는 중립
    길이   = 빈도    흔한 낱말일수록 짧은 음형

겹치지 않음
──────────
(등급 × 성질) 칸마다 쓰는 화음 모양이 서로소이고, 한 칸 안에서는
결정적 스트림에서 하나씩 떼어 쓴다. 그래서 사전 전체에서 프레이즈는
유일하다. tools/verify.py 가 실제로 확인한다.

내는 것
    data/dictionary.tsv.gz     낱말–프레이즈 사전 (zgrep 으로 훑을 수 있다)
    data/dictionary.meta.json  칸별 발급 수, 등급 경계 따위
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import pitch, tags as T  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402
from sorimun.core.markers import MARKER_TAGS, MarkerAllocator  # noqa: E402
from sorimun.core.phrase import PhraseAllocator, encode  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT_TSV = ROOT / "data" / "dictionary.tsv.gz"
OUT_META = ROOT / "data" / "dictionary.meta.json"

# ── 등급 경계: 순위 기준. 지프 분포에 맞춰 대수적으로 벌린다. ────────
# 일상어(0~3등급)는 잘게 나누고, 긴 꼬리는 4~5등급으로 몰아 둔다.
TIER_BANDS = (300, 1_500, 6_000, 25_000, 100_000)
TIER_LABEL = ("아주 흔함", "흔함", "보통", "드묾", "아주 드묾", "희귀·미등재")

NO_FREQ_COST = 9999  # 말뭉치에 없는 표제어의 기본 비용


def tier_of_rank(rank: int) -> int:
    for i, b in enumerate(TIER_BANDS):
        if rank <= b:
            return i
    return len(TIER_BANDS)


def quality_of_polarity(p: int) -> Quality:
    if p > 0:
        return Quality.MAJOR
    if p < 0:
        return Quality.MINOR
    return Quality.NEUTRAL


def read_tsv_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        yield from csv.reader(fh, delimiter="\t")


def main() -> int:
    # ── 읽기 ────────────────────────────────────────────────────────
    cost: dict[tuple[str, str], int] = {}
    for form, tag, c in read_tsv_gz(BUILD / "lexicon.tsv.gz"):
        cost[(form, tag)] = int(c)

    freq: dict[tuple[str, str], int] = {}
    for form, tag, n in read_tsv_gz(BUILD / "frequency.tsv.gz"):
        freq[(form, tag)] = int(n)

    pol: dict[tuple[str, str], int] = {}
    for form, tag, p, _w, _src in read_tsv_gz(BUILD / "sentiment.tsv.gz"):
        pol[(form, tag)] = int(p)

    # 표제어 목록과 말뭉치에 나온 형태소를 합친다. 분석기가 내놓는
    # 형태소인데 사전에 없으면 문장을 옮길 때 구멍이 나기 때문이다.
    keys = set(cost) | set(freq)
    keys = {(f, t) for (f, t) in keys if t not in T.SYMBOL}
    print(f"표제어 {len(cost):,} ∪ 말뭉치형태소 {len(freq):,} = {len(keys):,}")

    # ── 순위 ────────────────────────────────────────────────────────
    # 말뭉치 빈도 우선, 없으면 mecab 비용(낮을수록 흔함)으로 가른다.
    ordered = sorted(
        keys,
        key=lambda k: (-freq.get(k, 0), cost.get(k, NO_FREQ_COST), k[0], k[1]),
    )

    # ── 배정 ────────────────────────────────────────────────────────
    content = PhraseAllocator()
    marker = MarkerAllocator()
    rows = []
    tier_count = [0] * (len(TIER_BANDS) + 1)
    qual_count = {q: 0 for q in Quality}
    marker_count = 0

    for rank, key in enumerate(ordered, start=1):
        form, tag = key
        f = freq.get(key, 0)
        if tag in MARKER_TAGS:
            ph = marker.take(tag)
            tier, p, q, kind = -1, 0, "", "표지"
            marker_count += 1
        else:
            tier = tier_of_rank(rank)
            p = pol.get(key, 0)
            q = quality_of_polarity(p)
            ph = content.take(tier, q)
            tier_count[tier] += 1
            qual_count[q] += 1
            kind = "내용"
            q = q.value

        bottom = pitch.place(60, ph.ambitus)
        notes = " ".join(
            "+".join(pitch.name(x) for x in ps) for ps, _d, _r in ph.render(bottom)
        )
        rows.append(
            [form, tag, kind, f, rank, tier, p, q,
             ph.n_events, ph.ambitus, ph.length, encode(ph), notes]
        )

    # ── 쓰기 ────────────────────────────────────────────────────────
    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT_TSV, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["표제어", "품사", "갈래", "빈도", "순위", "등급",
                    "극성", "성질", "음형수", "폭", "길이", "프레이즈", "음이름"])
        w.writerows(rows)

    meta = {
        "판": 1,
        "항목수": len(rows),
        "표지수": marker_count,
        "등급경계": list(TIER_BANDS),
        "등급이름": list(TIER_LABEL),
        "등급별항목수": tier_count,
        "성질별항목수": {q.value: n for q, n in qual_count.items()},
        "칸별발급수": {f"{t}/{q.value}": n for (t, q), n in content.issued.items()},
        "표지별발급수": marker.issued,
        "음역": {"최저": pitch.LOWEST, "최고": pitch.HIGHEST,
                 "최저음이름": pitch.name(pitch.LOWEST),
                 "최고음이름": pitch.name(pitch.HIGHEST)},
    }
    OUT_META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"→ {OUT_TSV.relative_to(ROOT)} ({OUT_TSV.stat().st_size:,}B)")
    print(f"\n표지(조사·어미) {marker_count:,}개")
    print("등급별 내용어:")
    for i, n in enumerate(tier_count):
        print(f"  {i} {TIER_LABEL[i]:<14} {n:>8,}")
    print("성질별 내용어:", {q.value: n for q, n in qual_count.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
