#!/usr/bin/env python3
"""만들어진 사전이 규칙을 지키는지 실제로 확인한다.

  1. 겹침 없음   프레이즈가 두 낱말에 배정된 적이 없는가
  2. 음역        어떤 배치에서도 2옥타브를 벗어나지 않는가
  3. 갈래 분리   조사·어미와 내용어가 음가로 갈리는가
  4. 축 일치     극성↔성질, 순위↔등급 이 어긋난 항목이 없는가
"""

from __future__ import annotations

import csv
import gzip
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import pitch  # noqa: E402
from sorimun.core.markers import MARKER_TAGS  # noqa: E402
from sorimun.core.phrase import CONTENT_DURATIONS, MARKER_DURATION, decode  # noqa: E402

DICT = ROOT / "data" / "dictionary.tsv.gz"

TIER_BANDS = (300, 1_500, 6_000, 25_000, 100_000)


def tier_of_rank(rank: int) -> int:
    for i, b in enumerate(TIER_BANDS):
        if rank <= b:
            return i
    return len(TIER_BANDS)


def main() -> int:
    with gzip.open(DICT, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    print(f"항목 {len(rows):,}개 검사\n")
    fails = 0

    # ── 1. 겹침 없음 ────────────────────────────────────────────────
    seen: dict[tuple, tuple[str, str]] = {}
    dups = []
    for r in rows:
        ph = decode(r["프레이즈"], r["갈래"] == "표지")
        k = ph.key()
        if k in seen:
            dups.append((seen[k], (r["표제어"], r["품사"])))
        else:
            seen[k] = (r["표제어"], r["품사"])
    if dups:
        fails += 1
        print(f"✗ 겹침 {len(dups):,}쌍")
        for a, b in dups[:5]:
            print(f"    {a} ↔ {b}")
    else:
        print(f"✓ 겹침 없음 — {len(seen):,}개 프레이즈가 모두 다르다")

    # ── 2. 음역 ─────────────────────────────────────────────────────
    # 배치 가능한 모든 자리에 놓아 보고 2옥타브를 벗어나는지 본다.
    bad = 0
    worst = 0
    for r in rows:
        ph = decode(r["프레이즈"])
        worst = max(worst, ph.ambitus)
        lo, hi = pitch.placement_window(ph.ambitus)
        if hi < lo:
            bad += 1
            continue
        for bottom in (lo, (lo + hi) // 2, hi):
            try:
                ph.render(bottom)
            except ValueError:
                bad += 1
                break
    if bad:
        fails += 1
        print(f"✗ 음역 이탈 {bad:,}개")
    else:
        print(f"✓ 음역 — 모든 항목이 {pitch.name(pitch.LOWEST)}~{pitch.name(pitch.HIGHEST)} "
              f"(2옥타브) 안. 최대 폭 {worst}반음")

    # ── 3. 갈래 분리 ────────────────────────────────────────────────
    leak = 0
    for r in rows:
        ph = decode(r["프레이즈"])
        durs = {e.duration for e in ph.events}
        if r["갈래"] == "표지":
            if durs != {MARKER_DURATION} or r["품사"] not in MARKER_TAGS:
                leak += 1
        else:
            if MARKER_DURATION in durs or not durs <= set(CONTENT_DURATIONS):
                leak += 1
    if leak:
        fails += 1
        print(f"✗ 갈래 분리 위반 {leak:,}개")
    else:
        print(f"✓ 갈래 분리 — 16분음표는 조사·어미 전용, 내용어에는 없다")

    # ── 4. 축 일치 ──────────────────────────────────────────────────
    mismatch_q = mismatch_t = 0
    for r in rows:
        if r["갈래"] != "내용":
            continue
        p = int(r["극성"])
        want = "major" if p > 0 else "minor" if p < 0 else "neutral"
        if r["성질"] != want:
            mismatch_q += 1
        if int(r["등급"]) != tier_of_rank(int(r["순위"])):
            mismatch_t += 1
    if mismatch_q or mismatch_t:
        fails += 1
        print(f"✗ 축 어긋남 — 극성↔성질 {mismatch_q}, 순위↔등급 {mismatch_t}")
    else:
        print("✓ 축 일치 — 긍정=장, 부정=단, 중립=중성 / 순위=등급")

    # ── 통계 ────────────────────────────────────────────────────────
    print("\n── 얼마나 다르게 들리는가 ──")
    pitchset = Counter()
    by_tier = defaultdict(Counter)
    for r in rows:
        pitchset[r["음이름"]] += 1
        by_tier[r["등급"]][r["음이름"]] += 1
    print(f"  서로 다른 음높이 배열: {len(pitchset):,}가지 / 항목 {len(rows):,}개")
    print("  (같은 음높이 배열이라도 음가·쉼표가 달라 프레이즈는 유일하다)")
    ev = Counter(len(r["프레이즈"].split("|")) for r in rows)
    print(f"  음형 개수 분포: {dict(sorted(ev.items()))}")
    print("  등급별 음높이 배열 가짓수:")
    for t in sorted(by_tier, key=lambda x: int(x)):
        n = sum(by_tier[t].values())
        print(f"    등급 {t:>2}: {len(by_tier[t]):>6,}가지 / {n:>7,}항목")

    print()
    if fails:
        print(f"실패 {fails}건")
        return 1
    print("모든 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
