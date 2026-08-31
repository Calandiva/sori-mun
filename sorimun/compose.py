"""작곡 — 문장을 소리로 적는다.

낱말마다 셋 중 하나로 적힌다.

    개념   두 말에 다 있는 낱말. 소리는 언어를 담지 않으므로 어느 말로도
           읽어 낼 수 있다.
    낱말   그 말에만 있는 것 (조사·어미, 관사·전치사, 개념표에 없는 낱말).
           언어 화음을 앞세워 적는다.
    글자   사전에도 없는 것. 글자를 하나씩 받아 적는다.

부호를 나르는 것은 음높이와 화성뿐이다. 길이와 세기는 표현일 뿐이므로
연주하는 사람이 흔들어도 뜻은 상하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .concepts import Concept, Concepts
from .core import alphabet, codes as C, pitch
from .core.glyph import Event, Glyph, Kind, encode, terminator
from .core.harmony import Quality
from .core.roles import Role
from .dictionary import Dictionary
from .lang.base import Analysis, Token


@dataclass(slots=True)
class Note:
    pitches: tuple[int, ...]
    start: int
    duration: int
    velocity: int
    slot: str
    source: str
    role: str
    glyph: int

    @property
    def end(self) -> int:
        return self.start + self.duration


@dataclass(slots=True)
class Piece:
    lang: str
    notes: list[Note] = field(default_factory=list)
    glyphs: list[Glyph] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    analysis: Analysis | None = None
    tempo: int = 72

    @property
    def chords(self) -> list[tuple[int, ...]]:
        """되읽기에 넣을 꼴 — 화음의 차례. 길이는 담지 않는다."""
        return [n.pitches for n in sorted(self.notes, key=lambda x: x.start)]

    @property
    def length(self) -> int:
        return max((n.end for n in self.notes), default=0)

    @property
    def ambitus(self) -> tuple[int, int]:
        if not self.notes:
            return (pitch.LOWEST, pitch.LOWEST)
        return (min(min(n.pitches) for n in self.notes),
                max(max(n.pitches) for n in self.notes))

    @property
    def translatable(self) -> float:
        """개념으로 적힌 낱말의 비율. 다른 말로 읽어 낼 수 있는 몫이다."""
        content = [g for g in self.glyphs if g.role is not Role.MARKER]
        if not content:
            return 1.0
        n = sum(1 for g in content if g.kind is Kind.CONCEPT)
        return n / len(content)


class Composer:
    def __init__(self, lang: str, tempo: int = 72, analyzer=None) -> None:
        self.lang = lang
        self.dict = Dictionary.load(lang)
        self.concepts = Concepts.load()
        self.tempo = tempo
        self.analyzer = analyzer

    def _faithful(self, group: list[Token]) -> bool:
        """이 어절이 형태소에서 원문 그대로 되지어지는가."""
        if self.analyzer is None:
            return True
        surface = "".join(t.surface for t in group if t.surface)
        if not surface:
            return True
        parts = []
        for t in group:
            f = t.form
            if t.surface[:1].isupper():
                f = f[:1].upper() + f[1:]
            parts.append((f, t.tag))
        try:
            return self.analyzer.join(parts, [0] * len(parts)) == surface
        except Exception:
            return False

    def _spellable_surface(self, group: list[Token]) -> str:
        return "".join(t.surface for t in group if t.surface)

    def compose(self, analysis: Analysis) -> Piece:
        piece = Piece(lang=self.lang, analysis=analysis, tempo=self.tempo)
        cursor = 0

        for group in analysis.groups:
            if self.analyzer is not None and not self._faithful(group):
                surface = "".join(t.surface for t in group if t.surface)
                cursor = self._spell(piece, group[0].role, surface, cursor,
                                     C.CLOSE_BREAK)
                continue
            for j, tok in enumerate(group):
                close = (C.CLOSE_BREAK if j + 1 >= len(group)
                         else C.CLOSE_CONTINUE)
                cursor = self._one(piece, tok, cursor, close)

        e = terminator(analysis.terminator)
        piece.notes.append(Note(e.pitches, cursor, e.duration, e.velocity,
                                "종결", f"종결 {analysis.terminator}",
                                "맺음", -1))
        return piece

    def _one(self, piece: Piece, tok: Token, cursor: int, close: int) -> int:
        flag = 1 if tok.surface[:1].isupper() else 0
        c = self.concepts.of(self.lang, tok.form, tok.tag)
        if c is not None and c.form(self.lang) == (tok.form, tok.tag):
            g = encode(tok.role, Kind.CONCEPT, c.tier, c.quality, c.index,
                       close=close, polarity=c.polarity, flag=flag)
            return self._emit(piece, g, cursor, f"{tok} ≡{c}", tok.role)

        e = self.dict.get(tok.form, tok.tag)
        if e is not None:
            g = encode(tok.role, Kind.WORD, e.tier, e.quality, e.index,
                       lang=self.lang, close=close, polarity=e.polarity,
                       flag=flag)
            return self._emit(piece, g, cursor, str(tok), tok.role)

        # 형태소 하나를 받아 적을 때는 그 형태소의 꼴을 쓴다. 어절
        # 표면형을 쓰면 뒤따르는 조사와 겹쳐 같은 글자가 두 번 나온다.
        return self._spell(piece, tok.role, tok.form, cursor, close, flag)

    def _spell(self, piece: Piece, role: Role, text: str,
               cursor: int, close: int, flag: int = 0) -> int:
        chars = [ch for ch in text
                 if alphabet.to_index(self.lang, ch) is not None] or ["?"]
        for j, ch in enumerate(chars):
            last = j == len(chars) - 1
            g = encode(role, Kind.LETTER, -1, Quality.NEUTRAL,
                       alphabet.to_index(self.lang, ch), lang=self.lang,
                       close=close if last else C.CLOSE_CONTINUE,
                       flag=flag if j == 0 else 0)
            cursor = self._emit(piece, g, cursor, f"글자 {ch}", role)
        return cursor

    @staticmethod
    def _emit(piece: Piece, g: Glyph, cursor: int, label: str,
              role: Role) -> int:
        gi = len(piece.glyphs)
        piece.glyphs.append(g)
        piece.labels.append(label)
        for ev in g.events:
            piece.notes.append(Note(ev.pitches, cursor, ev.duration,
                                    ev.velocity, ev.slot, label,
                                    role.value, gi))
            cursor += ev.duration + ev.rest_after
        return cursor


def combine(pieces: list[Piece]) -> Piece:
    """여러 문장의 악보를 하나로 잇는다. 문장 사이는 종결 화음이 가른다."""
    if not pieces:
        return Piece(lang="ko")
    out = Piece(lang=pieces[0].lang, tempo=pieces[0].tempo,
                analysis=pieces[0].analysis)
    offset = 0
    for p in pieces:
        for n in sorted(p.notes, key=lambda x: x.start):
            out.notes.append(Note(n.pitches, n.start + offset, n.duration,
                                  n.velocity, n.slot, n.source, n.role,
                                  n.glyph))
        out.glyphs.extend(p.glyphs)
        out.labels.extend(p.labels)
        offset = out.length + 4
    return out
