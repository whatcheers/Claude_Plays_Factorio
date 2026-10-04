"""Minimal Source-RCON client for Factorio."""
import os
import socket
import struct

AUTH, AUTH_RESPONSE, EXEC = 3, 2, 2


class RconError(Exception):
    pass


class Rcon:
    def __init__(self, host=None, port=None, password=None, timeout=10.0):
        self.host = host or os.environ.get("FACTORIO_RCON_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("FACTORIO_RCON_PORT", 27015))
        self.password = password or os.environ.get("FACTORIO_RCON_PASSWORD", "")
        self.timeout = timeout
        self.sock = None
        self._id = 0

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        rid, _, _ = self._roundtrip(AUTH, self.password)
        if rid == -1:
            raise RconError("RCON auth failed (wrong password)")

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _send(self, ptype, body):
        self._id += 1
        data = struct.pack("<ii", self._id, ptype) + body.encode("utf-8") + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(data)) + data)
        return self._id

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise RconError("connection closed")
            buf += chunk
        return buf

    def _recv(self):
        (size,) = struct.unpack("<i", self._recv_exact(4))
        data = self._recv_exact(size)
        rid, ptype = struct.unpack("<ii", data[:8])
        return rid, ptype, data[8:-2].decode("utf-8", "replace")

    def _roundtrip(self, ptype, body):
        self._send(ptype, body)
        while True:
            rid, rtype, text = self._recv()
            if ptype == AUTH and rtype != AUTH_RESPONSE:
                continue  # empty RESPONSE_VALUE precedes the auth response
            return rid, rtype, text

    def command(self, cmd):
        """Run a console command; returns its printed output.

        Factorio answers each request in a single packet, so no
        multi-packet sentinel dance is needed.
        """
        _, _, text = self._roundtrip(EXEC, cmd)
        return text

    def lua(self, code):
        """Run Lua via /silent-command; use rcon.print(...) to return data."""
        return self.command("/silent-command " + code)
