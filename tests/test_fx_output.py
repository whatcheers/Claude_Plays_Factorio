import fx
from fx import build_summary, judge


def ent(i, typ, status, tile=(0, 0), **kw):
    return dict({"index": i, "name": typ, "type": typ, "ghost": False, "tile": list(tile), "status": status}, **kw)


def test_build_summary_counts_by_name():
    assert build_summary(["transport-belt", "inserter", "transport-belt"]) == "built 3: 2 transport-belt, 1 inserter"


def test_terse_prove_hides_machines_ok_in_every_sample():
    samples = [[ent(1, "furnace", "working"), ent(2, "lab", "working", tile=(5, 5))]] * 3
    lines, bad = judge(samples, verbose=False)
    assert bad == [] and lines == []
    full, _ = judge(samples)
    assert any("ok in 3/3" in l for l in full) and any(": working" in l for l in full)


def test_terse_prove_keeps_flaky_machines_and_problems():
    samples = [[ent(1, "furnace", s), ent(2, "lab", "working", tile=(5, 5))] for s in ("working", "no_fuel", "working")]
    lines, bad = judge(samples, verbose=False)
    assert bad == [] and lines == ["  0,0 furnace: ok in 2/3 samples"]
    ghost = dict(ent(3, "inserter", None, tile=(1, 1)), ghost=True)
    lines, bad = judge([[ghost]], verbose=False)
    assert bad and lines == ["  1,1 inserter: still a ghost"]


def test_terse_prove_keeps_empty_output_container():
    ins = ent(1, "inserter", "working", drop=[2.5, 0.5])
    chest = ent(2, "wooden-chest", None, tile=(2, 0), type="container")
    lines, bad = judge([[ins, chest]], verbose=False)
    assert bad and any("wooden-chest" in l for l in lines)


def test_verbose_flag_parses(monkeypatch):
    seen = {}

    class NoBridge:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

    monkeypatch.setattr(fx, "Bridge", NoBridge)
    monkeypatch.setattr(fx, "cmd_status", lambda b, a: seen.setdefault("v", fx.VERBOSE))
    monkeypatch.delenv("FX_VERBOSE", raising=False)
    assert fx.main(["-v", "status"]) == 0 and seen.pop("v") is True
    assert fx.main(["status"]) == 0 and seen.pop("v") is False
