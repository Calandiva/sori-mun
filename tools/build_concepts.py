#!/usr/bin/env python3
"""개념 층 — 두 말을 잇는다.

소리가 언어에 매이지 않으려면, '사랑' 과 'love' 가 같은 번호를 받아야
한다. 그래야 영어로 적은 소리를 한국어로 읽어 낼 수 있다.

바탕은 MUSE 한·영 대역쌍이다. 다만 그대로는 쓸 수 없다 —
`night → 나이트`(음차), `water → 물이`(굴절형), `sing → sing`(그대로)
같은 잡음이 섞여 있다. 그래서 이렇게 씻는다.

    1. 한국어 쪽을 표제어로 되돌린다 (물이 → 물, 아름다운 → 아름답)
    2. 두 사전에 다 있는 것만 남긴다
    3. 품사가 서로 맞는 것만 남긴다 (명사↔체언, 동사↔용언 …)
    4. 서로가 서로의 으뜸 짝인 것만 남긴다
       — love 의 으뜸 한국어가 사랑이고, 사랑의 으뜸 영어가 love 일 때만.
         음차(러브)와 굴절형은 빈도에서 밀려 저절로 떨어진다.

내는 것: data/concepts.tsv.gz
    번호 <TAB> 한국어 <TAB> 품사 <TAB> 영어 <TAB> 품사 <TAB> 빈도 <TAB> 극성
"""

from __future__ import annotations

import csv
import gzip
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.core import tags as KT  # noqa: E402
from sorimun.dictionary import Dictionary  # noqa: E402
from sorimun.lang import tags_en as ET  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "concepts.tsv.gz"
CURATED = ROOT / "data" / "concepts_curated.tsv"
GRAMMAR = ROOT / "data" / "concepts_grammar.tsv"

# 품사가 서로 맞아야 한다. 명사를 동사에 이어 붙이면 문장이 무너진다.
COMPATIBLE = {
    ET.NN: KT.SUBSTANTIVE, ET.NNP: KT.SUBSTANTIVE, ET.PRP: KT.SUBSTANTIVE,
    ET.CD: {"NR", "NNG", "MM"},
    ET.VB: {"VV", "VA", "VX", "XR", "NNG"},   # 하다형 명사도 용언 노릇을 한다
    ET.JJ: {"VA", "MM", "XR", "NNG"},
    ET.RB: {"MAG", "MAJ"},
    ET.UH: {"IC"},
    ET.IN: {"JKB"}, ET.CC: {"MAJ", "JC"}, ET.DT: {"MM"},
}


def read_pairs() -> set[tuple[str, str]]:
    pairs = set()
    for name, flip in (("muse_en_ko.txt", False), ("muse_ko_en.txt", True)):
        path = RAW / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            p = line.rstrip("\n").split("\t")
            if len(p) != 2:
                continue
            en, ko = (p[1], p[0]) if flip else (p[0], p[1])
            en, ko = en.strip().lower(), ko.strip()
            if not en or not ko or not en.isascii() or ko.isascii():
                continue      # 그대로 옮겨 적은 것은 버린다
            pairs.add((en, ko))
    return pairs


