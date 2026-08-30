#!/usr/bin/env python3
"""KNU 한국어 감성사전을 형태소 단위 극성으로 옮긴다.

원본 표제어는 '가치있는', '눈물을 흘리다' 처럼 구(句)나 활용형이 섞여
있어 형태소 사전과 바로 맞물리지 않는다. 그래서 표제어를 쪼갠 뒤
내용 형태소들에 극성을 나눠 싣고 모아서 평균낸다.

그냥 평균내면 안 되는 이유
──────────────────────
KNU 는 부정 쪽으로 크게 치우쳐 있다 (부정 9,829 : 긍정 4,871).
그래서 '하', '사람', '일' 처럼 긍·부정 양쪽 표제어에 두루 나오는
형태소가 그 편향을 그대로 물려받아 -1 이 되어 버린다. 두 가지로 막는다.

  중심화   전체 평균 극성을 빼서 편향을 없앤다. 널리 퍼진 형태소는
           0 근처로 모이고, 한쪽에 쏠린 형태소만 극성이 남는다.
  일관성   표의 방향이 갈리면 극성을 주지 않는다. 같은 부호가
           일정 비율을 넘어야 인정한다.

마지막으로 data/sentiment_overrides.tsv 의 손질 값이 덮어쓴다.

내는 것: data/build/sentiment.tsv.gz
    표제어 <TAB> 품사 <TAB> 극성(-2~2) <TAB> 증거무게 <TAB> 출처
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

from sorimun.core import tags as T  # noqa: E402

SRC = ROOT / "data" / "raw" / "knu_sentiment.json"
OVERRIDES = ROOT / "data" / "sentiment_overrides.tsv"
OUT = ROOT / "data" / "build" / "sentiment.tsv.gz"

BEARING = T.SUBSTANTIVE | T.PREDICATE | {"MAG", "MAJ", "IC", "XR"}

MIN_WEIGHT = 0.9      # 이만큼의 증거는 있어야 극성을 준다
MIN_AGREEMENT = 0.62  # 표의 방향이 이만큼은 한쪽으로 모여야 한다
T1, T2 = 0.55, 1.45   # 중심화된 가중평균의 ±1 / ±2 문턱


def load_overrides() -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    if not OVERRIDES.exists():
        return out
    for line in OVERRIDES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        out[(parts[0], parts[1])] = int(parts[2])
    return out


def main() -> int:
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("kiwipiepy 가 필요하다:  pip install kiwipiepy", file=sys.stderr)
        return 1

    entries = json.loads(SRC.read_text(encoding="utf-8"))
    pols = []
    for e in entries:
        try:
            pols.append(int(e["polarity"]))
        except (ValueError, KeyError):
            pols.append(0)

    bias = sum(pols) / len(pols)
    print(f"KNU 항목 {len(entries):,}개, 전체 평균 극성 {bias:+.4f} (이만큼 중심화)")

    kiwi = Kiwi(num_workers=-1)
    # [극성합, 무게합, 양(+)무게, 음(-)무게]
    acc: defaultdict[tuple[str, str], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0, 0.0]
    )

    skipped = 0
    for pol, tokens in zip(pols, kiwi.tokenize(e["word"] for e in entries)):
        content = [
            (t.form, T.normalize(t.tag))
            for t in tokens
            if T.normalize(t.tag) in BEARING
        ]
        if not content:
            skipped += 1
            continue
        centered = pol - bias
        w = 1.0 / len(content)   # 짧은 표제어일수록 직접 증거다
        for key in content:
            a = acc[key]
            a[0] += centered * w
            a[1] += w
            if centered > 0:
                a[2] += w
            elif centered < 0:
                a[3] += w

    rows = []
    dist: defaultdict[int, int] = defaultdict(int)
    rejected_agreement = 0
    for (form, tag), (s, w, wp, wn) in acc.items():
        if w < MIN_WEIGHT:
            continue
        mean = s / w
        signed = wp if mean > 0 else wn
        agreement = signed / (wp + wn) if (wp + wn) else 0.0
        if agreement < MIN_AGREEMENT:
            rejected_agreement += 1
            continue
        if mean >= T2:
            p = 2
        elif mean >= T1:
            p = 1
        elif mean <= -T2:
            p = -2
        elif mean <= -T1:
            p = -1
        else:
            p = 0
        if p == 0:
            continue
        rows.append([form, tag, p, round(w, 3), "knu"])
        dist[p] += 1

    # 손질 값이 마지막에 덮어쓴다.
    ov = load_overrides()
    idx = {(r[0], r[1]): r for r in rows}
    n_fixed = n_added = n_cleared = 0
    for (form, tag), p in ov.items():
        r = idx.get((form, tag))
        if p == 0:
            if r is not None:
                rows.remove(r)
                dist[r[2]] -= 1
                n_cleared += 1
            continue
        if r is None:
            row = [form, tag, p, 999.0, "손질"]
            rows.append(row)
            idx[(form, tag)] = row
            dist[p] += 1
            n_added += 1
        else:
            if r[2] != p:
                dist[r[2]] -= 1
                dist[p] += 1
                n_fixed += 1
            r[2], r[4] = p, "손질"

    rows.sort(key=lambda r: (-r[3], r[0]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerows(rows)

    print(f"내용 형태소 없어 건너뜀 {skipped:,} / 일관성 미달로 기각 {rejected_agreement:,}")
    print(f"손질: 중립복원 {n_cleared}, 값교정 {n_fixed}, 신규 {n_added}")
    print(f"극성 부여 {len(rows):,}개  분포 {dict(sorted(dist.items()))}")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")

    check = {(r[0], r[1]): r[2] for r in rows}
    print("\n표본 확인 (중립이어야 할 것 / 극성이 있어야 할 것):")
    for probe in [("하","VV"),("사람","NNG"),("일","NNG"),("되","VV"),("모양","NNG"),
                  ("있","VA"),None,
                  ("사랑","NNG"),("아름답","VA"),("행복","NNG"),("밝","VA"),
                  ("슬프","VA"),("어둡","VA"),("죽음","NNG"),("고통","NNG"),("나쁘","VA")]:
        if probe is None:
            print("  " + "─"*40); continue
        v = check.get(probe)
        print(f"  {probe[0]:<6}/{probe[1]:<4} {'중립' if v is None else f'{v:+d}'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
