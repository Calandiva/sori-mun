import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def dictionary():
    from sorimun.dictionary import Dictionary
    return Dictionary()


@pytest.fixture(scope="session")
def analyzer():
    from sorimun.core.analyze import Analyzer
    return Analyzer()


@pytest.fixture(scope="session")
def composer(dictionary):
    from sorimun.compose import Composer
    return Composer(dictionary)