def main() -> int:
    try:
        from kiwipiepy import Kiwi
    except ImportError:
        print("kiwipiepy 가 필요하다", file=sys.stderr)
        return 1

    ko_dic, en_dic = Dictionary.load("ko"), Dictionary.load("en")
    pairs = read_pairs()
    print(f"대역쌍 {len(pairs):,}")

    # 1. 한국어 쪽을 표제어로 되돌린다
    kiwi = Kiwi(num_workers=-1)
    ko_words = sorted({ko for _en, ko in pairs})
    lemma: dict[str, tuple[str, str] | None] = {}
    for w, toks in zip(ko_words, kiwi.tokenize(ko_words)):
        content = [(t.form, KT.normalize(t.tag)) for t in toks
                   if KT.normalize(t.tag) in KT.CONTENT]
        lemma[w] = content[-1] if len(content) == 1 else None
        if len(content) > 1:
            # 합성어는 통째로 사전에 있으면 그대로 쓴다
            for tag in ("NNG", "NNP", "MAG"):
                if ko_dic.get(w, tag):
                    lemma[w] = (w, tag)
                    break

    # 2~3. 두 사전에 다 있고 품사가 맞는 것만
    ok: list[tuple[str, str, str, str, str, int, int]] = []
    for en, ko in sorted(pairs):
        lm = lemma.get(ko)
        if lm is None:
            continue
        ko_form, ko_tag = lm
        ke = ko_dic.get(ko_form, ko_tag)
        if ke is None:
            continue
        for ee in en_dic.find(en):
            allowed = COMPATIBLE.get(ee.tag)
            if allowed and ko_tag in allowed:
                ok.append((en, ee.tag, ko_form, ko_tag,
                           ee.freq, ke.freq, ee.polarity or ke.polarity))
                break
    print(f"  표제어·품사 맞물림 {len(ok):,}")

    # 4. 서로가 서로의 으뜸 짝인 것만
    best_ko: dict[str, tuple] = {}
    best_en: dict[str, tuple] = {}
    for row in ok:
        en, en_tag, ko, ko_tag, en_f, ko_f, pol = row
        if en not in best_ko or ko_f > best_ko[en][5]:
            best_ko[en] = row
        if ko not in best_en or en_f > best_en[ko][4]:
            best_en[ko] = row

    mutual = []
    for en, row in best_ko.items():
        ko = row[2]
        if best_en.get(ko) and best_en[ko][0] == en:
            mutual.append(row)
    print(f"  서로 으뜸인 짝 {len(mutual):,}")

    # 손질 표가 있으면 덮어쓴다
    curated = 0
    if CURATED.exists():
        by_en = {(r[0], r[1]): i for i, r in enumerate(mutual)}
        by_ko = {(r[2], r[3]): i for i, r in enumerate(mutual)}
        for line in CURATED.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            f = line.split("\t")
            if len(f) != 4:
                continue
            en, en_tag, ko, ko_tag = f
            ee, ke = en_dic.get(en, en_tag), ko_dic.get(ko, ko_tag)
            if ee is None or ke is None:
                print(f"    손질 무시(사전에 없음): {line}")
                continue
            for tbl in (by_en.get((en, en_tag)), by_ko.get((ko, ko_tag))):
                if tbl is not None and mutual[tbl] is not None:
                    mutual[tbl] = None
            mutual.append((en, en_tag, ko, ko_tag, ee.freq, ke.freq,
                           ee.polarity or ke.polarity))
            curated += 1
        mutual = [m for m in mutual if m is not None]
        print(f"  손질 {curated}개 반영 → {len(mutual):,}")

    # 흔한 개념이 앞 번호를 받아 이름이 짧아진다
    mutual.sort(key=lambda r: (-(r[4] + r[5]), r[0], r[2]))

    # 문법 개념을 맨 앞에 세운다. 가장 자주 나오므로 가장 짧게 적혀야
    # 한다. 사전에 없는 기호꼴이라 낱말 검사를 거치지 않는다.
    grammar = []
    if GRAMMAR.exists():
        for line in GRAMMAR.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            f = line.split("\t")
            if len(f) < 4:
                continue
            ko_form, ko_tag, en_form, en_tag = f[0], f[1], f[2], f[3]
            grammar.append((en_form, en_tag, ko_form, ko_tag, 10**9, 10**9, 0))
    mutual = grammar + mutual

    # 한 낱말이 두 개념에 걸치면 되찾기가 일대일이 아니게 된다.
    # ('잡' 이 take 와 hold 둘 다이면, 번호에서 낱말로 돌아올 때 어느
    #  쪽인지 알 수 없다.) 앞에 온 것을 남기고 뒤엣것을 버린다.
    seen_ko: set[tuple[str, str]] = set()
    seen_en: set[tuple[str, str]] = set()
    kept, dropped = [], []
    for row in mutual:
        en, en_tag, ko, ko_tag = row[0], row[1], row[2], row[3]
        if (en, en_tag) in seen_en or ((ko, ko_tag) in seen_ko and ko_tag != "∅"):
            dropped.append(f"{en}/{en_tag}↔{ko}/{ko_tag}")
            continue
        seen_en.add((en, en_tag))
        if ko_tag != "∅":
            seen_ko.add((ko, ko_tag))
        kept.append(row)
    mutual = kept
    print(f"  문법 개념 {len(grammar)}개를 앞에 세움")
    if dropped:
        print(f"  한쪽이 겹쳐 버린 짝 {len(dropped)}개: "
              + ", ".join(dropped[:6]) + (" …" if len(dropped) > 6 else ""))
    print(f"  → 개념 {len(mutual):,}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["번호", "한국어", "품사", "영어", "품사", "빈도", "극성"])
        for i, (en, en_tag, ko, ko_tag, en_f, ko_f, pol) in enumerate(mutual):
            w.writerow([i, ko, ko_tag, en, en_tag, en_f + ko_f, pol])

    print(f"\n개념 {len(mutual):,} → {OUT.relative_to(ROOT)} "
          f"({OUT.stat().st_size:,}B)")
    print("\n앞자리 개념 20:")
    for i, (en, en_tag, ko, ko_tag, ef, kf, pol) in enumerate(mutual[:20]):
        print(f"  {i:>3} {ko}/{ko_tag:<5} ↔ {en}/{en_tag:<4} 극성{pol:+d}")
    probe = ["love", "night", "song", "water", "beautiful", "death",
             "dark", "slowly", "spring", "sing"]
    idx = {r[0]: r for r in mutual}
    print("\n표본:", {w: (idx[w][2] if w in idx else "—") for w in probe})
    return 0


if __name__ == "__main__":
    sys.exit(main())
