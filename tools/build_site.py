#!/usr/bin/env python3
"""웹페이지가 쓸 자료를 만든다.

예제 문장을 실제로 분석·작곡해서 그 결과를 그대로 싣는다. 페이지에
적힌 분석표와 악보는 파이썬이 낸 것과 같은 값이며, 브라우저는 그것을
그리고 소리로 낼 뿐이다.

내는 것: docs/data.js
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.compose import ROLE_RULES, Composer  # noqa: E402
from sorimun.core import pitch  # noqa: E402
from sorimun.core.analyze import Analyzer  # noqa: E402
from sorimun.core.harmony import Quality, shape_table  # noqa: E402
from sorimun.core.markers import GESTURE, GESTURE_NAME  # noqa: E402
from sorimun.core.tags import KOREAN_NAME, Role  # noqa: E402
from sorimun.dictionary import Dictionary  # noqa: E402
from sorimun.io.text import TIER_LABEL  # noqa: E402

OUT = ROOT / "docs" / "data.js"

EXAMPLES = [
    ("아름다운 노래가 어두운 밤을 천천히 어루만졌다.",
     "일곱 성분 중 다섯이 한 문장에 다 나온다. 관형어는 높고 짧게 스치고, "
     "서술어는 C3 까지 내려가 길게 착지한다."),
    ("사랑은 죽음보다 강하다.",
     "긍정어 '사랑'은 장3도 관계, 부정어 '죽음'은 단3도 관계를 받는다. "
     "감정 축이 가장 또렷하게 들리는 문장."),
    ("철수야, 물이 얼음이 되었다.",
     "'물이'와 '얼음이'는 똑같이 '이'로 끝나지만 하나는 주격(JKS), 하나는 "
     "보격(JKC)이다. 조사가 다르니 몸짓도 다르다."),
    ("밥은 내가 먹었다.",
     "'밥은'의 은/는은 주어 표시가 아니다. 뒤에 진짜 주어 '내가'가 있으므로 "
     "'밥은'은 목적어로 잡히고 중고음역으로 올라간다."),
    ("그는 슬픔의 노래를 부른다.",
     "관형격 '의'는 상행 단2도 — 바로 뒤 체언에 매달리는 소리다."),
    ("아, 봄이 왔구나!",
     "감탄사 '아'는 독립어. 가장 높은 자리에서 앞뒤로 긴 쉼표를 두르고 홀로 "
     "울린다. 느낌표는 서술어의 세기를 올린다."),
    ("너는 어디로 가니?",
     "물음표는 맨 끝에 상행 장2도를 하나 덧붙여 말끝을 올린다."),
    ("쀍뿕뿅이 우두두두 쏟아졌다.",
     "'쀍뿕뿅'은 사전에 없다. 미등재어는 화음 넷짜리 긴 음형을 받아 "
     "길고 낯설게 울린다."),
]

# 사전에서 페이지에 실을 몫. 전부 싣기에는 28만 개가 너무 크다.
DICT_MARKERS = True          # 조사·어미는 전부
DICT_CONTENT_TOP = 4000      # 내용어는 빈도 상위만


def role_key(role: Role) -> str:
    return role.value


def main() -> int:
    analyzer = Analyzer()
    d = Dictionary()
    composer = Composer(d)

    examples = []
    for text, note in EXAMPLES:
        s = analyzer.analyze(text)
        sc = composer.compose(s)
        seen = set()
        mapping = []
        for label, e, _role in sc.entries:
            if label in seen:
                continue
            seen.add(label)
            item = {
                "form": e.form, "tag": e.tag,
                "tagName": KOREAN_NAME.get(e.tag, e.tag),
                "kind": e.kind, "events": e.phrase.n_events,
            }
            if e.is_marker:
                item["gesture"] = GESTURE[e.tag]
                item["gestureName"] = GESTURE_NAME[e.tag]
            else:
                item["tier"] = e.tier
                item["tierLabel"] = "미등재" if not e.known else TIER_LABEL[e.tier]
                item["polarity"] = e.polarity
                item["quality"] = e.quality
                item["known"] = e.known
            mapping.append(item)

        examples.append({
            "text": text,
            "note": note,
            "term": s.terminator,
            "tempo": sc.tempo,
            "length": sc.length,
            "eojeols": [
                {
                    "surface": e.surface,
                    "role": role_key(e.role),
                    "guessed": e.guessed,
                    "morphs": [
                        {"form": m.form, "tag": m.tag,
                         "tagName": KOREAN_NAME.get(m.tag, m.tag)}
                        for m in e.morphs
                    ],
                }
                for e in s.eojeols
            ],
            "map": mapping,
            "notes": [
                {"p": list(n.pitches), "s": n.start, "d": n.duration,
                 "v": n.velocity, "src": n.source, "role": n.role,
                 "k": n.kind, "e": n.eojeol}
                for n in sorted(sc.notes, key=lambda x: x.start)
            ],
        })

    # ── 규칙표 ──────────────────────────────────────────────────────
    table = shape_table()
    tiers = []
    for t in range(6):
        tiers.append({
            "tier": t,
            "label": TIER_LABEL[t],
            "shapes": {
                q.value: [list(s.voicing) for s in table.get((t, q), [])[:6]]
                for q in Quality
            },
            "counts": {q.value: len(table.get((t, q), [])) for q in Quality},
        })

    roles = []
    for role in (Role.INDEPENDENT, Role.ADNOMINAL, Role.OBJECT, Role.COMPLEMENT,
                 Role.SUBJECT, Role.ADVERBIAL, Role.PREDICATE):
        r = ROLE_RULES[role]
        roles.append({
            "role": role.value, "register": r.register,
            "registerName": pitch.name(r.register),
            "dur": (f"×{r.dur_num}" if r.dur_den == 1
                    else f"×{r.dur_num}/{r.dur_den}"),
            "velocity": r.velocity, "note": r.note,
        })

    gestures = [
        {"tag": t, "name": KOREAN_NAME.get(t, t), "semitones": g,
         "gesture": GESTURE_NAME[t]}
        for t, g in GESTURE.items()
    ]

    # ── 사전 일부 ───────────────────────────────────────────────────
    entries = list(d.entries)
    markers = [e for e in entries if e.is_marker]
    content = sorted(
        (e for e in entries if not e.is_marker), key=lambda e: -e.freq
    )[:DICT_CONTENT_TOP]
    chosen = markers + content if DICT_MARKERS else content
    # [표제어, 품사, 등급(표지는 -1), 극성, 빈도, 프레이즈코드]
    dict_rows = [
        [e.form, e.tag, e.tier, e.polarity, e.freq, e.code]
        for e in sorted(chosen, key=lambda e: (-e.freq, e.form))
    ]

    payload = {
        "meta": {
            "entries": len(d),
            "markers": len(markers),
            "lowest": pitch.LOWEST,
            "highest": pitch.HIGHEST,
            "shapeCount": sum(len(v) for v in table.values()),
            "dictSample": len(dict_rows),
        },
        "examples": examples,
        "rules": {"tiers": tiers, "roles": roles, "gestures": gestures},
        "dict": dict_rows,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.SORIMUN = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print(f"  예제 {len(examples)}개, 사전 표본 {len(dict_rows):,}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
