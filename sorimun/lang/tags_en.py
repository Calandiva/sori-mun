"""영어 품사 체계.

한국어의 세종 체계와 짝이 맞도록 간추렸다. 두 언어가 같은 여덟 자리를
쓰므로, 품사에서 자리로 가는 길만 언어마다 다르다.
"""

from __future__ import annotations

NN = "NN"    # 명사
NNP = "NNP"  # 고유명사
PRP = "PRP"  # 대명사
VB = "VB"    # 동사
MD = "MD"    # 조동사
JJ = "JJ"    # 형용사
RB = "RB"    # 부사
DT = "DT"    # 한정사·관사
IN = "IN"    # 전치사
CC = "CC"    # 접속사
UH = "UH"    # 감탄사
CD = "CD"    # 수사
TO = "TO"    # to
POSS = "POSS"  # 소유격 's
NEG = "NEG"  # not / n't
EX = "EX"    # there (존재)
WP = "WP"    # wh- 낱말

KOREAN_NAME = {
    NN: "명사", NNP: "고유명사", PRP: "대명사", VB: "동사", MD: "조동사",
    JJ: "형용사", RB: "부사", DT: "한정사", IN: "전치사", CC: "접속사",
    UH: "감탄사", CD: "수사", TO: "to", POSS: "소유격", NEG: "부정",
    EX: "there", WP: "wh-낱말",
}
ENGLISH_NAME = {
    NN: "noun", NNP: "proper noun", PRP: "pronoun", VB: "verb",
    MD: "auxiliary", JJ: "adjective", RB: "adverb", DT: "determiner",
    IN: "preposition", CC: "conjunction", UH: "interjection", CD: "numeral",
    TO: "to", POSS: "possessive", NEG: "negation", EX: "existential there",
    WP: "wh-word",
}

CONTENT = {NN, NNP, PRP, VB, JJ, RB, UH, CD, EX, WP}
GRAMMATICAL = {DT, IN, CC, MD, TO, POSS, NEG}
NOMINAL = {NN, NNP, PRP, EX, WP}

# Moby Part-of-Speech 의 낱자 코드를 우리 체계로 옮긴다.
MOBY = {
    "N": NN, "p": NN, "h": NN, "o": PRP,
    "V": VB, "t": VB, "i": VB,
    "A": JJ, "v": RB, "C": CC, "P": IN, "!": UH, "r": PRP,
    "D": DT, "I": DT,
}

# 닫힌 부류는 손으로 못박는다. 실제 문장에서 가장 자주 나오고, 자리를
# 가르는 데 결정적이라 사전 추정에 맡기지 않는다.
CLOSED: dict[str, str] = {}
def _fill(tag: str, words: str) -> None:
    for w in words.split():
        CLOSED[w] = tag

_fill(DT, "the a an this that these those each every some any no all both "
          "half either neither another such what which whose my your his her "
          "its our their")
_fill(PRP, "i you he she it we they me him us them myself yourself himself "
           "herself itself ourselves yourselves themselves mine yours hers "
           "ours theirs one oneself")
# be·have·do 는 기본적으로 동사다. 뒤에 또 다른 동사가 올 때만 조동사가
# 된다 ("is singing"). 그래야 "Love is strong" 의 is 가 서술어 자리를 갖는다.
_fill(VB, "am is are was were be been being do does did have has had "
          "'m 're 've 'd")
_fill(MD, "can could will would shall should may might must ought "
          "need dare 'll")
_fill(IN, "of in to for with on at by from up about into over after beneath "
          "under above across against along among around before behind below "
          "beside besides between beyond during except inside near off onto "
          "outside past since through throughout toward towards underneath "
          "until upon via within without than like")
_fill(CC, "and but or nor yet so for because although though while whereas "
          "if unless whether since as when where")
_fill(RB, "not never always often sometimes rarely seldom very quite too also "
          "just only even still already yet again once twice here there now "
          "then soon later well badly slowly quickly really almost nearly "
          "perhaps maybe indeed however therefore thus rather much more most "
          "less least far away back down out up off ever")
