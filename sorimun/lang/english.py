"""영어 — 품사 붙이기와 문장 성분 판별.

한국어는 조사가 자리를 말하지만 영어는 어순과 기능어가 말한다. 그래서
길은 다르되 닿는 곳은 같다 — 두 언어가 같은 여덟 자리를 쓴다.

    the beautiful song  gently  touched  the dark night
     └관형어───────┘      └부사어┘  └서술어┘   └관형어──┘└목적어┘
          └주어(song)                              └목적어(night)

푸는 순서
    1. 낱말 가르기 — 줄임말은 갈라 둔다 (don't → do + n't)
    2. 품사 붙이기 — 닫힌 부류 표 → 사전 → 끝소리 어림, 그 뒤 앞뒤 문맥으로 고름
    3. 이름마디(NP) 묶기
    4. 으뜸동사를 찾고, 그 앞뒤로 자리를 매긴다

완전한 구문분석이 아니라 규칙 어림이다. 다만 결정적이므로 같은 문장은
언제나 같은 결과를 낸다 — 되읽기가 어긋나지 않는 데에는 그것으로 족하다.
"""

from __future__ import annotations

import csv
import gzip
import re
from pathlib import Path

from . import register
from ..core.roles import Role
from . import inflect_en as INF
from . import tags_en as E
from .base import Analysis, Token

LANG = "en"

LEX_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "build" / "lexicon_en.tsv.gz"

_TOKEN = re.compile(r"[A-Za-z][A-Za-z'\-]*|\d+(?:[.,]\d+)?|[^\sA-Za-z\d]")
_SUFFIX_CONTRACTIONS = ("n't", "'s", "'re", "'ve", "'ll", "'d", "'m")
_SENT_END = re.compile(r"(?<=[.!?])\s+")


def _load_lexicon() -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    if not LEX_PATH.exists():
        return tags
    with gzip.open(LEX_PATH, "rt", encoding="utf-8") as fh:
        for w, t, _n in csv.reader(fh, delimiter="\t"):
            tags.setdefault(w, []).append(t)
    return tags


