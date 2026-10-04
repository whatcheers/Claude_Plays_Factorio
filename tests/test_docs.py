import re

import fx


def test_claude_md_documents_setup_and_every_command():
    doc = open("CLAUDE.md", encoding="utf-8").read()
    for needle in ("mods\\claude-bridge", "local-rcon-socket", "local-rcon-password", "FACTORIO_RCON_PASSWORD", "Host new game"):
        assert needle in doc, needle
    commands = sorted(n[4:] for n in dir(fx) if n.startswith("cmd_"))
    assert len(commands) >= 15
    for c in commands:
        assert re.search(rf"`{c}\b", doc), f"CLAUDE.md does not document `{c}`"
