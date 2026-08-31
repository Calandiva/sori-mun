#!/usr/bin/env python3
"""두 축의 조화 검증 — 언어적으로, 음악적으로.

주장 1 (음악):  같은 성질 안에서 등급이 오를수록 불협화도가 단조 증가한다.
                '흔함 = 익숙한 화음' 이 실제 음향으로 성립하는가.
주장 2 (음악):  장/단/중성 화음이 음악 이론대로 판별된다.
                장은 장3도 관계, 단은 단3도 관계, 중성은 3도 없음.
주장 3 (직교):  네 사분면(흔함×장, 흔함×단, 드묾×장, 드묾×단)이 모두
                실제 낱말로 채워져 있고, 각각 다른 화음을 받는다.
주장 4 (언어):  등급이 실제 말뭉치 빈도와 단조 대응한다 (지프 법칙).
주장 5 (언어):  극성 부여가 원본 감성사전과 일치한다.
"""

from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import pitch  # noqa: E402
from sorimun.core.banks import BANKS  # noqa: E402
from sorimun.core.harmony import Quality, dissonance, quality  # noqa: E402
from sorimun.dictionary import Dictionary, TIER_LABEL  # noqa: E402

FAIL = 0


def check(ok, label, detail=""):
    global FAIL
    if ok:
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}" + (f"\n      {detail}" if detail else ""))