_fill(UH, "oh ah oops wow hey hi hello alas ouch huh hmm yes no yeah nope "
          "okay ok please thanks bravo")
_fill(WP, "who whom whose what which when where why how")
_fill(CD, "zero one two three four five six seven eight nine ten eleven "
          "twelve thirteen fourteen fifteen sixteen seventeen eighteen "
          "nineteen twenty thirty forty fifty sixty seventy eighty ninety "
          "hundred thousand million billion first second third")
# 'her' 는 한정사(her hand)이자 목적격 대명사(loves her)다. 두 읽기를
# 다 주고 비터비가 고르게 한다.
_AMBIGUOUS_PRP = ("her",)
CLOSED["to"] = TO
CLOSED["not"] = NEG
CLOSED["n't"] = NEG
CLOSED["there"] = EX
CLOSED["'s"] = POSS

BE = {"am", "is", "are", "was", "were", "be", "been", "being",
      "'m", "'re", "'s"}
AUXVERB = BE | {"do", "does", "did", "have", "has", "had", "'ve", "'d"}

# 낱말이 여럿에 걸릴 때 기울 쪽. 문맥 점수의 바탕값이 된다.
PRIOR = {NN: 3, VB: 2, JJ: 2, RB: 1, NNP: 0, PRP: 0, CD: 0,
         DT: 0, IN: 0, CC: 0, MD: 0, UH: -1, TO: 0, POSS: 0,
         NEG: 0, EX: 0, WP: 0}

# 연결동사 — 뒤에 오는 것은 목적어가 아니라 보어다.
COPULA = {
    "be", "am", "is", "are", "was", "were", "been", "being", "become",
    "becomes", "became", "becoming", "seem", "seems", "seemed", "appear",
    "appears", "appeared", "remain", "remains", "remained", "stay", "stays",
    "stayed", "feel", "feels", "felt", "look", "looks", "looked", "sound",
    "sounds", "sounded", "get", "gets", "got", "turn", "turns", "turned",
    "grow", "grows", "grew",
}

# 끝소리로 품사를 가늠한다. 사전에 없을 때만 쓴다.
SUFFIX = (
    ("ness", NN), ("ment", NN), ("tion", NN), ("sion", NN), ("ity", NN),
    ("ance", NN), ("ence", NN), ("ship", NN), ("hood", NN), ("ism", NN),
    ("ist", NN), ("er", NN), ("or", NN),
    ("ly", RB),
    ("ous", JJ), ("ful", JJ), ("less", JJ), ("ive", JJ), ("able", JJ),
    ("ible", JJ), ("al", JJ), ("ic", JJ), ("ish", JJ), ("y", JJ),
    ("ize", VB), ("ise", VB), ("ify", VB), ("ate", VB),
    ("ing", VB), ("ed", VB),
)


