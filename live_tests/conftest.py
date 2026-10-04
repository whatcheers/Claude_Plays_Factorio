import pytest

from helpers import fx


@pytest.fixture(autouse=True, scope="session")
def claude_character():
    code, out = fx("spawn")
    assert code == 0, out
