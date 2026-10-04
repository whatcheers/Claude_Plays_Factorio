"""Keep research going: every 30 s, if nothing is being researched, queue the
preferred tech using only the science packs we make (green once any green has been
made). Run it in the background."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bridge import Bridge  # noqa: E402

# peaceful map: never spend flasks on combat techs
SKIP = ("military", "gun-turret", "stone-wall", "weapon", "physical-projectile", "heavy-armor", "turret")
# preferred order; anything else red-only follows, cheapest first
PREFER = ["logistics", "electric-mining-drill", "logistic-science-pack", "steel-processing", "fast-inserter", "radar",
          "automation-2", "research-speed-1", "research-speed-2", "logistics-2",
          # the road to blue science
          "engine", "fluid-handling", "oil-gathering", "plastics", "advanced-circuit", "sulfur-processing",
          "chemical-science-pack",
          "advanced-material-processing", "electric-energy-distribution-1",
          "toolbelt", "landfill", "circuit-network", "solar-energy"]
RED, GREEN = "automation-science-pack", "logistic-science-pack"
MADE_GREEN = ("local s = game.forces.player.get_item_production_statistics(game.surfaces[1])"
              " rcon.print(s.get_input_count('logistic-science-pack'))")


def pick(avail, packs=(RED,)):
    """Preferred (else cheapest) tech whose science packs are all ones we make."""
    red = [t for t in avail if not t.get("trigger") and t.get("ingredients") and set(t["ingredients"]) <= set(packs)
           and not any(k in t["name"] for k in SKIP)]
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
                    try:
                        green = int(b.lua(MADE_GREEN).strip() or 0) > 0
                    except Exception:
                        green = False
                    n = pick(r.get("available", []), (RED, GREEN) if green else (RED,))
                    if n:
                        b.call("research", {"name": n})
                        b.call("say", {"text": f"[Lab Director] research done, the labs are starting on {n.replace('-', ' ')}"}, check=False)
                        print(f"{time.strftime('%H:%M:%S')} queued {n}", flush=True)
        except Exception as e:  # game reloading etc.: try again next round
            print(f"{time.strftime('%H:%M:%S')} {e}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