# ── 품사 이음 점수 ───────────────────────────────────────────────────
# 앞 품사에서 뒤 품사로 이어질 만한 정도. 비터비로 문장 전체에서 가장
# 그럴듯한 이음을 고른다. 앞뒤만 보고 하나씩 정하면 'he sings' 의 sings
# 가 명사가 되는 식으로 오류가 연쇄한다.
_T: dict[str, dict[str, int]] = {
    "^":  {NN: 2, NNP: 2, PRP: 4, DT: 4, JJ: 1, RB: 2, UH: 3, WP: 3,
           MD: 2, EX: 2, IN: 1, CD: 1, VB: -4, TO: -3, POSS: -6, NEG: -3},
    DT:   {NN: 6, JJ: 5, CD: 3, NNP: 4, RB: 1, VB: -6, PRP: -4, DT: -6,
           IN: -4, MD: -5, TO: -5},
    JJ:   {NN: 7, JJ: 4, NNP: 4, CD: 2, IN: 1, CC: 1, VB: -2, DT: -3},
    NN:   {VB: 5, IN: 4, MD: 4, CC: 2, NN: 1, RB: 2, POSS: 3, TO: 1,
           DT: -4, JJ: -3, PRP: -3},
    NNP:  {VB: 5, IN: 4, MD: 4, CC: 2, NNP: 2, NN: 1, POSS: 3, DT: -4, JJ: -3},
    PRP:  {VB: 6, MD: 5, RB: 2, IN: 2, CC: 1, NN: -5, JJ: -4, DT: -4},
    VB:   {DT: 5, NN: 3, PRP: 6, IN: 4, RB: 5, JJ: 3, TO: 3, CD: 2,
           NNP: 3, VB: -3, MD: -2},
    # 계사 뒤는 형용사 자리다 — "is strong", "was dark". 보통 동사와
    # 갈라 두지 않으면 "walked together" 의 together 까지 형용사가 된다.
    "BE": {JJ: 7, NN: 4, DT: 4, RB: 3, IN: 3, VB: 2, CD: 2, NNP: 3},
    MD:   {VB: 7, RB: 3, NEG: 4, DT: -1, NN: -3, JJ: -2, PRP: 1},
    IN:   {DT: 5, NN: 4, PRP: 4, JJ: 3, NNP: 4, CD: 2, VB: -5, MD: -4},
    RB:   {VB: 5, JJ: 4, RB: 2, DT: 2, IN: 2, MD: 2, NN: -1},
    TO:   {VB: 8, DT: 2, NN: -2, JJ: -2},
    CC:   {NN: 3, DT: 3, PRP: 3, VB: 3, JJ: 3, NNP: 3, RB: 2},
    UH:   {NN: 2, DT: 2, PRP: 3, VB: -1, JJ: 1, WP: 1},
    CD:   {NN: 5, JJ: 2, IN: 2, VB: 1},
    POSS: {NN: 6, JJ: 4, NNP: 3, VB: -4},
    NEG:  {VB: 5, JJ: 3, RB: 2, DT: 2, NN: -1},
    EX:   {VB: 5, MD: 4, NN: -3},
    WP:   {VB: 4, MD: 5, PRP: 2, NN: 1, JJ: 1, DT: 2},
}


def transition(prev: str, nxt: str) -> int:
    return _T.get(prev, {}).get(nxt, 0)


# ── 굴절형 품사 넓히기 ───────────────────────────────────────────────
# Moby 는 굴절형을 '고립형으로 무엇이 될 수 있는가' 로만 싣는다.
# touched 는 형용사로만, sings 는 아예 없다. 그대로 두면 동사 읽기를
# 잃어버려 문장이 통째로 어긋난다. 그래서 밑말을 되짚어 품사를 넓힌다.
def _stems(word: str):
    w = word
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y", ("VB", "NN")
    if w.endswith("es") and len(w) > 3:
        yield w[:-2], ("VB", "NN")
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        yield w[:-1], ("VB", "NN")
    if w.endswith("ed") and len(w) > 3:
        yield w[:-2], ("VB", "JJ")
        yield w[:-1], ("VB", "JJ")                      # loved → love
        if len(w) > 4 and w[-3] == w[-4]:
            yield w[:-3], ("VB", "JJ")                  # stopped → stop
    if w.endswith("ing") and len(w) > 4:
        yield w[:-3], ("VB",)
        yield w[:-3] + "e", ("VB",)                     # making → make
        if len(w) > 5 and w[-4] == w[-5]:
            yield w[:-4], ("VB",)                       # running → run
    if w.endswith(("er", "est")) and len(w) > 4:
        cut = 2 if w.endswith("er") else 3
        yield w[:-cut], ("JJ",)
        yield w[:-cut] + "e", ("JJ",)
    if w.endswith("ly") and len(w) > 4:
        yield w[:-2], ("RB",)


def derive(word: str, known) -> set[str]:
    """밑말이 사전에 있으면 굴절형에도 그 품사를 물려준다.

    known(stem) 이 그 밑말의 품사 집합을 낸다.
    """
    out: set[str] = set()
    for stem, gives in _stems(word):
        have = known(stem)
        if not have:
            continue
        for g in gives:
            if g == "RB":
                if JJ in have:
                    out.add(RB)
            elif g in have:
                out.add(g)
            elif g == JJ and VB in have:
                out.add(JJ)          # 과거분사는 형용사 노릇도 한다
    return out
