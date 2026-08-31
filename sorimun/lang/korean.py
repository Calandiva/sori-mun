"""한국어 — 형태소 분석과 문장 성분 판별.

조사와 어미가 자리를 거의 결정한다. 한국어에서 문장 성분을 드러내는
것이 바로 그것들이기 때문이다.

    체언 + 이/가(JKS)      주어        용언 + 다/까(EF)      서술어
    체언 + 을/를(JKO)      목적어      용언 + 은/는/을(ETM)  관형어
    체언 + 이/가(JKC)      보어        관형사(MM)            관형어
    체언 + 의(JKG)         관형어      부사(MAG/MAJ)         부사어
    체언 + 에/에서(JKB)    부사어      감탄사(IC)            독립어
    체언 + 아/야(JKV)      독립어      조사·어미 자신        표지

조사가 없거나 보조사(은/는)뿐이면 문장 짜임으로 어림한다. 완전한
구문분석이 아니라 규칙 어림이며, 어림한 자리는 표시해 둔다.
"""

from __future__ import annotations

from . import base, register
from ..core.roles import Role
from ..core import tags as T
from .base import Analysis, Token

LANG = "ko"

_PARTICLE_ROLE = {
    "JKS": Role.SUBJECT,
    "JKO": Role.OBJECT,
    "JKC": Role.COMPLEMENT,
    "JKG": Role.ADNOMINAL,
    "JKB": Role.ADVERBIAL,
    "JKV": Role.INDEPENDENT,
    "JKQ": Role.ADVERBIAL,
}


class _Chunk:
    """어절 하나 — 띄어쓰기로 갈리는 덩이."""

    __slots__ = ("morphs", "role", "guessed", "surface")

    def __init__(self, morphs, surface):
        self.morphs = morphs           # [(form, tag)]
        self.surface = surface
        self.role = Role.ADVERBIAL
        self.guessed = False

    @property
    def content(self):
        return [m for m in self.morphs if m[1] in T.CONTENT]

    @property
    def head(self):
        c = self.content
        return c[-1] if c else None

    def has(self, *tags):
        return any(m[1] in tags for m in self.morphs)

    def last_particle(self):
        ps = [m for m in self.morphs if m[1] in T.PARTICLE]
        return ps[-1] if ps else None


def _classify(chunks: list[_Chunk]) -> None:
    n = len(chunks)
    for i, e in enumerate(chunks):
        head = e.head
        if head is None:
            e.role, e.guessed = Role.ADVERBIAL, True
            continue
        tag = head[1]

        if tag in T.PREDICATE or e.has("XSV", "XSA"):
            if e.has("ETM"):
                e.role = Role.ADNOMINAL
            elif e.has("ETN"):
                p = e.last_particle()
                e.role = _PARTICLE_ROLE.get(p[1], Role.OBJECT) if p else Role.OBJECT
            else:
                e.role = Role.PREDICATE
            continue
        if tag == "IC":
            e.role = Role.INDEPENDENT
            continue
        if tag == "MM":
            e.role = Role.ADNOMINAL
            continue
        if tag in ("MAG", "MAJ"):
            e.role = Role.ADVERBIAL
            continue
        if e.has("VCP", "VCN"):
            e.role = Role.PREDICATE
            continue

        p = e.last_particle()
        if p is not None and p[1] in _PARTICLE_ROLE:
            e.role = _PARTICLE_ROLE[p[1]]
            continue

        e.role, e.guessed = Role.SUBJECT, True

    _refine(chunks)


def _refine(chunks: list[_Chunk]) -> None:
    """조사가 말해 주지 않은 자리를 문장 짜임으로 메운다."""
    explicit_subject = any(c.role is Role.SUBJECT and not c.guessed for c in chunks)
    explicit_object = any(c.role is Role.OBJECT and not c.guessed for c in chunks)
    used_subject = explicit_subject

    for c in chunks:
        if not c.guessed:
            continue
        head = c.head
        if head is None or head[1] not in T.SUBSTANTIVE:
            c.role = Role.ADVERBIAL
            continue
        # 보조사 '은/는' 은 주제를 세운다. 다만 뒤에 진짜 주어가 따로
        # 있으면 이쪽은 주어가 아니다 — "밥은 내가 먹었다".
        if explicit_subject:
            c.role = Role.OBJECT if not explicit_object else Role.ADVERBIAL
            continue
        if not used_subject:
            c.role, used_subject = Role.SUBJECT, True
            continue
        if not explicit_object:
            c.role, explicit_object = Role.OBJECT, True
        else:
            c.role = Role.ADVERBIAL


