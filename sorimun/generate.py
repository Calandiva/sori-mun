"""생성 — 개념과 자리에서 문장을 짓는다.

되읽기의 마지막 걸음이자, 소리가 하나의 말이 되는 지점이다. 소리에는
개념과 자리만 적혀 있으므로, 어느 말로 읽어 낼지는 여기서 정해진다.

    (사랑, 주어) (강하, 서술어)  →  한국어: 사랑이 강하다.
                                 →  영어:   love is strong.

조사와 어미, 관사와 어순은 그 말의 것이지 소리의 것이 아니다. 그래서
소리에 담지 않고 여기서 새로 짓는다. 영어로 적은 소리를 한국어로 읽어
낼 수 있는 까닭이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from .concepts import Concept
from .core import tags as KT
from .core.roles import Role
from .lang import inflect_en as INF
from .lang import tags_en as ET


@dataclass(frozen=True)
class RawWord:
    """받아 적힌 낱말 — 옮기지 않고 글자 그대로 나른다 (고유명사 등)."""

    text: str

    # Concept 과 같은 낯을 갖춰 생성기가 구별 없이 다루게 한다
    @property
    def ko_form(self):
        return self.text

    @property
    def ko_tag(self):
        return "RAW"

    @property
    def en_form(self):
        return self.text

    @property
    def en_tag(self):
        return "RAW"


@dataclass
class Chunk:
    """머리말 하나와 그것에 붙은 꾸밈말·문법."""

    role: Role
    head: Concept
    grams: list[str]
    mods: list[tuple[Concept, list[str]]]


def _chunks(items) -> list[Chunk]:
    """차례대로 읽으며 꾸밈말을 제 머리말에 붙인다.

    자리별로만 모으면 'sad songs' 의 sad 가 앞의 she 에 붙어
    '슬픈 그녀가 노래를' 이 되어 버린다. 꾸밈말은 반드시 바로 뒤에
    오는 머리말의 것이다.
    """
    bundled = _bundle(items)
    out: list[Chunk] = []
    pending: list[tuple[Concept, list[str]]] = []
    for role, c, grams in bundled:
        if role is Role.ADNOMINAL:
            pending.append((c, grams))
            continue
        out.append(Chunk(role, c, grams, pending))
        pending = []
    if pending:
        if out:
            out[-1].mods.extend(pending)
        else:
            c, g = pending[0]
            out.append(Chunk(Role.SUBJECT, c, g, pending[1:]))
    return out


def _bundle(items):
    """문법 개념을 바로 앞 낱말에 붙여 묶는다.

    소리에는 '어루만지다' 와 '과거' 가 나란히 적힌다. 어느 말로 읽든
    그 둘은 한 낱말로 합쳐져야 한다.

    다만 **같은 어절 안에서만** 붙인다. 붙일 낱말이 그 어절에 없으면
    (개념표에 없어 소리에서 빠진 경우) 그 문법은 버린다. 앞 어절의
    엉뚱한 낱말에 붙으면 '천천히 + 과거 = slowlied' 같은 것이 나온다.
    """
    out: list[list] = []
    orphan: list[str] = []      # 붙일 낱말을 아직 못 만난 문법
    for entry in items:
        role, c, group = entry if len(entry) == 3 else (*entry, 0)
        if c.en_tag == INF.TAG:
            if out and out[-1][3] == group:
                out[-1][2].append(c.en_form)
            else:
                # 'was dark' 처럼 계사가 개념이 아니어서 빠지면 시제가
                # 붙을 데를 잃는다. 다음 낱말로 넘겨 준다.
                orphan.append(c.en_form)
            continue
        out.append([role, c, orphan + [], group])
        orphan = []
    return [(r, c, g) for r, c, g, _grp in out]

# ── 한국어 ───────────────────────────────────────────────────────────
_ORDER_KO = (Role.INDEPENDENT, Role.ADNOMINAL, Role.SUBJECT, Role.COMPLEMENT,
             Role.ADVERBIAL, Role.OBJECT, Role.PREDICATE)


def _has_final(word: str) -> bool:
    """끝 글자에 받침이 있는가. 조사를 고르는 데 쓴다."""
    if not word:
        return False
    ch = word[-1]
    if not ("가" <= ch <= "힣"):
        return True
    return (ord(ch) - 0xAC00) % 28 != 0


def _particle(word: str, with_final: str, without: str) -> str:
    return with_final if _has_final(word) else without


def korean(items: list[tuple[Role, Concept]], terminator: str = ".",
           kiwi=None) -> str:
    """개념과 자리에서 한국어 문장을 짓는다."""
    chunks = _chunks(items)

    # 영어의 'is strong' 은 보어를 세우지만 한국어는 '강하다' 로 서술어를
    # 세운다. 서술어가 비어 있고 보어가 용언이면 그쪽을 서술어로 올린다.
    if not any(c.role is Role.PREDICATE for c in chunks):
        for c in chunks:
            if c.role is Role.COMPLEMENT and c.head.ko_tag in ("VA", "VV", "XR"):
                c.role = Role.PREDICATE     # "길고 힘들다" — 전부 올린다

    # 서술어가 여럿이면 (길다 + 힘들다) 마지막만 '다' 로 맺고 앞은
    # '고' 로 잇는다 — "길고 힘들다".
    preds = [c for c in chunks if c.role is Role.PREDICATE]
    out: list[str] = []
    for role in _ORDER_KO:
        for ch in chunks:
            if ch.role is not role or ch.head.ko_tag == "∅":
                continue
            for m, mg in ch.mods:
                if m.ko_tag != "∅":
                    out.append(_korean_one(m.ko_form, m.ko_tag,
                                           Role.ADNOMINAL, kiwi, mg))
            if ch.head.ko_tag == "RAW":
                out.append(_korean_raw(ch.head.ko_form, role))
            else:
                linking = (role is Role.PREDICATE and len(preds) > 1
                           and ch is not preds[-1])
                out.append(_korean_one(ch.head.ko_form, ch.head.ko_tag,
                                       role, kiwi, ch.grams,
                                       linking=linking))
    text = " ".join(x for x in out if x)
    return (text + terminator) if text else ""


def _korean_raw(text: str, role: Role) -> str:
    """받아 적힌 낱말 — 자리에 맞는 조사만 붙인다."""
    if role is Role.SUBJECT:
        return text + ("이" if _has_final(text) else "가")
    if role is Role.OBJECT:
        return text + ("을" if _has_final(text) else "를")
    if role is Role.ADNOMINAL:
        return text + "의"
    return text


# 주격에서 꼴이 바뀌는 대명사
_IRREGULAR_SUBJECT = {"나": "내가", "너": "네가", "저": "제가", "누구": "누가"}


def _korean_one(form: str, tag: str, role: Role, kiwi,
                grams: list[str] | None = None, linking: bool = False) -> str:
    grams = grams or []
    predicate = tag in KT.PREDICATE or tag == "XR"

    def join(morphs):
        if kiwi is None:
            return "".join(m[0] for m in morphs)
        try:
            return kiwi.join(morphs).replace(" ", "")
        except Exception:
            return "".join(m[0] for m in morphs)

    if INF.PLURAL in grams and not predicate:
        form = form + "들"
    pre: list[tuple[str, str]] = []
    if INF.PAST in grams:
        pre.append(("었", "EP"))
    if INF.WILL in grams:
        pre.append(("겠", "EP"))
    negate = INF.NOT in grams

    if role is Role.SUBJECT:
        if predicate:
            return join([(form, "VA" if tag == "VA" else "VV"), ("음", "ETN")]) \
                + _particle(form, "이", "가")
        if form in _IRREGULAR_SUBJECT:
            return _IRREGULAR_SUBJECT[form]
        return form + _particle(form, "이", "가")
    if role is Role.OBJECT:
        return form + _particle(form, "을", "를")
    if role is Role.COMPLEMENT:
        return form + _particle(form, "이", "가")
    if role is Role.PREDICATE:
        if predicate:
            base = tag if tag in ("VV", "VA") else "VV"
            morphs = [(form, base)]
            if negate:
                morphs += [("지", "EC"), ("않", "VX")]
            morphs += pre
            if linking:
                morphs.append(("고", "EC"))    # "길고 힘들다" 의 앞쪽
            else:
                # 동사의 현재 종결은 'ㄴ다/는다'. '부르다' 가 아니라 '부른다'.
                ending = ("ᆫ다" if (base == "VV" and not pre and not negate)
                          else "다")
                morphs.append((ending, "EF"))
            return join(morphs)
        if tag in ("NNG", "NNP", "XR"):
            # 명사 개념이 서술어 자리에 오면 하다-동사가 된다 — '사랑한다'.
            morphs = [(form, "NNG"), ("하", "XSV")]
            if negate:
                morphs += [("지", "EC"), ("않", "VX")]
            morphs += pre
            morphs.append(("ᆫ다", "EF") if not pre and not negate else ("다", "EF"))
            return join(morphs)
        head = form + _particle(form, "이", "")
        return head + ("었다" if INF.PAST in grams else "다")
    if role is Role.ADNOMINAL:
        if tag == "MM":
            return form
        if predicate:
            morphs = [(form, tag if tag in ("VV", "VA") else "VA")]
            morphs += pre + [("ᆫ", "ETM")]
            return join(morphs)
        return form + "의"
    if role is Role.ADVERBIAL:
        if tag in ("MAG", "MAJ"):
            return form
        if predicate:
            return join([(form, tag if tag in ("VV", "VA") else "VV"),
                         ("게", "EC")])
        return form + "에"
    return form


# ── 영어 ─────────────────────────────────────────────────────────────
_ORDER_EN = (Role.INDEPENDENT, Role.ADNOMINAL, Role.SUBJECT, Role.PREDICATE,
             Role.OBJECT, Role.COMPLEMENT, Role.ADVERBIAL)

_BE = "is"


_OBJECT_PRP = {"i": "me", "he": "him", "she": "her", "we": "us",
               "they": "them", "who": "whom"}


def _verbable(word: str) -> bool:
    """이 영어 낱말에 동사 읽기가 있는가."""
    from .dictionary import Dictionary
    try:
        return Dictionary.load("en").get(word, "VB") is not None
    except Exception:
        return False

# 영어에서 흔히 관사 없이 쓰는 낱말들. 'the love' 는 어색하다.
# 관사 없이 쓰는 것은 추상명사에 한한다. 'the water', 'the night' 은
# 자연스럽지만 'the love' 는 어색하다.
_NO_ARTICLE = {
    "love", "death", "life", "time", "peace", "war", "hope", "fear",
    "sadness", "joy", "beauty", "music", "money", "work", "blood", "air",
}


def english(items: list[tuple[Role, Concept]], terminator: str = ".") -> str:
    chunks = _chunks(items)
    # 서술어가 될 동사가 없는데 보어가 있으면 계사를 세워야 한다.
    # 'water · dark · 과거' 는 'The water darked' 가 아니라
    # 'The water was dark' 다.
    has_verb = any(c.role is Role.PREDICATE and c.head.en_tag == ET.VB
                   for c in chunks)

    # 한국어에는 수 일치가 없으므로 소리에도 없다. 영어로 낼 때 되살린다.
    subj = next((c for c in chunks if c.role is Role.SUBJECT), None)
    third_sg = bool(subj) and subj.head.en_form not in (
        "i", "you", "we", "they") and INF.PLURAL not in subj.grams

    parts: list[str] = []
    copula_done = False
    for role in _ORDER_EN:
        for ch in chunks:
            if ch.role is not role:
                continue
            head, tag, grams = ch.head.en_form, ch.head.en_tag, list(ch.grams)
            if tag == "RAW":
                parts.append(head)
                continue
            if role is Role.PREDICATE and tag == ET.NN and _verbable(head):
                tag = ET.VB      # 사랑하다 → loves (love 는 동사이기도 하다)
            if (role is Role.PREDICATE and tag == ET.VB and third_sg
                    and not ({INF.PAST, INF.THIRD, INF.ING, INF.WILL} & set(grams))):
                grams.append(INF.THIRD)
            if head == "" or tag == "∅":
                continue
            copular = (role is Role.PREDICATE and tag in (ET.JJ, ET.NN)) or (
                role is Role.COMPLEMENT and not has_verb and tag in (ET.JJ, ET.NN))
            if copular:
                # 병렬 — "is long and hard". 계사는 첫 번째만 세운다.
                if copula_done:
                    parts.append("and")
                else:
                    parts.append("was" if INF.PAST in grams else _BE)
                    copula_done = True
                if INF.NOT in grams:
                    parts.append("not")
                parts.append(head)
                continue
            if INF.WILL in grams:
                parts.append("will")
            if INF.NOT in grams and role is Role.PREDICATE:
                parts.append("did not" if INF.PAST in grams else "does not")
                parts.append(head)
                continue
            if role is Role.OBJECT and tag == ET.PRP:
                head = _OBJECT_PRP.get(head, head)    # loves her, not loves she
            if (role in (Role.SUBJECT, Role.OBJECT, Role.COMPLEMENT)
                    and tag == ET.NN and INF.PLURAL not in grams
                    and head not in _NO_ARTICLE):
                parts.append("the")
            for m, mg in ch.mods:
                if m.en_form and m.en_tag != "∅":
                    f = m.en_form
                    for g in mg:
                        if g in (INF.PAST, INF.PLURAL, INF.THIRD, INF.ING):
                            f = INF.apply(f, g)
                    parts.append(f)
            for g in grams:
                if g in (INF.PAST, INF.PLURAL, INF.THIRD, INF.ING):
                    head = INF.apply(head, g)
            parts.append(head)

    if not parts:
        return ""
    text = " ".join(parts)
    return text[:1].upper() + text[1:] + terminator
