#!/usr/bin/env python3
"""웹페이지가 쓸 자료를 만든다.

브라우저는 **적기와 되읽기 둘 다** 한다. 그래서 이런 것들을 실어 보낸다.

    화음 은행·부호     되읽기의 바탕
    개념표·근사표      두 말을 잇는 자리
    사전 부분집합      흔한 낱말의 (등급, 성질, 번호). 여기 없는 낱말은
                       글자로 받아 적으므로 정확성은 잃지 않는다
    활용표             한국어의 융합형 (부른 = 부르 + ᆫ). 규칙형은
                       단순 연결이라 표가 필요 없다

내는 것: docs/data.js
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.compose import Composer  # noqa: E402
from sorimun.core import tags as KT  # noqa: E402
from sorimun.concepts import Concepts  # noqa: E402
from sorimun.core import codes as C, pitch  # noqa: E402
from sorimun.core.glyph import Kind  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402
from sorimun.core.roles import ENGLISH_NAME, ORDER as ROLES  # noqa: E402
from sorimun.decompose import read, render  # noqa: E402
from sorimun.lang import inflect_en as EI  # noqa: E402
from sorimun.dictionary import TIER_LABEL, TIER_LABEL_EN  # noqa: E402
from sorimun.generate import _korean_one  # noqa: E402
from sorimun.lang import get, inflect_en as INF  # noqa: E402

OUT = ROOT / "docs" / "data.js"



# 체언은 받침만 보면 조사를 붙일 수 있으므로 브라우저가 짓는다.
# 활용이 필요한 용언만 미리 지어 실어 보낸다.
_PREDICATE_TAGS = {"VV", "VA", "VX", "VCP", "VCN", "XR"}


def korean_forms(c, kiwi):
    """활용이 필요한 낱말만, 자리마다의 꼴을 미리 지어 둔다."""
    if c.ko_tag not in _PREDICATE_TAGS:
        return None
    from sorimun.core.roles import Role
    return {
        "p": _korean_one(c.ko_form, c.ko_tag, Role.PREDICATE, kiwi, []),
        "pp": _korean_one(c.ko_form, c.ko_tag, Role.PREDICATE, kiwi, [INF.PAST]),
        "a": _korean_one(c.ko_form, c.ko_tag, Role.ADNOMINAL, kiwi, []),
        "ap": _korean_one(c.ko_form, c.ko_tag, Role.ADNOMINAL, kiwi, [INF.PAST]),
        "v": _korean_one(c.ko_form, c.ko_tag, Role.ADVERBIAL, kiwi, []),
    }


def main() -> int:
    ka, ea = get("ko"), get("en")
    kiwi = getattr(ka, "_kiwi", None)
    cx = Concepts.load()

    codes = {
        "roles": [r.value for r in ROLES],
        "rolesEn": [ENGLISH_NAME[r] for r in ROLES],
        "pedal": C.PEDAL,
        "roleInner": [C.ROLE_INNER[r] for r in ROLES],
        "kindMark": {f"{k}|{l}": v for (k, l), v in C.KIND_MARK.items()},
        "flagMark": C.FLAG_MARK,
        "joinMark": C.JOIN_MARK,
        "termSet": {k: list(v) for k, v in C.TERM_SET.items()},
        "tonicSet": {q.value: list(v) for q, v in C.TONIC_SET.items()},
        "sigAnchor": {str(s2): [q.value, t] for s2, (q, t) in C.SIG_ANCHOR.items()},
        "qualitySig": {q.value: v for q, v in C.QUALITY_SIG.items()},
        "tierLeap": list(C.TIER_LEAP),
        "scale": {q.value: list(v) for q, v in C.SCALE.items()},
        "digitOrder": {q.value: list(v) for q, v in C.DIGIT_ORDER.items()},
        "terminators": list(C.TERMINATORS),
        "durTonic": C.DUR_TONIC, "durDigit": C.DUR_DIGIT,
        "durSig": C.DUR_SIG, "durSigEnd": C.DUR_SIG_END,
        "durTerm": C.DUR_TERM,
        "lowest": pitch.LOWEST, "highest": pitch.HIGHEST,
        "tierLabel": list(TIER_LABEL), "tierLabelEn": list(TIER_LABEL_EN),
    }

    # 개념표 — 되읽기와 생성에 필요한 것만
    # 자리를 아끼려고 배열로 싣는다: [한국어, 품사, 영어, 품사, 등급, 극성, 활용]
    concepts = []
    for c in cx.all:
        f = korean_forms(c, kiwi)
        row = [c.ko_form, c.ko_tag, c.en_form, c.en_tag, c.tier, c.polarity]
        if f:
            row.append([f["p"], f["pp"], f["a"], f["ap"], f["v"]])
        concepts.append(row)

    # ── 사전 부분집합 — 브라우저 인코더의 낱말 ──────────────────────
    from sorimun.dictionary import Dictionary
    Q = {"major": 0, "minor": 1, "neutral": 2}

    ko_dic = Dictionary.load("ko")
    ko_rows = []
    ko_kept: set[tuple[str, str]] = set()
    concept_ko = {(c.ko_form, c.ko_tag) for c in cx.all if c.ko_tag != "∅"}
    for e in sorted(ko_dic.entries, key=lambda x: -x.freq):
        is_marker = e.tag in KT.GRAMMATICAL
        need = (is_marker or (e.form, e.tag) in concept_ko
                or len(ko_kept) < 32_000)
        if not need:
            continue
        ko_kept.add((e.form, e.tag))
        ko_rows.append([e.form, e.tag, e.tier, Q[e.quality.value],
                        e.index, e.polarity])

    en_dic = Dictionary.load("en")
    en_rows = []
    en_kept: set[tuple[str, str]] = set()
    concept_en = {(c.en_form, c.en_tag) for c in cx.all}
    from sorimun.lang import tags_en as ET
    for e in sorted(en_dic.entries, key=lambda x: -x.freq):
        closed = e.tag in ET.GRAMMATICAL or e.form in ET.CLOSED
        need = (closed or (e.form, e.tag) in concept_en
                or len(en_kept) < 22_000)
        if not need:
            continue
        en_kept.add((e.form, e.tag))
        en_rows.append([e.form, e.tag, e.tier, Q[e.quality.value],
                        e.index, e.polarity])

    # ── 활용표 — 융합형만 (부른 = 부르/VV + ᆫ/ETM) ──────────────────
    inflect_rows = []
    inflect_path = ROOT / "data" / "raw" / "mecab" / "Inflect.csv"
    if inflect_path.exists():
        import csv as _csv
        best: dict[tuple[str, str], tuple[int, str]] = {}
        with inflect_path.open(encoding="utf-8") as fh:
            for row in _csv.reader(fh):
                if len(row) < 12:
                    continue
                surface, cost, expr = row[0], int(row[3]), row[11]
                morphs = []
                bad = False
                for part in expr.split("+"):
                    bits = part.split("/")
                    if len(bits) < 2:
                        bad = True
                        break
                    morphs.append((bits[0], KT.normalize(bits[1])))
                if bad or not morphs:
                    continue
                head_form, head_tag = morphs[0]
                # 첫 형태소는 내용어(부분집합에 있어야 한다), 나머지는 표지
                if (head_form, head_tag) not in ko_kept:
                    continue
                if head_tag in KT.GRAMMATICAL:
                    continue
                if any(t not in KT.GRAMMATICAL for _f, t in morphs[1:]):
                    continue
                mstr = " ".join(f"{f}/{t}" for f, t in morphs)
                key = (surface, mstr)
                if key not in best or cost < best[key][0]:
                    best[key] = (cost, mstr)
        for (surface, mstr), (cost, _m) in sorted(best.items()):
            inflect_rows.append([surface, mstr, cost])

    # ── 영어 태거 표 — 파이썬 쪽이 진실 원천이다 ────────────────────
    en_tagger = {
        "closed": dict(ET.CLOSED),
        "prior": dict(ET.PRIOR),
        "trans": {k: dict(v) for k, v in ET._T.items()},
        "suffix": [[a, b] for a, b in ET.SUFFIX],
        "copula": sorted(ET.COPULA),
        "be": sorted(ET.BE),
        "aux": sorted(ET.AUXVERB),
        "nominal": sorted(ET.NOMINAL),
        "grammatical": sorted(ET.GRAMMATICAL),
        "content": sorted(ET.CONTENT),
        "koreanName": dict(ET.KOREAN_NAME),
    }

    # 한국어 품사 이름과 갈래
    ko_tags = {
        "koreanName": dict(KT.KOREAN_NAME),
        "grammatical": sorted(KT.GRAMMATICAL),
        "substantive": sorted(KT.SUBSTANTIVE),
        "predicate": sorted(KT.PREDICATE),
    }

    # ── 근사표 부분집합 ─────────────────────────────────────────────
    approx_rows = []
    for (lang, form, tag), ci in sorted(cx._approx.items()):
        kept = ko_kept if lang == "ko" else en_kept
        if (form, tag) in kept:
            approx_rows.append([lang, form, tag, ci])

    # ── 이론 수치 — 페이지가 주장을 증거와 함께 보이도록 ────────────
    from sorimun.core.harmony import _IC_ROUGHNESS, _interval_class
    theory = {
        "leapRoughness": [round(_IC_ROUGHNESS[_interval_class(v)], 3)
                          for v in C.TIER_LEAP],
        # 사분면 대표 낱말 (흔함=0~1등급, 드묾=4~5등급)
        "quadrants": {},
    }
    for lang in ("ko", "en"):
        d = ko_dic if lang == "ko" else en_dic
        best: dict[str, list] = {"흔함×장": [], "흔함×단": [],
                                 "드묾×장": [], "드묾×단": []}
        for e in sorted(d.entries, key=lambda x: -x.freq):
            if e.quality is Quality.NEUTRAL:
                continue
            fam = "흔함" if e.tier <= 1 else ("드묾" if e.tier >= 4 else None)
            if fam is None:
                continue
            key = f"{fam}×{'장' if e.quality is Quality.MAJOR else '단'}"
            if len(best[key]) < 6:
                best[key].append([e.form, e.tag, e.tier,
                                  0 if e.quality is Quality.MAJOR else 1])
        theory["quadrants"][lang] = best

    # 전체 사전을 웹에서 찾을 수 있게 눌러 둔 채로 복사한다.
    # 브라우저의 DecompressionStream 이 그대로 푼다.
    import shutil
    dict_dir = ROOT / "docs" / "dict"
    dict_dir.mkdir(exist_ok=True)
    for lang in ("ko", "en"):
        shutil.copyfile(ROOT / "data" / f"dictionary_{lang}.tsv.gz",
                        dict_dir / f"{lang}.tsv.gz")

    from sorimun.core import alphabet
    from sorimun.core import codes as CC
    payload = {
        "codes": codes,
        "concepts": concepts,
        "dict": {"ko": ko_rows, "en": en_rows},
        "enTagger": en_tagger, "koTags": ko_tags,
        "enIrr": {"past": EI.IRREGULAR_PAST,
                  "plural": EI.IRREGULAR_PLURAL},
        "alphabet": {k: "".join(v) for k, v in alphabet.ALPHABET.items()},
        "inflect": inflect_rows,
        "approx": approx_rows,
        "theory": theory,
        "durations": {
            "tonic": CC.DUR_TONIC, "sig": CC.DUR_SIG,
            "sigEnd": CC.DUR_SIG_END, "digit": CC.DUR_DIGIT,
            "term": CC.DUR_TERM, "restWord": CC.REST_WORD,
            "restGlyph": CC.REST_GLYPH,
            "scale": {r.value: list(CC.ROLE_DURATION_SCALE[r])
                      for r in CC.ROLE_DURATION_SCALE},
            "vel": {"sig": CC.VEL_SIG, "digit": CC.VEL_DIGIT,
                    "term": CC.VEL_TERM, "accent": CC.POLARITY_ACCENT},
        },
        "meta": {
            "concepts": len(cx),
            "ko": len(ko_dic), "en": len(en_dic),
            "koShipped": len(ko_rows), "enShipped": len(en_rows),
            "inflect": len(inflect_rows),
            "reserved": len(C.TERM_SET) + len(C.KIND_MARK) + 2,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.SORIMUN = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n", encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print(f"  개념 {len(concepts):,}, "
          f"ko 낱말 {len(ko_rows):,}, en 낱말 {len(en_rows):,}, "
          f"활용 {len(inflect_rows):,}, 근사 {len(approx_rows):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
