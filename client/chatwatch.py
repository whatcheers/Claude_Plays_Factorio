"""Stream in-game chat to stdout, one line per message, for Claude's Monitor.

Remembers the last message it printed in .chat_seq, so a restart doesn't replay.
Survives the game going away (re-host, reload) by reconnecting.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import ROOT, Bridge, BridgeError  # noqa: E402

SEQ = os.path.join(ROOT, ".chat_seq")


def load_seq():
    try:
        with open(SEQ, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_seq(n):
    with open(SEQ, "w", encoding="utf-8") as f:
        f.write(str(n))


def main():
    after = load_seq()
    b = None
    down = False
    while True:
        try:
            if b is None:
                b = Bridge()
            r = b.call("chat_read", {"after": after})
            if down:  # only "back" once a read actually worked
                print("[chatwatch] chat connected", flush=True)
                down = False
            if r["seq"] < after:  # new map: counter restarted
                after = 0
                r = b.call("chat_read", {"after": 0})
            for m in r["msgs"]:
                print(f"[chat] {m['from']}: {m['text']}", flush=True)
                after = m["id"]
            save_seq(after)
        except (BridgeError, OSError, ValueError) as e:
            if b is not None:
                try:
                    b.close()
                except OSError:
                    pass
                b = None
            if not down:
                print(f"[chatwatch] game unreachable: {e}", flush=True)
                down = True
        time.sleep(2)


if __name__ == "__main__":
    main()
