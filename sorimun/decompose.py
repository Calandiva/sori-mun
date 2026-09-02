"""되읽기 — 소리에서 뜻으로, 그리고 어느 말로든.

화음의 차례만 본다. 길이도 쉼표도 보지 않으므로 사람이 연주해 길이가
흔들려도 뜻은 그대로다.

    화음 차례 → 글리프 → (자리, 개념 또는 낱말) → 문장

개념으로 적힌 낱말은 어느 말로도 나온다. 영어로 적은 소리를 한국어로
읽어 내는 것이 이 층에서 이루어진다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .concepts import Concept, Concepts
from .generate import RawWord
from .core import alphabet, codes as C
from .core.glyph import (DecodeError, Glyph, Kind, decode, is_join,
                         read_terminator)
from .core.roles import Role
from .dictionary import Dictionary
from .generate import english, korean


@dataclass(slots=True)
class Item:
    """되찾은 낱말 하나."""

    role: Role
    kind: Kind
    concept: Concept | None = None
    form: str = ""
    tag: str = ""
    lang: str | None = None
    group: int = 0
    flag: int = 0

    def __str__(self) -> str:
        if self.concept is not None:
            return f"{self.concept}/{self.role.value}"
        return f"{self.form}/{self.tag}·{self.role.value}"


@dataclass(slots=True)
class Reading:
    items: list[Item] = field(default_factory=list)
    terminator: str = "."
    glyphs: list[Glyph] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def source_lang(self) -> str | None:
        """소리를 적은 말. 개념만으로 이루어졌다면 어느 말도 아니다."""
        langs = {i.lang for i in self.items if i.lang}
        return next(iter(langs)) if len(langs) == 1 else None

    @property
    def concepts(self) -> list[tuple[Role, Concept, int]]:
        """(자리, 개념, 어절번호). 어절번호가 있어야 문법 개념이 제
        낱말에 붙는다 — 다른 어절의 낱말에 붙으면 뜻이 뒤틀린다."""
        return [(i.role, i.concept, i.group)
                for i in self.items if i.concept is not None]

    def cross_items(self) -> list:
        """다른 말로 지을 때 쓸 목록.

        정확한 개념은 그대로, 그 말 전용 낱말은 가장 가까운 개념으로
        잇고(어루만지다 ≈ touch), 받아 적은 낱말은 글자 그대로 넘긴다
        (고유명사는 옮기지 않고 그대로 두는 것이 맞다). 그래서 한 바퀴
        돌아도 핵심 낱말이 살아남는다.
        """
        from .core.glyph import Kind

        cx = Concepts.load()
        out = []
        for i in self.items:
            if i.concept is not None:
                out.append((i.role, i.concept, i.group))
            elif i.kind is Kind.LETTER:
                out.append((i.role, RawWord(i.form), i.group))
            elif i.lang is not None:
                c = cx.approx(i.lang, i.form, i.tag)
                if c is not None:
                    out.append((i.role, c, i.group))
        return out

    @property
    def translatable(self) -> float:
        content = [i for i in self.items if i.role is not Role.MARKER]
        if not content:
            return 1.0
        return sum(1 for i in content if i.concept is not None) / len(content)


def read(chords: list[tuple[int, ...]]) -> Reading:
    """화음 차례에서 자리와 뜻을 되찾는다."""
    r = Reading()
    cx = Concepts.load()
    i = 0
    group = 0
    chars: list[str] = []
    char_role = Role.ADVERBIAL
    char_lang = "ko"

    def flush() -> None:
        nonlocal chars
        if chars:
            r.items.append(Item(char_role, Kind.LETTER, None, "".join(chars),
                                "?", char_lang, group))
            chars = []

    while i < len(chords):
        mark = read_terminator(chords[i])
        if mark is not None:
            flush()
            r.terminator = mark
            i += 1
            continue
        try:
            g, i = decode(chords, i)
        except DecodeError as exc:
            r.warnings.append(f"{i}번째 화음에서 막혔다: {exc}")
            break
        r.glyphs.append(g)

        # 이음 화음이 따라오면 같은 낱말이 이어진다
        joined = i < len(chords) and is_join(chords[i])
        if joined:
            i += 1

        if g.kind is Kind.LETTER:
            ch = alphabet.to_char(g.lang, g.index)
            if g.flag and not chars:
                ch = ch.upper()
            chars.append(ch)
            char_role, char_lang = g.role, g.lang
            if not joined:
                flush()
        else:
            flush()
            if g.kind is Kind.CONCEPT:
                c = cx.at(g.index)
                if c is None:
                    r.warnings.append(f"개념 {g.index} 이 표에 없다")
                    r.items.append(Item(g.role, g.kind, None, "?", "?", None, group))
                else:
                    r.items.append(Item(g.role, g.kind, c, group=group,
                                        flag=g.flag))
            else:
                d = Dictionary.load(g.lang)
                e = d.at(g.tier, g.quality, g.index)
                if e is None:
                    r.warnings.append(
                        f"{g.lang} 사전 칸 ({g.tier},{g.quality.value}) 에 "
                        f"번호 {g.index} 가 없다")
                    r.items.append(Item(g.role, g.kind, None, "?", "?", g.lang, group))
                else:
                    r.items.append(Item(g.role, g.kind, None, e.form, e.tag,
                                        g.lang, group, g.flag))
        if not joined:
            group += 1

    flush()
    return r


# ── 어느 말로 읽어 낼 것인가 ─────────────────────────────────────────
def render(r: Reading, lang: str, analyzer=None) -> str:
    """되읽은 것을 목표 언어로 낸다.

    적힌 말과 같은 말로 읽으면 원문이 그대로 돌아온다. 다른 말로 읽으면
    개념과 자리만으로 문장을 새로 짓는다 — 조사·어미와 어순은 그 말의
    것이므로 여기서 새로 붙인다.
    """
    src = r.source_lang
    # 개념만으로 이루어진 소리는 어느 말의 것도 아니다. 그럴 때는 언제나
    # 새로 짓는다 — 원문이라 할 것이 없기 때문이다.
    if src is not None and src == lang:
        return _same(r, lang, analyzer)
    items = r.cross_items()
    if lang == "ko":
        kiwi = getattr(analyzer, "_kiwi", None)
        return korean(items, r.terminator, kiwi)
    return english(items, r.terminator)


def _same(r: Reading, lang: str, analyzer) -> str:
    """적힌 말 그대로 되짓는다. 원문이 정확히 돌아온다."""
    morphs: list[tuple[str, str]] = []
    groups: list[int] = []
    for it in r.items:
        if it.concept is not None:
            f, t = it.concept.form(lang)
            if t == "∅":
                continue      # 이 말에서는 겉으로 드러나지 않는 문법이다
        else:
            f, t = it.form, it.tag
        if it.flag:
            f = f[:1].upper() + f[1:]
        morphs.append((f, t))
        groups.append(it.group)
    if analyzer is None:
        return " ".join(m[0] for m in morphs) + r.terminator
    text = analyzer.join(morphs, groups)
    return text + r.terminator if text else ""


# ── 여러 문장 ────────────────────────────────────────────────────────
def split_sentences(chords: list[tuple[int, ...]]) -> list[list[tuple[int, ...]]]:
    """화음 차례를 문장 단위로 가른다.

    종결 화음은 저만의 은행을 쓰므로(은행이 서로소다) 모양만 보고
    안전하게 가를 수 있다.
    """
    out: list[list[tuple[int, ...]]] = []
    cur: list[tuple[int, ...]] = []
    for c in chords:
        cur.append(tuple(c))
        if read_terminator(c) is not None:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def read_all(chords: list[tuple[int, ...]]) -> list[Reading]:
    """여러 문장을 각각 되읽는다."""
    return [read(part) for part in split_sentences(chords)]


def render_all(chords: list[tuple[int, ...]], lang: str, analyzer=None) -> str:
    """화음 차례 전체를 목표 언어의 글로 낸다."""
    parts = [render(r, lang, analyzer) for r in read_all(chords)]
    return " ".join(p for p in parts if p)
