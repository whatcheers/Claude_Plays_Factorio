"""Keep research going: every 30 s, if nothing is being researched, queue the
cheapest available tech that needs only red science. Run it in the background."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402

# preferred order; anything else red-only follows, cheapest first
PREFER = ["logistics", "electric-mining-drill", "steel-processing", "logistic-science-pack", "fast-inserter", "radar"]


def pick(avail):
    red = [t for t in avail if not t.get("trigger") and (t.get("ingredients") or []) == ["automation-science-pack"]]
    names = {t["name"]: t for t in red}
    for n in PREFER:
        if n in names:
            return n
    return min(red, key=lambda t: t.get("units") or 0)["name"] if red else None


def main():
    while True:
        try:
            with Bridge() as b:
                r = b.call("tech")
                if not r.get("current"):
                    n = pick(r.get("available", []))
                    if n:
                        b.call("research", {"name": n})
                        b.call("say", {"text": f"Research done; now researching {n}."}, check=False)
                        print(f"{time.strftime('%H:%M:%S')} queued {n}", flush=True)
        except Exception as e:  # game reloading etc.: try again next round
            print(f"{time.strftime('%H:%M:%S')} {e}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