class EnglishAnalyzer:
    lang = LANG
    _lex: dict[str, list[str]] | None = None

    def __init__(self) -> None:
        if EnglishAnalyzer._lex is None:
            EnglishAnalyzer._lex = _load_lexicon()
        self.lex = EnglishAnalyzer._lex

    # ── 1. 낱말 가르기 ──────────────────────────────────────────────
    def _tokenize(self, text: str) -> tuple[list[str], list[int], list[str], str]:
        """낱말, 덩이 번호, 원문 그대로의 꼴, 그리고 종결 부호."""
        words: list[str] = []
        groups: list[int] = []
        raws: list[str] = []
        term = "."
        for gi, raw in enumerate(text.split()):
            for piece in _TOKEN.findall(raw):
                if piece in ".?!":
                    term = piece
                    continue
                if not piece[0].isalnum():
                    # 문장 안쪽 기호는 앞말에 달아 둔다
                    words.append(piece)
                    groups.append(gi)
                    raws.append(piece)
                    continue
                low = piece.lower()
                cut = None
                for c in _SUFFIX_CONTRACTIONS:
                    if low.endswith(c) and len(low) > len(c):
                        cut = c
                        break
                if cut:
                    words.append(low[: -len(cut)])
                    groups.append(gi)
                    raws.append(piece[: -len(cut)])
                    words.append(cut)
                    groups.append(gi)
                    raws.append(piece[-len(cut):])
                else:
                    words.append(low)
                    groups.append(gi)
                    raws.append(piece)
        return words, groups, raws, term

    # ── 2. 품사 붙이기 ──────────────────────────────────────────────
    def _candidates(self, w: str) -> list[str]:
        if w and not w[0].isalnum():
            return ["SYM"]
        closed = E.CLOSED.get(w)
        if w == "her":
            return [E.DT, E.PRP]      # her hand / loves her
        if closed and w not in ("there", "that", "as", "since", "like",
                                "no", "so", "one", "back", "down", "out", "up"):
            return [closed]
        got = set(self.lex.get(w, []))
        got |= E.derive(w, lambda stem: set(self.lex.get(stem, ())))
        if closed:
            got.add(closed)
        # be·have·do 는 홀로 쓰면 동사, 뒤에 동사가 오면 조동사다.
        # 어느 쪽인지는 비터비가 문장 전체를 보고 고르게 둔다.
        if w in E.AUXVERB:
            got |= {E.VB, E.MD}
        if w in INF.IRREGULAR_PAST.values() or w in INF.IRREGULAR_PLURAL.values():
            # came, went, saw … 불규칙형은 사전이 동사로 싣지 않는 일이 잦다
            got.add(E.VB if w in INF.IRREGULAR_PAST.values() else E.NN)
        if got:
            return sorted(got)
        if w.isdigit():
            return [E.CD]
        for suf, tag in E.SUFFIX:
            if w.endswith(suf) and len(w) > len(suf) + 2:
                return [tag]
        return [E.NN]

    def _emission(self, w: str, t: str, first: bool) -> int:
        """이 낱말이 이 품사일 만한 정도."""
        sc = E.PRIOR.get(t, 0)
        if w == "her" and t == E.PRP:
            sc += 12         # 한정사 읽기(closed+lex)와 같은 무게를 준다
        if w in E.AUXVERB:
            # be·have·do 는 본동사와 조동사 둘 다 제값으로 놓고, 어느
            # 쪽인지는 이음 점수가 고르게 둔다. 한쪽에만 상을 주면
            # "has come" 의 has 가 영영 본동사로 굳는다.
            if t in (E.VB, E.MD):
                sc += 8
        elif E.CLOSED.get(w) == t:
            sc += 8
        if t in self.lex.get(w, ()):
            sc += 4
        # 감탄사 읽기는 문장 첫머리가 아니면 여간해서 아니다
        if t == E.UH and not first:
            sc -= 5
        for suf, guess in E.SUFFIX:
            if w.endswith(suf) and len(w) > len(suf) + 2:
                if guess == t:
                    sc += 3
                break
        if w.endswith("ly") and t == E.RB:
            sc += 4
        if w.endswith(("er", "est")) and t == E.JJ:
            sc += 2
        if first and t == E.VB:
            sc -= 2
        return sc

    def _viterbi(self, words: list[str], cands: list[list[str]]) -> tuple[list[str], int]:
        n = len(words)
        score: list[dict[str, int]] = []
        back: list[dict[str, str]] = []
        for i, w in enumerate(words):
            cur: dict[str, int] = {}
            bk: dict[str, str] = {}
            for t in cands[i]:
                em = self._emission(w, t, i == 0)
                if i == 0:
                    cur[t] = em + E.transition("^", t)
                    bk[t] = "^"
                else:
                    best_p, best_s = None, -10**9
                    for pt, ps in score[i - 1].items():
                        # 계사는 보통 동사와 다른 자리를 이끈다
                        key = ("BE" if pt == E.VB and words[i - 1] in E.BE
                               else pt)
                        v = ps + E.transition(key, t)
                        if v > best_s:
                            best_p, best_s = pt, v
                    cur[t] = em + best_s
                    bk[t] = best_p
            score.append(cur)
            back.append(bk)
        tags = [""] * n
        tags[-1] = max(score[-1], key=lambda t: score[-1][t])
        total = score[-1][tags[-1]]
        for i in range(n - 1, 0, -1):
            tags[i - 1] = back[i][tags[i]]
        return tags, total

    def _tag(self, words: list[str]) -> list[str]:
        """비터비로 품사를 붙인다.

        앞뒤만 보고 하나씩 정하면 오류가 연쇄한다 — 'he sings' 의 sings
        를 명사로 잘못 잡으면 he 까지 관형어가 되어 버린다. 그래서 낱말
        자체의 그럴듯함(emission)과 품사끼리의 이음(transition)을 더해
        문장 전체에서 가장 높은 길을 고른다.
        """
        n = len(words)
        if n == 0:
            return []
        cands = [self._candidates(w) for w in words]
        tags, _ = self._viterbi(words, cands)

        # 동사가 하나도 없으면, 동사가 될 수 있는 자리를 하나씩 못박아
        # 다시 풀고 가장 높은 길을 고른다. 첫 후보를 그냥 집으면
        # 'the spring came' 의 spring 이 동사가 되어 버린다.
        if not any(t in (E.VB, E.MD) for t in tags):
            best, best_score = tags, -10**9
            for i in range(n):
                if E.VB not in cands[i]:
                    continue
                forced = [list(c) for c in cands]
                forced[i] = [E.VB]
                got, sc = self._viterbi(words, forced)
                if sc > best_score:
                    best, best_score = got, sc
            tags = best

        # 조동사로 뽑혔는데 뒤에 본동사가 없으면 그 자신이 본동사다
        for i, w in enumerate(words):
            if tags[i] == E.MD and w in E.AUXVERB:
                if not any(tags[j] == E.VB and words[j] not in E.AUXVERB
                           for j in range(i + 1, n)):
                    tags[i] = E.VB

        # 'long and hard' — 접속사로 이어진 것은 앞쪽과 품사를 맞춘다
        for i in range(2, n):
            if tags[i - 1] == E.CC and tags[i - 2] in (E.JJ, E.RB, E.NN):
                if tags[i - 2] in cands[i] and tags[i] != tags[i - 2]:
                    tags[i] = tags[i - 2]

        # 문장 끝에 동사가 또 오는 일은 드물다. 앞에 이미 동사가 있고
        # 형용사로도 읽힌다면 형용사로 본다 — "piled up white".
        if (n >= 2 and tags[-1] == E.VB and E.JJ in cands[-1]
                and not words[-1].endswith(("ing", "ed"))):
            if any(t == E.VB for t in tags[:-1]):
                tags[-1] = E.JJ
        return tags

    # ── 3~4. 자리 매기기 ────────────────────────────────────────────
    def _roles(self, words: list[str], tags: list[str]) -> list[Role]:
        n = len(words)
        roles: list[Role] = [Role.ADVERBIAL] * n

        # 으뜸동사 — to 앞선 것은 빼고 가장 먼저 나오는 동사
        verb = None
        for i, t in enumerate(tags):
            if t == E.VB and (i == 0 or tags[i - 1] != E.TO):
                verb = i
                break
        if verb is None:
            for i, t in enumerate(tags):
                if t == E.MD:
                    verb = i
                    break
        copula = verb is not None and words[verb] in E.COPULA

        # 의문문은 어순이 뒤집힌다 — "are you going?" 의 주어는 동사 뒤다.
        inverted = bool(words) and (
            tags[0] == E.MD
            or (tags[0] == E.WP and len(tags) > 1 and tags[1] in (E.MD, E.VB))
        )

        # 이름마디의 머리 — 이어지는 체언 무리의 마지막
        head = [False] * n
        i = 0
        while i < n:
            if tags[i] in E.NOMINAL:
                j = i
                while j + 1 < n and tags[j + 1] in E.NOMINAL:
                    j += 1
                head[j] = True
                i = j + 1
            else:
                i += 1

        prep_open = False       # 전치사 뒤 이름마디 안인가
        subject_taken = False
        for i, t in enumerate(tags):
            if t == E.UH:
                roles[i] = Role.INDEPENDENT
            elif t in E.GRAMMATICAL:
                roles[i] = Role.MARKER
                if t == E.IN:
                    prep_open = True
            elif t == E.RB:
                roles[i] = Role.ADVERBIAL
            elif t == E.VB:
                roles[i] = Role.PREDICATE
                prep_open = False
            elif t in (E.JJ, E.CD):
                nxt = tags[i + 1] if i + 1 < n else None
                if nxt in E.NOMINAL or nxt in (E.JJ, E.CD):
                    roles[i] = Role.ADNOMINAL
                elif copula and verb is not None and i > verb:
                    roles[i] = Role.COMPLEMENT
                else:
                    roles[i] = Role.ADNOMINAL
            elif t in E.NOMINAL:
                if t == E.WP and i == 0:
                    # who/what 은 주어 노릇, where/when/why/how 는 부사 노릇
                    roles[i] = (Role.SUBJECT if words[i] in ("who", "what")
                                else Role.ADVERBIAL)
                elif not head[i]:
                    roles[i] = Role.ADNOMINAL      # 이름마디 안의 꾸밈말
                elif prep_open:
                    roles[i] = Role.ADVERBIAL      # 전치사구는 부사 노릇
                elif verb is None:
                    roles[i] = Role.SUBJECT if i == 0 else Role.OBJECT
                elif inverted and not subject_taken:
                    roles[i] = Role.SUBJECT        # 뒤집힌 어순의 주어
                    subject_taken = True
                elif i < verb:
                    roles[i] = Role.SUBJECT
                    subject_taken = True
                else:
                    roles[i] = Role.COMPLEMENT if copula else Role.OBJECT
                if head[i]:
                    prep_open = False
            else:
                roles[i] = Role.ADVERBIAL
        return roles

    # ── 바깥에서 쓰는 것 ────────────────────────────────────────────
    def sentences(self, text: str) -> list[Analysis]:
        out = []
        for part in _SENT_END.split(text.strip()):
            if part.strip():
                out.append(self.analyze(part.strip()))
        return out

    def analyze(self, text: str) -> Analysis:
        words, groups, raws, term = self._tokenize(text)
        if not words:
            return Analysis(text=text, tokens=[], terminator=term, lang=LANG)
        tags = self._tag(words)
        roles = self._roles(words, tags)
        known = lambda f, t: t in self.lex.get(f, ())
        tokens: list[Token] = []
        for w, t, r, g, raw in zip(words, tags, roles, groups, raws):
            # 굴절은 밑말과 갈라 세운다. 한국어가 '어루만지 + 었' 으로
            # 서듯 영어도 'touch + «past»' 로 세워야 두 말이 같은 개념을
            # 나눠 가질 수 있다.
            piece = INF.split(w, t, known) if t in (E.VB, E.NN) else None
            if piece is not None:
                base, gram = piece
                tokens.append(Token(base, t, r, g, raw))
                tokens.append(Token(gram, INF.TAG, Role.MARKER, g, ""))
            else:
                tokens.append(Token(w, t, r, g, raw))
        return Analysis(text=text, tokens=tokens, terminator=term, lang=LANG)

    def join(self, morphs: list[tuple[str, str]], groups: list[int]) -> str:
        """낱말에서 문장을 되짓는다. 영어는 표면형을 그대로 실으므로 정확하다."""
        if not morphs:
            return ""
        out: list[str] = []
        cur = ""
        g0 = groups[0]
        for (form, tag), g in zip(morphs, groups):
            if tag == INF.TAG:
                # 굴절은 바로 앞 낱말에 붙는다
                cur = INF.apply(cur, form) if cur else form
                continue
            if g != g0:
                out.append(cur)
                cur, g0 = form, g
            else:
                cur += form
        out.append(cur)
        return " ".join(x for x in out if x)


register(LANG, EnglishAnalyzer)