def main() -> int:
    print("═" * 66)
    print("주장 1 — 같은 성질 안에서 등급↑ = 불협화도↑ (익숙함의 축)")
    mono_ok = True
    for q in Quality:
        ds = [dissonance(BANKS.meaning[(t, q)].voicing) for t in range(6)]
        mono = all(a < b for a, b in zip(ds, ds[1:]))
        mono_ok &= mono
        row = " → ".join(f"{d:.3f}" for d in ds)
        print(f"    {q.value:<8} {row}   {'단조증가 ✓' if mono else '단조 아님 ✗'}")
    check(mono_ok, "세 성질 모두에서 의미 화음의 불협화도가 등급을 따라 단조 증가")

    spread_ok = True
    for q in Quality:
        lo = dissonance(BANKS.meaning[(0, q)].voicing)
        hi = dissonance(BANKS.meaning[(5, q)].voicing)
        if hi / max(lo, 1e-9) < 2.0:
            spread_ok = False
    check(spread_ok, "0등급과 5등급의 거칢 차이가 2배 이상 — 귀로 구별된다")

    # 자릿 화음도 성질을 지킨다
    dq_ok = all(quality(sh.voicing) is q
                for q in Quality for sh in BANKS.digit[q])
    check(dq_ok, "자릿 화음(이름을 적는 소리)도 제 성질을 지킨다 — "
                 "긍정어는 이름 내내 장으로 울린다")

    print("\n주장 2 — 장/단/중성이 음악 이론대로 판별되는가")
    theory = [
        ((0, 4, 7), Quality.MAJOR, "장3화음"),
        ((0, 3, 8), Quality.MAJOR, "장3화음 1전위"),
        ((0, 5, 9), Quality.MAJOR, "장3화음 2전위"),
        ((0, 3, 7), Quality.MINOR, "단3화음"),
        ((0, 4, 9), Quality.MINOR, "단3화음 1전위"),
        ((0, 3, 6), Quality.MINOR, "감3화음(단 계열)"),
        ((0, 7), Quality.NEUTRAL, "완전5도"),
        ((0, 5, 10), Quality.NEUTRAL, "4도쌓기"),
        ((0, 2, 7), Quality.NEUTRAL, "sus2"),
        ((0, 4, 8), Quality.NEUTRAL, "증3화음(대칭 — 어느 쪽도 아님)"),
    ]
    t_ok = True
    for v, want, name in theory:
        got = quality(v)
        if got is not want:
            t_ok = False
            print(f"    ✗ {name} {v}: {got.value} ≠ {want.value}")
    check(t_ok, f"교과서 화음 {len(theory)}개가 전부 제 성질로 판별된다")

    used_ok = True
    for (t, q), sh in BANKS.meaning.items():
        if quality(sh.voicing) is not q:
            used_ok = False
    for q in Quality:
        for sh in BANKS.digit[q]:
            if quality(sh.voicing) is not q:
                used_ok = False
    check(used_ok, "실제로 쓰는 화음 전부가 제 성질에 속한다 (전수)")

    print("\n주장 3 — 네 사분면이 실제 낱말로 채워져 있는가")
    quadrants = {
        ("ko", "흔함×장"): [], ("ko", "흔함×단"): [],
        ("ko", "드묾×장"): [], ("ko", "드묾×단"): [],
        ("en", "흔함×장"): [], ("en", "흔함×단"): [],
        ("en", "드묾×장"): [], ("en", "드묾×단"): [],
    }
    for lang in ("ko", "en"):
        d = Dictionary.load(lang)
        for e in d.entries:
            if e.quality is Quality.NEUTRAL:
                continue
            fam = "흔함" if e.tier <= 1 else ("드묾" if e.tier >= 4 else None)
            if fam is None:
                continue
            pol = "장" if e.quality is Quality.MAJOR else "단"
            quadrants[(lang, f"{fam}×{pol}")].append(e)

    all_filled = True
    for (lang, quad), entries in quadrants.items():
        entries.sort(key=lambda e: -e.freq)
        ex = ", ".join(f"{e.form}" for e in entries[:4])
        if not entries:
            all_filled = False
        print(f"    {lang} {quad:<7} {len(entries):>6,}개   예: {ex}")
    check(all_filled, "여덟 사분면(두 말 × 네 조합)이 모두 채워져 있다")

    # 사분면 대표들이 서로 다른 화음을 받는가
    reps = {}
    for (lang, quad), entries in quadrants.items():
        if lang != "ko" or not entries:
            continue
        e = entries[0]
        reps[quad] = BANKS.meaning[(e.tier, e.quality)].voicing
    check(len(set(reps.values())) == len(reps),
          "네 사분면의 대표 낱말이 서로 다른 의미 화음을 받는다",
          str(reps))
    print("    대표 화음:")
    for quad, v in reps.items():
        print(f"      {quad:<7} {v}   불협화도 {dissonance(v):.3f} · "
              f"{quality(v).value}")

    print("\n주장 4 — 등급이 실제 빈도와 단조 대응하는가 (지프)")
    for lang in ("ko", "en"):
        d = Dictionary.load(lang)
        # 등급별 빈도 중앙값
        by_tier: dict[int, list[int]] = {t: [] for t in range(6)}
        for e in d.entries:
            by_tier[e.tier].append(e.freq)
        medians = []
        for t in range(6):
            v = sorted(by_tier[t])
            medians.append(v[len(v) // 2] if v else 0)
        mono = all(a >= b for a, b in zip(medians, medians[1:]))
        print(f"    {lang} 등급별 빈도 중앙값: "
              + " ≥ ".join(f"{m:,}" for m in medians))
        check(mono, f"{lang}: 등급이 오를수록 빈도 중앙값이 내려간다")

    print("\n주장 5 — 극성 부여가 원본 감성사전과 일치하는가 (표본)")
    probes_ko = [("사랑", "NNG", 1), ("행복", "NNG", 1), ("아름답", "VA", 1),
                 ("기쁘", "VA", 1), ("죽음", "NNG", -1), ("슬프", "VA", -1),
                 ("고통", "NNG", -1), ("나쁘", "VA", -1), ("어둡", "VA", -1),
                 ("밥", "NNG", 0), ("나무", "NNG", 0), ("시간", "NNG", 0)]
    probes_en = [("love", "NN", 1), ("happy", "JJ", 1), ("beautiful", "JJ", 1),
                 ("good", "JJ", 1), ("death", "NN", -1), ("sad", "JJ", -1),
                 ("pain", "NN", -1), ("bad", "JJ", -1), ("dark", "JJ", 0),
                 ("tree", "NN", 0), ("time", "NN", 0), ("water", "NN", 0)]
    for lang, probes in (("ko", probes_ko), ("en", probes_en)):
        d = Dictionary.load(lang)
        bad = []
        for form, tag, want_sign in probes:
            e = d.get(form, tag)
            got = 0 if e is None else (1 if e.polarity > 0 else
                                       -1 if e.polarity < 0 else 0)
            if got != want_sign:
                bad.append(f"{form}({got}≠{want_sign})")
        check(not bad, f"{lang} 표본 {len(probes)}개의 극성 방향이 맞다",
              " ".join(bad))

    print("\n" + "═" * 66)
    if FAIL:
        print(f"실패 {FAIL}건")
        return 1
    print("두 축은 서로 어긋나지 않는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
