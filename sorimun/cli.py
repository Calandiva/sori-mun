"""소리문 명령줄 도구."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .compose import Composer
from .concepts import Concepts
from .core import pitch
from .decompose import read, render
from .dictionary import Dictionary, TIER_LABEL
from .io import text as T
from .lang import detect, get

BANNER = "소리문 — 하나의 소리, 두 개의 말"


# ── 옮김: 글 → 소리 ──────────────────────────────────────────────────
def cmd_render(args) -> int:
    body = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    if not body or not body.strip():
        print("옮길 문장이 없다.", file=sys.stderr)
        return 1
    lang = args.lang or detect(body)
    an = get(lang)
    cp = Composer(lang, tempo=args.tempo, analyzer=an)

    outdir = Path(args.out)
    for i, a in enumerate(an.sentences(body), start=1):
        p = cp.compose(a)
        if not args.quiet:
            print(f"\n{T.analysis_table(a)}\n")
            print(T.glyph_table(p))
            print()
            print(T.score_table(p))
            print(f"\n  개념으로 적힌 낱말 {p.translatable:.0%} "
                  f"— 이만큼이 다른 말로도 읽힌다")
        stem = outdir / (f"{args.name}-{i:02d}" if i > 1 or args.file
                         else args.name)
        made = []
        if args.mid:
            from .io import midi
            made.append(midi.write(p, stem.with_suffix(".mid")))
        if args.wav:
            from .io import wave_out
            made.append(wave_out.write(p, stem.with_suffix(".wav")))
        if args.xml:
            from .io import musicxml
            made.append(musicxml.write(p, stem.with_suffix(".musicxml")))
        for m in made:
            print(f"  → {m}  ({m.stat().st_size:,}B)")
    return 0


# ── 읽기: 소리 → 글 ──────────────────────────────────────────────────
def cmd_read(args) -> int:
    from .io import midi_read

    if args.file:
        chords = midi_read.chords(args.file)
        src = f"{args.file} 에서 화음 {len(chords)}개"
    elif args.notes:
        chords = midi_read.parse_notes(args.notes)
        src = f"손으로 넣은 화음 {len(chords)}개"
    else:
        print("읽을 소리가 없다. --file 로 .mid 파일을 주거나 "
              "--notes 로 음이름을 적어라.", file=sys.stderr)
        return 1

    r = read(chords)
    print(f"{src}\n")
    if not args.quiet:
        print(T.reading_table(r))
        print()
    targets = args.to or ["ko", "en"]
    for lang in targets:
        try:
            out = render(r, lang, get(lang))
        except Exception as exc:      # pragma: no cover
            out = f"(읽어 내지 못했다: {exc})"
        label = "한국어" if lang == "ko" else "영어"
        print(f"  {label:<5} 『{out}』")
    if r.translatable < 0.999:
        print(f"\n  개념으로 적힌 낱말 {r.translatable:.0%} "
              f"— 나머지는 적은 말에서만 읽힌다")
    for w in r.warnings:
        print(f"  ! {w}")
    return 0


# ── 사전 ─────────────────────────────────────────────────────────────
def cmd_lookup(args) -> int:
    cx = Concepts.load()
    for word in args.words:
        lang = args.lang or detect(word)
        d = Dictionary.load(lang)
        print(f"\n『{word}』 [{lang}]")
        entries = d.find(word)
        if not entries:
            print("  사전에 없다 — 글자로 받아 적힌다.")
            continue
        for e in entries[: args.limit]:
            c = cx.of(lang, e.form, e.tag)
            line = (f"  {e.form}/{e.tag:<5} 빈도 {e.freq:>9,}  "
                    f"{e.tier}등급 {TIER_LABEL[e.tier]:<9} "
                    f"극성 {e.polarity:+d}  {e.quality.value}")
            if c is not None and c.form(lang) == (e.form, e.tag):
                other = c.en_form if lang == "ko" else c.ko_form
                line += f"   ≡ 개념 {c.index} ({other})"
            print(line)
    return 0


def cmd_concept(args) -> int:
    cx = Concepts.load()
    hits = []
    for c in cx.all:
        if args.word:
            if args.word not in (c.ko_form, c.en_form):
                continue
        hits.append(c)
    print(f"개념 {len(cx):,}개 중 {len(hits):,}개\n")
    print(f"  {'번호':>6}  {'한국어':<14}{'영어':<16}{'등급':<6}극성")
    print("  " + "─" * 58)
    for c in hits[: args.limit]:
        print(f"  {c.index:>6}  {c.ko_form + '/' + c.ko_tag:<14}"
              f"{c.en_form + '/' + c.en_tag:<16}{c.tier:<6}{c.polarity:+d}")
    return 0


def cmd_rules(args) -> int:
    print(T.rules_text())
    return 0


# ── 뼈대 ─────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sorimun", description=BANNER)
    p.add_argument("--version", action="version", version=f"소리문 {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", aliases=["옮김"], help="글을 소리로 옮긴다")
    r.add_argument("text", nargs="?")
    r.add_argument("-f", "--file")
    r.add_argument("-l", "--lang", choices=["ko", "en"], help="말 (기본: 자동)")
    r.add_argument("-o", "--out", default="out")
    r.add_argument("-n", "--name", default="소리문")
    r.add_argument("--tempo", type=int, default=72)
    r.add_argument("--mid", action="store_true")
    r.add_argument("--wav", action="store_true")
    r.add_argument("--xml", action="store_true")
    r.add_argument("-q", "--quiet", action="store_true")
    r.set_defaults(func=cmd_render)

    d = sub.add_parser("read", aliases=["읽기"], help="소리를 글로 되읽는다")
    d.add_argument("-f", "--file", help="읽을 .mid 파일")
    d.add_argument("--notes", help='음이름으로 직접 (예: "C3+E3+E4 G3+A3+F4")')
    d.add_argument("--to", nargs="+", choices=["ko", "en"],
                   help="어느 말로 낼지 (기본: 둘 다)")
    d.add_argument("-q", "--quiet", action="store_true")
    d.set_defaults(func=cmd_read)

    lk = sub.add_parser("lookup", aliases=["사전"], help="낱말을 찾는다")
    lk.add_argument("words", nargs="+")
    lk.add_argument("-l", "--lang", choices=["ko", "en"])
    lk.add_argument("-n", "--limit", type=int, default=8)
    lk.set_defaults(func=cmd_lookup)

    cc = sub.add_parser("concept", aliases=["개념"], help="개념표를 본다")
    cc.add_argument("word", nargs="?")
    cc.add_argument("-n", "--limit", type=int, default=30)
    cc.set_defaults(func=cmd_concept)

    u = sub.add_parser("rules", aliases=["규칙"], help="규칙 전체를 보인다")
    u.set_defaults(func=cmd_rules)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd in ("render", "옮김") and not (args.mid or args.wav or args.xml):
        args.mid = True
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":
    sys.exit(main())
