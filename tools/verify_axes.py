#!/usr/bin/env python3
"""두 축의 조화 검증 — 언어적으로, 음악적으로.

주장 1 (음악):  등급이 오를수록 서명 도약의 거칢이 단조 증가한다.
                '흔함 = 부드러운 가락, 드묾 = 튀는 가락' 이 성립하는가.
주장 2 (음악):  장/단/중성이 멜로디에서 음악 이론대로 갈린다.
                서명1 이 3도의 성질을, 자릿음이 그 성질의 음계를 쓴다.
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
    print("주장 1 — 등급↑ = 서명 도약의 거칢↑ (익숙함의 축)")
    from sorimun.core import codes as CO
    from sorimun.core.harmony import _IC_ROUGHNESS, _interval_class
    rough = [_IC_ROUGHNESS[_interval_class(v)] for v in CO.TIER_LEAP]
    print("    도약(반음):", CO.TIER_LEAP)
    print("    거칢      :", [round(r, 2) for r in rough])
    check(all(a < b for a, b in zip(rough, rough[1:])),
          "여섯 등급의 서명 도약 거칢이 단조 증가한다 "
          "(완전4도 0.12 → 단2도 1.00)")
    check(rough[-1] / rough[0] > 4,
          "0등급과 5등급의 거칢 차이가 4배 이상 — 귀로 또렷이 갈린다")
    inner = list(CO.ROLE_INNER.values())
    check(len(set(inner)) == len(inner) and inner[:2] == [7, 5]
          and inner[-1] == 1,
          "역할 내성 — 가장 흔한 표지·주어가 완전5·4도, 가장 드문 "
          "독립어가 단2도")

    print("\n주장 2 — 장/단/중성이 멜로디에서 음악 이론대로 갈리는가")
    sig_ok = (CO.QUALITY_SIG[Quality.MAJOR] == 4
              and CO.QUALITY_SIG[Quality.MINOR] == 3
              and CO.QUALITY_SIG[Quality.NEUTRAL] == 6)
    check(sig_ok, "서명1 — 장은 장3도(+4), 단은 단3도(+3), 중성은 삼전음(+6)")
    maj, mi, neu = (CO.SCALE[Quality.MAJOR], CO.SCALE[Quality.MINOR],
                    CO.SCALE[Quality.NEUTRAL])
    check(4 in maj and 11 in maj and 3 not in maj,
          "장음계 — 장3도와 이끔음을 품고 단3도가 없다")
    check(3 in mi and 8 in mi and 4 not in mi and 11 not in mi,
          "자연단음계 — 단3도·단6도를 품고 장3도·이끔음이 없다")
    check(all(x % 2 == 0 for x in neu),
          "온음계 — 반음이 없어 어느 조성에도 기울지 않는다")
    check(all(max(CO.TONICS) + max(sc) <= 72 for sc in CO.SCALE.values()),
          "가장 높은 으뜸음에서도 세 음계가 2옥타브 상한 안에 있다")

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

    # 사분면 대표들이 서로 다른 멜로디를 받는가
    from sorimun.core.glyph import Kind, encode
    from sorimun.core.roles import ORDER as ROLES
    reps = {}
    for (lang, quad), entries in quadrants.items():
        if lang != "ko" or not entries:
            continue
        e = entries[0]
        g = encode(ROLES[3], Kind.WORD, e.tier, e.quality, e.index,
                   lang="ko")
        reps[quad] = (e.form, tuple(g.melody))
    mels = [m for _f, m in reps.values()]
    check(len(set(mels)) == len(mels),
          "네 사분면의 대표 낱말이 서로 다른 멜로디를 받는다")
    print("    대표 멜로디:")
    for quad, (form, mel) in reps.items():
        names = " ".join(pitch.name(p) for p in mel)
        print(f"      {quad:<7} {form:<6} {names}  ({len(mel)}음)")

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
