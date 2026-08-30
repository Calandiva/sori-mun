"""소리문 명령줄 도구."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import pitch
from .core.tags import KOREAN_NAME
from .dictionary import Dictionary
from .io import text as textio

BANNER = "소리문 — 한국어 문장을 음악으로"


# ── 옮김 ─────────────────────────────────────────────────────────────
def cmd_render(args: argparse.Namespace) -> int:
    from .core.analyze import Analyzer
    from .compose import Composer

    body = args.text
    if args.file:
        body = Path(args.file).read_text(encoding="utf-8")
    if not body or not body.strip():
        print("옮길 문장이 없다.", file=sys.stderr)
        return 1

    d = Dictionary(args.dict) if args.dict else Dictionary()
    analyzer = Analyzer()
    composer = Composer(d, tempo=args.tempo)
    sentences = analyzer.sentences(body)

    outdir = Path(args.out)
    stems = []
    for i, s in enumerate(sentences, 1):
        sc = composer.compose(s)
        if not args.quiet:
            print(f"\n{textio.analysis_table(s)}\n")
            print(textio.mapping_table(sc, d))
            print()
            print(textio.score_table(sc))

        stem = outdir / (f"{args.name}-{i:02d}" if len(sentences) > 1 else args.name)
        made = []
        if args.mid:
            from .io import midi
            made.append(midi.write(sc, stem.with_suffix(".mid")))
        if args.wav:
            from .io import wave_out
            made.append(wave_out.write(sc, stem.with_suffix(".wav")))
        if args.xml:
            from .io import musicxml
            made.append(musicxml.write(sc, stem.with_suffix(".musicxml")))
        for p in made:
            print(f"  → {p}  ({p.stat().st_size:,}B)")
        stems.append(stem)
    return 0


# ── 사전 ─────────────────────────────────────────────────────────────
def cmd_lookup(args: argparse.Namespace) -> int:
    d = Dictionary(args.dict) if args.dict else Dictionary()
    for word in args.words:
        entries = d.find(word)
        if args.tag:
            entries = [e for e in entries if e.tag == args.tag]
        print(f"\n『{word}』", end="")
        if not entries:
            e = d.get(word, args.tag or "NNG")
            print("  — 사전에 없다. 미등재어 규칙으로 만든 음형:\n")
            print(textio.entry_card(e, d))
            continue
        print(f"  — {len(entries)}가지 쓰임\n")
        for e in entries:
            print(textio.entry_card(e, d))
            print()
    return 0


# ── 찾기 ─────────────────────────────────────────────────────────────
def cmd_search(args: argparse.Namespace) -> int:
    d = Dictionary(args.dict) if args.dict else Dictionary()
    hits = []
    for e in d.entries:
        if args.tier is not None and e.tier != args.tier:
            continue
        if args.quality and e.quality != args.quality:
            continue
        if args.pos and e.tag != args.pos:
            continue
        if args.polarity is not None and e.polarity != args.polarity:
            continue
        if args.events is not None and e.phrase.n_events != args.events:
            continue
        if args.note:
            b = pitch.place(60, e.phrase.ambitus)
            names = {pitch.name(p) for ps, _, _ in e.phrase.render(b) for p in ps}
            if args.note not in names:
                continue
        hits.append(e)

    hits.sort(key=lambda e: -e.freq)
    print(f"{len(hits):,}개 일치 (앞의 {min(args.limit, len(hits))}개)\n")
    print(f"  {'표제어':<14}{'품사':<12}{'빈도':>10}{'등급':>5}{'극성':>5}  음이름")
    print("  " + "─" * 78)
    for e in hits[: args.limit]:
        b = pitch.place(60, e.phrase.ambitus)
        names = " ".join(
            "+".join(pitch.name(p) for p in ps) for ps, _, _ in e.phrase.render(b)
        )
        tier = "표지" if e.is_marker else str(e.tier)
        print(
            f"  {e.form:<14}{KOREAN_NAME.get(e.tag, e.tag):<11}{e.freq:>10,}"
            f"{tier:>5}{e.polarity:>+5}  {names}"
        )
    return 0


# ── 규칙 ─────────────────────────────────────────────────────────────
def cmd_rules(args: argparse.Namespace) -> int:
    from .core.harmony import Quality, shape_table
    from .core.markers import GESTURE, GESTURE_NAME

    print(f"{BANNER}\n")
    print(f"■ 음역 — {pitch.name(pitch.LOWEST)} ~ {pitch.name(pitch.HIGHEST)} "
          f"(정확히 2옥타브, 반음 {pitch.SPAN}개)")
    print(f"  화음 한 개 최대 폭 {pitch.MAX_CHORD_SPAN}반음, "
          f"프레이즈 최대 폭 {pitch.MAX_PHRASE_AMBITUS}반음\n")

    print("■ 협화도 ← 사용 빈도   (흔할수록 순한 화음)")
    t = shape_table()
    print(f"  {'등급':<6}{'뜻':<14}{'major':>7}{'minor':>7}{'neutral':>9}   보기")
    for tier in range(6):
        cells = [len(t.get((tier, q), [])) for q in Quality]
        ex = t.get((tier, Quality.NEUTRAL), [])
        print(f"  {tier:<6}{textio.TIER_LABEL[tier]:<13}"
              f"{cells[0]:>7}{cells[1]:>7}{cells[2]:>9}   "
              f"{[s.voicing for s in ex[:2]]}")
    print()

    print("■ 장·단 ← 감정 극성")
    print("  긍정(+1,+2) → 장3도 관계    부정(-1,-2) → 단3도 관계")
    print("  중립(0)     → 3도가 없는 화음 (완전5도·4도쌓기·2도 계열)\n")

    print("■ 문장 성분 ← 음역·음가·세기")
    print(textio.role_legend())
    print()

    print("■ 조사·어미 = 격(格)마다 고유한 음정 몸짓 (언제나 16분음표)")
    print(f"  {'품사':<7}{'이름':<14}{'음정':<8}{'몸짓'}")
    print("  " + "─" * 60)
    for tag, g in GESTURE.items():
        print(f"  {tag:<7}{KOREAN_NAME.get(tag, tag):<13}{g:>+4}반음  "
              f"{GESTURE_NAME[tag]}")
    print()
    print("■ 겹치지 않음")
    print("  (등급 × 성질) 칸마다 쓰는 화음 모양이 서로소이고, 한 칸 안에서는")
    print("  결정적 스트림에서 하나씩 떼어 쓴다. 그래서 사전 전체에서 프레이즈는")
    print("  유일하다. 16분음표는 조사·어미 전용이라 내용어와도 갈린다.")
    print("  미등재어는 화음 4개짜리 음형을 써서 사전 항목(최대 3개)과 갈린다.")
    return 0


# ── 뼈대 ─────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sorimun", description=BANNER)
    p.add_argument("--version", action="version", version=f"소리문 {__version__}")
    p.add_argument("--dict", help="쓸 사전 파일 (기본: data/dictionary.tsv)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", aliases=["옮김"], help="문장을 음악으로 옮긴다")
    r.add_argument("text", nargs="?", help="옮길 한국어 문장")
    r.add_argument("-f", "--file", help="문장이 담긴 파일")
    r.add_argument("-o", "--out", default="out", help="낼 곳 (기본: out/)")
    r.add_argument("-n", "--name", default="소리문", help="파일 이름")
    r.add_argument("--tempo", type=int, default=66, help="빠르기 ♩= (기본 66)")
    r.add_argument("--mid", action="store_true", help="MIDI 로 낸다")
    r.add_argument("--wav", action="store_true", help="WAV 로 낸다")
    r.add_argument("--xml", action="store_true", help="MusicXML 로 낸다")
    r.add_argument("-q", "--quiet", action="store_true", help="표를 찍지 않는다")
    r.set_defaults(func=cmd_render)

    l = sub.add_parser("lookup", aliases=["사전"], help="낱말의 음형을 찾는다")
    l.add_argument("words", nargs="+", help="찾을 낱말")
    l.add_argument("--tag", help="품사로 좁힌다 (NNG, JKS, VA …)")
    l.set_defaults(func=cmd_lookup)

    s = sub.add_parser("search", aliases=["찾기"], help="조건으로 사전을 훑는다")
    s.add_argument("--tier", type=int, help="협화도 등급 0~5")
    s.add_argument("--quality", choices=["major", "minor", "neutral"], help="성질")
    s.add_argument("--pos", help="품사 태그")
    s.add_argument("--polarity", type=int, help="감정 극성 -2~2")
    s.add_argument("--events", type=int, help="화음 개수")
    s.add_argument("--note", help="이 음이 들어간 것만 (예: C4)")
    s.add_argument("-n", "--limit", type=int, default=30, help="몇 개까지 (기본 30)")
    s.set_defaults(func=cmd_search)

    u = sub.add_parser("rules", aliases=["규칙"], help="변환 규칙 전체를 보인다")
    u.set_defaults(func=cmd_rules)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) in ("render", "옮김"):
        if not (args.mid or args.wav or args.xml):
            args.mid = True   # 아무것도 고르지 않으면 MIDI
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":
    sys.exit(main())