class KoreanAnalyzer:
    """kiwipiepy 로 형태소를 가르고, 조사·어미로 자리를 매긴다."""

    lang = LANG

    def __init__(self) -> None:
        try:
            from kiwipiepy import Kiwi
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "한국어 분석에는 kiwipiepy 가 필요하다:  pip install kiwipiepy"
            ) from exc
        self._kiwi = Kiwi(num_workers=-1)

    # ── 분석 ────────────────────────────────────────────────────────
    def sentences(self, text: str) -> list[Analysis]:
        out = []
        for s in self._kiwi.split_into_sents(text):
            body = s.text.strip()
            if body:
                out.append(self.analyze(body))
        if out:
            return out
        return [self.analyze(text.strip())] if text.strip() else []

    def analyze(self, text: str) -> Analysis:
        toks = list(self._kiwi.tokenize(text))
        term = "."
        for t in reversed(toks):
            if T.normalize(t.tag) == "SF":
                term = t.form if t.form in (".", "?", "!") else "."
                break

        chunks: list[_Chunk] = []
        marks: dict[int, list[str]] = {}   # 어절 뒤에 붙는 문장부호
        cur: list[tuple[str, str]] = []
        cur_start = 0
        prev_end = -1
        for t in toks:
            tag = T.normalize(t.tag)
            if tag in T.SYMBOL:
                # 문장 끝 부호는 종결 화음이 맡는다. 문장 안쪽 부호(쉼표
                # 따위)는 앞 어절에 달아 두어야 원문이 그대로 돌아온다.
                if tag != "SF" and t.form.strip():
                    idx = len(chunks) if cur else max(0, len(chunks) - 1)
                    marks.setdefault(idx, []).append(t.form)
                continue
            gap = prev_end >= 0 and text[prev_end:t.start] != text[prev_end:t.start].strip()
            if cur and gap:
                chunks.append(_Chunk(cur, text[cur_start:prev_end]))
                cur, cur_start = [], t.start
            if not cur:
                cur_start = t.start
            cur.append((t.form, tag))
            prev_end = t.start + t.len
        if cur:
            chunks.append(_Chunk(cur, text[cur_start:prev_end]))

        _classify(chunks)

        tokens: list[Token] = []
        for gi, c in enumerate(chunks):
            for form, tag in c.morphs:
                # 조사와 어미는 그 자체가 표지다. 내용 형태소만 어절의
                # 자리를 물려받는다.
                role = Role.MARKER if tag in T.GRAMMATICAL else c.role
                first = not tokens or tokens[-1].group != gi
                tokens.append(Token(form=form, tag=tag, role=role, group=gi,
                                    surface=c.surface if first else ""))
            for mk in marks.get(gi, []):
                # 표면형을 실어 두어야 '철수야,' 가 원문 그대로 되지어졌는지
                # 셈할 수 있다.
                tokens.append(Token(form=mk, tag="SYM", role=Role.MARKER,
                                    group=gi, surface=mk))
        return Analysis(text=text, tokens=tokens, terminator=term, lang=LANG)

    # ── 되짓기 ──────────────────────────────────────────────────────
    def join(self, morphs: list[tuple[str, str]], groups: list[int]) -> str:
        """형태소에서 문장을 되짓는다.

        kiwi 의 역생성을 쓴다. 활용과 축약이 원문 그대로 돌아온다 —
        '아름답/VA + ᆫ/ETM' 이 '아름다운' 이 된다.
        """
        if not morphs:
            return ""
        out: list[str] = []
        cur: list[tuple[str, str]] = []
        g0 = groups[0]
        for (form, tag), g in zip(morphs, groups):
            if g != g0:
                out.append(self._join_one(cur))
                cur, g0 = [], g
            cur.append((form, tag))
        if cur:
            out.append(self._join_one(cur))
        return " ".join(out)

    def _join_one(self, morphs: list[tuple[str, str]]) -> str:
        """어절 하나를 되짓는다.

        사전에 없어 글자로 받아 적은 것은 품사가 '?' 다. 그것은 역생성에
        넣지 않고 글자 그대로 이어 붙인다.
        """
        out = ""
        run: list[tuple[str, str]] = []

        def flush() -> str:
            # 어절은 띄어쓰기로 이미 갈린 덩이다. 역생성이 그 안에 넣는
            # 공백은 원문에 없던 것이므로 걷어낸다.
            return self._kiwi.join(run).replace(" ", "") if run else ""

        for form, tag in morphs:
            if tag in ("?", "SYM"):
                out += flush()
                run = []
                out += form
            else:
                run.append((form, tag))
        out += flush()
        return out


register(LANG, KoreanAnalyzer)
