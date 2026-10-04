import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))

from fakeworld import from_stamp
from watchdog import reversed_inserter


def test_reversed_inserter_is_caught():
    # furnace -> inserter -> chest, as the copper smelter was planned
    ents, codes = from_stamp("F.F.i>c.\nF.F.....\n")
    ins = next(e for e in ents if e["type"] == "inserter")
    codes = {k: v for k, v in codes.items()}
    assert not reversed_inserter(ins, codes)
    ins["drop"], ins["pickup"] = ins["pickup"], ins["drop"]   # replaced facing the wrong way
    assert reversed_inserter(ins, codes)
