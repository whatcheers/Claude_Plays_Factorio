"""Call the claude-bridge mod's remote interface over RCON."""
import json
import os
import time

from rcon import Rcon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BridgeError(Exception):
    pass


def _password():
    pw = os.environ.get("FACTORIO_RCON_PASSWORD")
    if pw:
        return pw
    path = os.path.join(ROOT, ".rcon_password")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    raise BridgeError("set FACTORIO_RCON_PASSWORD or write it to .rcon_password")


class Bridge:
    def __init__(self):
        self.r = Rcon(password=_password())
        try:
            self.r.connect()
        except OSError as e:
            raise BridgeError(f"can't reach RCON at {self.r.host}:{self.r.port} ({e}); host a multiplayer game first") from None
        # the first Lua command in a game can be eaten by the achievements prompt
        self.r.lua("rcon.print('')")

    def close(self):
        self.r.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def lua(self, code):
        return self.r.lua(code)

    def call(self, fn, args=None, check=True):
        payload = json.dumps(args or {})
        if "]==]" in payload:
            raise BridgeError("payload contains a Lua long-string terminator")
        text = self.r.lua(f'rcon.print(remote.call("claude", "{fn}", [==[{payload}]==]))').strip()
        if not text:
            raise BridgeError(f"{fn}: empty reply (is the claude-bridge mod enabled?)")
        if text.startswith("Cannot execute command"):
            raise BridgeError(text)
        res = json.loads(text)
        if check and isinstance(res, dict) and res.get("error"):
            raise BridgeError(f"{fn}: {res['error']}")
        return res

    # ---- ticks
    def paused(self):
        return self.lua("rcon.print(tostring(game.tick_paused))").strip() == "true"

    def set_paused(self, value):
        self.lua(f"game.tick_paused = {'true' if value else 'false'}")

    def tick(self):
        return int(self.lua("rcon.print(game.tick)").strip())

    def run_job(self, fn, args, wall_timeout=600):
        """Start a timed job in the mod, let the game run until it finishes,
        then restore the previous paused state."""
        was = self.paused()
        try:
            self.call(fn, args)
            self.set_paused(False)
            deadline = time.time() + wall_timeout
            while time.time() < deadline:
                j = self.call("job", check=False)
                if j.get("state") in ("done", "failed"):
                    return j
                time.sleep(0.1)
            self.call("cancel_job", check=False)
            return {"state": "failed", "msg": "wall-clock timeout"}
        finally:
            self.set_paused(was)

    def run_ticks(self, n):
        was = self.paused()
        try:
            start = self.tick()
            self.set_paused(False)
            while self.tick() < start + n:
                time.sleep(0.05)
        finally:
            self.set_paused(was)
