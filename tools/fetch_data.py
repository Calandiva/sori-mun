#!/usr/bin/env python3
"""원본 데이터를 내려받는다.

세 갈래를 쓴다.

  mecab-ko-dic  표제어와 품사. 조사(J.csv)가 기능별로 갈려 있어서
                같은 '이' 라도 주격/보격/관형격/부사격/보조사를
                각각 다른 항목으로 다룰 수 있다.  (Apache-2.0)
  FrequencyWords  OpenSubtitles 기반 한국어 어절 빈도.  (CC-BY-SA)
  KNU 한국어 감성사전  낱말의 긍정/부정 극성 -2 ~ +2.

내려받은 것은 data/raw/ 에 두며 저장소에는 넣지 않는다.
이 스크립트를 다시 돌리면 그대로 복원된다.
"""

from __future__ import annotations

import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

MECAB_BASE = "https://raw.githubusercontent.com/lindera/mecab-ko-dic/master"

# 쓸 품사 파일. 고유명사 더미(Person/Place/Wikipedia/Hanja/Foreign)는
# 표제어가 아니라 개체명 목록이라 뺀다.
MECAB_FILES = [
    "NNG.csv",    # 일반명사
    "NNP.csv",    # 고유명사
    "NNB.csv",    # 의존명사
    "NNBC.csv",   # 단위 의존명사
    "NP.csv",     # 대명사
    "NR.csv",     # 수사
    "VV.csv",     # 동사
    "VA.csv",     # 형용사
    "VX.csv",     # 보조용언
    "VCP.csv",    # 긍정지정사 (이다)
    "VCN.csv",    # 부정지정사 (아니다)
    "MM.csv",     # 관형사
    "MAG.csv",    # 일반부사
    "MAJ.csv",    # 접속부사
    "IC.csv",     # 감탄사
    "J.csv",      # 조사 전부 (JKS/JKO/JKG/JKB/JKC/JKV/JC/JX)
    "EP.csv",     # 선어말어미
    "EF.csv",     # 종결어미
    "EC.csv",     # 연결어미
    "ETM.csv",    # 관형형 전성어미
    "ETN.csv",    # 명사형 전성어미
    "XPN.csv",    # 체언 접두사
    "XSN.csv",    # 명사 파생 접미사
    "XSV.csv",    # 동사 파생 접미사
    "XSA.csv",    # 형용사 파생 접미사
    "XR.csv",     # 어근
    "CoinedWord.csv",  # 신조어
]

OTHER = {
    "frequency_ko.txt": (
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
        "master/content/2018/ko/ko_full.txt"
    ),
    "knu_sentiment.json": (
        "https://raw.githubusercontent.com/park1200656/KnuSentiLex/"
        "master/data/SentiWord_info.json"
    ),
}


def _ssl_context() -> ssl.SSLContext | None:
    """python.org 빌드는 CA 번들이 붙어 있지 않은 경우가 있다."""
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def _download(url: str, dest: Path) -> int:
    try:
        with urllib.request.urlopen(url, timeout=180, context=_ssl_context()) as r:
            data = r.read()
        dest.write_bytes(data)
        return len(data)
    except (urllib.error.URLError, ssl.SSLError):
        curl = shutil.which("curl")
        if not curl:
            raise
        subprocess.run(
            [curl, "-sSL", "--fail", "--max-time", "180", "-o", str(dest), url],
            check=True,
        )
        return dest.stat().st_size


def get(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  건너뜀 {dest.name} ({dest.stat().st_size:,}B)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  받는 중 {dest.name} … ", end="", flush=True)
    n = _download(url, dest)
    print(f"{n:,}B")


def main() -> int:
    print("mecab-ko-dic 표제어")
    for f in MECAB_FILES:
        get(f"{MECAB_BASE}/{f}", RAW / "mecab" / f)
    print("그 밖의 자료")
    for name, url in OTHER.items():
        get(url, RAW / name)
    print(f"\n완료 → {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
