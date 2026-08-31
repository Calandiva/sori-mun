import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KO_SENTENCES = [
    s for s in (ROOT / "data" / "sentences_ko.txt")
    .read_text(encoding="utf-8").split("\n") if s.strip()
]
EN_SENTENCES = [
    s for s in (ROOT / "data" / "sentences_en.txt")
    .read_text(encoding="utf-8").split("\n") if s.strip()
]


@pytest.fixture(scope="session")
def ko():
    from sorimun.lang import get
    return get("ko")


@pytest.fixture(scope="session")
def en():
    from sorimun.lang import get
    return get("en")


@pytest.fixture(scope="session")
def concepts():
    from sorimun.concepts import Concepts
    return Concepts.load()
