from helpers import bridge, find_clear, fx, write_stamp


def test_build_relints_beyond_the_fingerprint(tmp_path):
    with bridge() as b:
        x, y = find_clear(b, 12, 1)
    for t in ("lt-ug", "lt-ugout"):
        fx("unplan", t)
    # the output half sits 5 tiles past the tag's bbox, outside the +4 fingerprint
    assert fx("plan", write_stamp(tmp_path, "U>\n", "out.txt"), x + 6, y, 0, "--tag", "lt-ugout")[0] == 0
    assert fx("plan", write_stamp(tmp_path, "b>u>\n", "in.txt"), x, y, 0, "--tag", "lt-ug")[0] == 0
    try:
        code, out = fx("lint", "lt-ug")
        assert code == 0, out
        assert fx("look", x - 1, y - 1, x + 2, y + 1)[0] == 0
        assert fx("shot", x + 1, y + 0.5, 1)[0] == 0
        fx("unplan", "lt-ugout")  # breaks the pair without touching the fingerprinted box
        code, out = fx("build", "lt-ug")
        assert code != 0 and "fresh lint" in out and "underground" in out, out
    finally:
        fx("unplan", "lt-ug")
        fx("unplan", "lt-ugout")


def test_prove_samples():
    for tag in ("copper", "e2e"):
        code, out = fx("prove", tag, 180)
        if "unknown tag" not in out:
            assert "(3 samples)" in out and "ok in" in out, out
            return
    raise AssertionError("no built smelter tag to prove")
