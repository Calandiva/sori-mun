"""문장 분석 — 형태소에서 문장 성분으로.

낱말을 사전에서 찾기 전에, 그 낱말이 문장에서 무슨 자리를 맡는지부터
가린다. 같은 '밤' 이라도 '밤이 왔다' 의 밤(주어)과 '밤을 새웠다' 의
밤(목적어)은 다른 높이로 울려야 하기 때문이다.

절차
    형태소 분석(kiwi)  →  어절 묶기  →  성분 판별

성분 판별은 조사와 어미가 거의 결정한다. 한국어에서 문장 성분을
드러내는 것이 바로 그것들이기 때문이다.

    체언 + 이/가(JKS)      주어
    체언 + 을/를(JKO)      목적어
    체언 + 이/가(JKC)      보어      (되다·아니다 앞)
    체언 + 의(JKG)         관형어
    체언 + 에/에서(JKB)    부사어
    체언 + 아/야(JKV)      독립어
    용언 + 은/는/을(ETM)   관형어
    용언 + 다/까(EF)       서술어
    관형사(MM)             관형어
    부사(MAG/MAJ)          부사어
    감탄사(IC)             독립어

조사가 없거나 보조사(은/는)뿐일 때는 자리로 미룬다. 완전한 구문분석이
아니라 규칙 어림이며, 어림한 자리는 `guessed` 로 표시해 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tags as T
from .tags import Role


@dataclass(frozen=True, slots=True)
class Morph:
    """형태소 하나."""

    form: str
    tag: str
    start: int
    length: int

    @property
    def key(self) -> tuple[str, str]:
        return (self.form, self.tag)

    def __str__(self) -> str:
        return f"{self.form}/{self.tag}"


@dataclass(slots=True)
class Eojeol:
    """어절 하나 — 띄어쓰기로 갈리는 덩이."""

    surface: str
    morphs: list[Morph]
    role: Role = Role.ADVERBIAL
    guessed: bool = False          # 조사가 없어 자리를 어림했는가
    modifies: int | None = None    # 관형어가 꾸미는 어절의 자리

    @property
    def content(self) -> list[Morph]:
        return [m for m in self.morphs if m.tag in T.CONTENT]

    @property
    def head(self) -> Morph | None:
        """의미의 중심. 한국어는 뒤가 중심이므로 마지막 내용 형태소."""
        c = self.content
        return c[-1] if c else None

    @property
    def particles(self) -> list[Morph]:
        return [m for m in self.morphs if m.tag in T.PARTICLE]

    @property
    def endings(self) -> list[Morph]:
        return [m for m in self.morphs if m.tag in T.ENDING]

    def has(self, *tags: str) -> bool:
        return any(m.tag in tags for m in self.morphs)

    def last_particle(self) -> Morph | None:
        ps = self.particles
        return ps[-1] if ps else None


@dataclass(slots=True)
class Sentence:
    """문장 하나."""

    text: str
    eojeols: list[Eojeol] = field(default_factory=list)
    terminator: str = "."   # . ? ! …

    @property
    def morphs(self) -> list[Morph]:
        return [m for e in self.eojeols for m in e.morphs]


# ── 어절 묶기 ────────────────────────────────────────────────────────
def _group(text: str, tokens) -> list[Eojeol]:
    """형태소를 띄어쓰기 기준으로 어절에 담는다."""
    out: list[Eojeol] = []
    cur: list[Morph] = []
    cur_start = 0
    prev_end = -1

    for tok in tokens:
        tag = T.normalize(tok.tag)
        if tag in T.SYMBOL:
            continue
        m = Morph(tok.form, tag, tok.start, tok.len)
        gap = prev_end >= 0 and text[prev_end:tok.start].strip() != text[prev_end:tok.start]
        if cur and gap:
            out.append(Eojeol(text[cur_start:prev_end], cur))
            cur, cur_start = [], tok.start
        if not cur:
            cur_start = tok.start
        cur.append(m)
        prev_end = tok.start + tok.len

    if cur:
        out.append(Eojeol(text[cur_start:prev_end], cur))
    return out


# ── 성분 판별 ────────────────────────────────────────────────────────
_PARTICLE_ROLE = {
    "JKS": Role.SUBJECT,
    "JKO": Role.OBJECT,
    "JKC": Role.COMPLEMENT,
    "JKG": Role.ADNOMINAL,
    "JKB": Role.ADVERBIAL,
    "JKV": Role.INDEPENDENT,
    "JKQ": Role.ADVERBIAL,
}


def _classify(eojeols: list[Eojeol]) -> None:
    """각 어절에 문장 성분을 매긴다."""
    n = len(eojeols)

    # 1차: 조사·어미가 분명히 말해 주는 것부터
    for i, e in enumerate(eojeols):
        head = e.head
        if head is None:
            e.role = Role.ADVERBIAL
            e.guessed = True
            continue

        # 용언으로 끝나는 어절
        if head.tag in T.PREDICATE or e.has("XSV", "XSA"):
            if e.has("ETM"):
                e.role = Role.ADNOMINAL       # 관형절: 뒤 체언을 꾸민다
                e.modifies = i + 1 if i + 1 < n else None
                continue
            if e.has("ETN"):
                p = e.last_particle()
                e.role = _PARTICLE_ROLE.get(p.tag, Role.OBJECT) if p else Role.OBJECT
                continue
            if e.has("EF"):
                e.role = Role.PREDICATE
                continue
            if e.has("EC"):
                e.role = Role.PREDICATE       # 앞 절의 서술어
                continue
            e.role = Role.PREDICATE
            continue

        # 감탄사
        if head.tag == "IC":
            e.role = Role.INDEPENDENT
            continue

        # 관형사
        if head.tag == "MM":
            e.role = Role.ADNOMINAL
            e.modifies = i + 1 if i + 1 < n else None
            continue

        # 부사
        if head.tag in ("MAG", "MAJ"):
            e.role = Role.ADVERBIAL
            continue

        # 체언 — 조사가 결정한다
        if e.has("VCP", "VCN"):               # 체언 + 이다/아니다
            e.role = Role.PREDICATE
            continue

        p = e.last_particle()
        if p is not None and p.tag in _PARTICLE_ROLE:
            e.role = _PARTICLE_ROLE[p.tag]
            if e.role is Role.ADNOMINAL:
                e.modifies = i + 1 if i + 1 < n else None
            continue

        # 보조사(은/는/도/만)뿐이거나 조사가 아예 없다 → 자리로 어림한다
        e.role = Role.SUBJECT
        e.guessed = True

    # 2차: 어림한 것들을 문장 전체를 보고 고친다
    _refine(eojeols)


def _refine(eojeols: list[Eojeol]) -> None:
    """조사가 말해 주지 않은 자리를 문장 짜임으로 메운다."""
    explicit_subject = any(
        e.role is Role.SUBJECT and not e.guessed for e in eojeols
    )
    explicit_object = any(e.role is Role.OBJECT and not e.guessed for e in eojeols)
    used_subject = explicit_subject

    for i, e in enumerate(eojeols):
        if not e.guessed:
            continue
        head = e.head
        if head is None or head.tag not in T.SUBSTANTIVE:
            e.role = Role.ADVERBIAL
            continue

        # 보조사 '은/는' 은 주제를 세운다. 다만 뒤에 진짜 주어(이/가)가
        # 따로 있으면 이쪽은 주어가 아니다 — "밥은 내가 먹었다".
        if explicit_subject:
            e.role = Role.OBJECT if not explicit_object else Role.ADVERBIAL
            continue

        # 아직 주어가 없다면 첫 체언 어절이 주어를 맡는다.
        if not used_subject:
            e.role = Role.SUBJECT
            used_subject = True
            continue

        # 그 다음은 목적어, 또 그 다음은 부사어.
        if not explicit_object:
            e.role = Role.OBJECT
            explicit_object = True
        else:
            e.role = Role.ADVERBIAL


# ── 바깥에서 쓰는 것 ─────────────────────────────────────────────────
class Analyzer:
    """한국어 문장을 형태소·어절·성분으로 푼다."""

    def __init__(self) -> None:
        try:
            from kiwipiepy import Kiwi
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "형태소 분석에는 kiwipiepy 가 필요하다:  pip install kiwipiepy"
            ) from exc
        self._kiwi = Kiwi(num_workers=-1)

    def sentences(self, text: str) -> list[Sentence]:
        """글을 문장 단위로 갈라 각각 분석한다."""
        out = []
        for s in self._kiwi.split_into_sents(text):
            body = s.text.strip()
            if not body:
                continue
            out.append(self.analyze(body))
        return out or ([self.analyze(text.strip())] if text.strip() else [])

    def analyze(self, text: str) -> Sentence:
        tokens = list(self._kiwi.tokenize(text))
        term = "."
        for tok in reversed(tokens):
            if T.normalize(tok.tag) == "SF":
                term = tok.form
                break
        eojeols = _group(text, tokens)
        _classify(eojeols)
        return Sentence(text=text, eojeols=eojeols, terminator=term)
