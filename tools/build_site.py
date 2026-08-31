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
from sorimun.core.banks import BANKS  # noqa: E402
from sorimun.core.glyph import Kind  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402
from sorimun.core.roles import ENGLISH_NAME, ORDER as ROLES  # noqa: E402
from sorimun.decompose import read, render  # noqa: E402
from sorimun.dictionary import TIER_LABEL, TIER_LABEL_EN  # noqa: E402
from sorimun.generate import _korean_one  # noqa: E402
from sorimun.lang import get, inflect_en as INF  # noqa: E402

OUT = ROOT / "docs" / "data.js"

EXAMPLES = [
    ("ko", "아이가 조용히 웃었다.",
     "일곱 자리 가운데 셋이 나온다. 소리에는 '아이·웃다·과거·조용히' 라는 "
     "개념만 담기고 조사와 어미는 담기지 않는다. 그래서 영어로도 읽힌다."),
    ("en", "The child laughed quietly.",
     "위와 똑같은 소리다. 영어로 적었지만 소리는 같은 개념을 담으므로 "
     "한국어로 읽어 내면 '아이가 조용히 웃었다' 가 나온다."),
    ("ko", "바람이 꽃을 흔들었다.",
     "주어·목적어·서술어가 모두 개념으로 적힌다. 자리는 역할 화음이, "
     "뜻은 의미 화음과 자릿 화음이 나른다."),
    ("en", "The water was dark.",
     "영어의 'was' 는 한국어에 없다. 그래서 소리에 담기지 않고, 과거라는 "
     "개념만 담긴다. 한국어로 읽으면 '어두웠다' 로 되살아난다."),
    ("ko", "아름다운 노래가 어두운 밤을 천천히 어루만졌다.",
     "'어루만지다' 는 개념표에 없어 한국어 전용으로 적힌다. 그런 낱말은 "
     "다른 말로 옮겨지지 않는다 — 소리에 옮겨진 몫이 표시된다."),
    ("ko", "쀍뿕뿅이 우두두두 쏟아졌다.",
     "사전에도 없는 말은 글자를 하나씩 받아 적는다. 길고 더듬거리지만 "
     "글자 하나 틀리지 않고 돌아온다."),
    ("en", "Love is stronger than death.",
     "비교급과 전치사는 영어의 것이라 소리에 담기지 않는다. 개념으로 "
     "옮겨진 몫이 낮아지는 것이 그대로 드러난다."),
    ("en", "Zxqwv frobnicates the widget.",
     "사전에 없는 영어 낱말도 글자로 받아 적힌다."),
]


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

    examples = []
    for lang, text, note in EXAMPLES:
        an = ka if lang == "ko" else ea
        p = Composer(lang, analyzer=an).compose(an.analyze(text))
        r = read(p.chords)
        examples.append({
            "lang": lang, "text": text, "note": note,
            "tempo": p.tempo,
            "translatable": round(p.translatable, 3),
            "ko": render(r, "ko", ka),
            "en": render(r, "en", ea),
            "tokens": [
                {"form": t.form, "tag": t.tag, "role": t.role.value,
                 "group": t.group}
                for t in p.analysis.tokens
            ],
            "notes": [
                {"p": list(n.pitches), "s": n.start, "d": n.duration,
                 "v": n.velocity, "slot": n.slot, "src": n.source,
                 "role": n.role, "g": n.glyph}
                for n in sorted(p.notes, key=lambda x: x.start)
            ],
            "glyphs": [
                {"role": g.role.value, "kind": g.kind.value,
                 "lang": g.lang, "tier": g.tier,
                 "quality": g.quality.value, "index": g.index,
                 "label": lab}
                for g, lab in zip(p.glyphs, p.labels)
            ],
        })

    banks = {
        "role": [list(BANKS.role[i].voicing) for i in range(8)],
        "language": {k: list(v.voicing) for k, v in BANKS.language.items()},
        "letter": {k: list(v.voicing) for k, v in BANKS.letter.items()},
        "close": [list(s.voicing) for s in BANKS.close],
        "term": [list(s.voicing) for s in BANKS.term],
    }

    codes = {
        "roles": [r.value for r in ROLES],
        "rolesEn": [ENGLISH_NAME[r] for r in ROLES],
        "rolePitch": [C.ROLE_PITCH[r] for r in ROLES],
        "flagOffsets": list(C.FLAG_OFFSETS),
        "melBase": C.MEL_BASE,
        "qualitySig": {q.value: v for q, v in C.QUALITY_SIG.items()},
        "tierLeap": list(C.TIER_LEAP),
        "scale": {q.value: list(v) for q, v in C.SCALE.items()},
        "terminators": list(C.TERMINATORS),
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
        "codes": codes, "banks": banks, "examples": examples,
        "concepts": concepts,
        "dict": {"ko": ko_rows, "en": en_rows},
        "enTagger": en_tagger, "koTags": ko_tags,
        "alphabet": {k: "".join(v) for k, v in alphabet.ALPHABET.items()},
        "inflect": inflect_rows,
        "approx": approx_rows,
        "theory": theory,
        "durations": {
            "role": CC.DUR_ROLE, "head": CC.DUR_HEAD, "sig": CC.DUR_SIG,
            "digit": CC.DUR_DIGIT, "close": CC.DUR_CLOSE,
            "term": CC.DUR_TERM,
            "scale": {r.value: list(CC.ROLE_DURATION_SCALE[r])
                      for r in CC.ROLE_DURATION_SCALE},
            "vel": {"role": CC.VEL_ROLE, "head": CC.VEL_HEAD,
                    "sig": CC.VEL_SIG, "digit": CC.VEL_DIGIT,
                    "close": CC.VEL_CLOSE, "term": CC.VEL_TERM,
                    "accent": CC.POLARITY_ACCENT},
        },
        "meta": {
            "concepts": len(cx),
            "ko": len(ko_dic), "en": len(en_dic),
            "koShipped": len(ko_rows), "enShipped": len(en_rows),
            "inflect": len(inflect_rows),
            "reserved": len(BANKS.all_shapes()),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.SORIMUN = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n", encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print(f"  예제 {len(examples)}, 개념 {len(concepts):,}, "
          f"ko 낱말 {len(ko_rows):,}, en 낱말 {len(en_rows):,}, "
          f"활용 {len(inflect_rows):,}, 근사 {len(approx_rows):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
