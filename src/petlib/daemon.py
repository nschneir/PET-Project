"""Per-session monitor daemon: owns the one VICE binary-monitor connection.

VICE resumes the CPU whenever a monitor connection closes and accepts only
one monitor connection at a time (2026-07-10 transport findings). This
process holds that single connection for the session's lifetime, so the
machine's run/stop state survives across pet/MCP commands — each command
is a short-lived IPC client on the session's unix socket.

Run as:  python -m petlib.daemon --name NAME --vice-port PORT --socket PATH
Spawned by Session.launch; the client side is petlib.daemon_client."""

from __future__ import annotations

import argparse
import json
import os
import select
import socket
import time
import traceback

from . import rpc
from .monitor import MonitorClient
from .protocol import ResponseType

RUNNING = "running"
STOPPED = "stopped"

#: every MonitorClient method a client may call, plus the release verb.
ALLOWED = frozenset({
    "ping", "memory_read", "memory_write", "resume", "release", "registers",
    "set_register", "reset", "keyboard_feed", "display", "palette",
    "vice_info", "quit", "resource_get", "autostart", "checkpoint_set",
    "checkpoint_delete", "checkpoint_toggle", "checkpoint_list",
    "condition_set", "step", "finish", "wait_for_stop",
})

#: methods that leave the machine halted by their own meaning.
STOPPING = frozenset({"step", "finish"})


class PetDaemon:
    """One VICE connection + the session's desired run/stop state."""

    def __init__(self, mon: MonitorClient, listen: socket.socket | None,
                 session: str):
        self.mon = mon
        self.listen = listen
        self.session = session
        self.state = RUNNING
        self._quitting = False

    # --- main loops -------------------------------------------------------

    def serve_forever(self) -> None:
        while True:
            if not self._idle_wait():
                return                          # xpet died while idle
            client, _ = self.listen.accept()
            self._handle(client)
            if self._quitting:
                return

    def _idle_wait(self) -> bool:
        """Block until a client connects; meanwhile pump unsolicited VICE
        events. A stop=True checkpoint can fire with nobody waiting — the
        machine parks and the daemon must remember STOPPED, or the next
        inspection command's release() would destroy the parked state.
        Returns False when the VICE connection is gone."""
        while True:
            r, _, _ = select.select([self.listen, self.mon._sock], [], [])
            if self.mon._sock in r and not self._pump_vice_events():
                return False
            if self.listen in r:
                return True

    def _pump_vice_events(self) -> bool:
        try:
            events = self.mon.poll_events(0.05)
        except (ConnectionError, OSError):
            return False
        for ev in events:
            if ev.response_type == ResponseType.STOPPED:
                self.state = STOPPED
            self.mon.events.append(ev)          # keep for a later wait_for_stop
        return True

    # --- one client -------------------------------------------------------

    def _handle(self, client: socket.socket) -> None:
        try:
            self._serve_client(client)
        finally:
            client.close()
            if not self._quitting:
                self._restore()

    def _serve_client(self, client: socket.socket) -> None:
        f = client.makefile("rwb")
        rpc.send_line(f, {"hello": "pet-daemon",
                          "version": rpc.PROTOCOL_VERSION,
                          "session": self.session})
        while True:
            line = f.readline()
            if not line:
                return                          # client disconnected
            req = json.loads(line)
            resp = {"id": req.get("id")}
            try:
                result = self._dispatch(client, req["method"],
                                        rpc.decode_value(req.get("args", [])),
                                        rpc.decode_value(req.get("kwargs", {})))
                resp["ok"] = rpc.encode_value(result)
            except Exception as e:              # marshalled to the client
                resp["err"] = type(e).__name__
                resp["msg"] = str(e)
                rpc.send_line(f, resp)
                if isinstance(e, ConnectionError):
                    self._quitting = True       # xpet died; nothing to restore
                    return
                continue
            rpc.send_line(f, resp)
            if req["method"] == "quit":
                self._quitting = True
                return

    def _dispatch(self, client: socket.socket, method: str,
                  args: list, kwargs: dict):
        if method not in ALLOWED:
            raise ValueError(f"unknown daemon method {method!r}")
        if method == "release":
            self._restore()
            return None
        if method == "resume":
            self.mon.resume()
            self.state = RUNNING
            return None
        if method == "wait_for_stop":
            timeout = float(args[0]) if args else float(kwargs["timeout"])
            return self._wait_for_stop(client, timeout)
        result = getattr(self.mon, method)(*args, **kwargs)
        if method in STOPPING:
            self.state = STOPPED
        return result

    def _wait_for_stop(self, client: socket.socket, timeout: float):
        """wait_for_stop in <=0.5 s slices, aborting if the client vanishes
        (a Ctrl-C'd `pet wait --break` must not wedge the daemon)."""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            info = self.mon.wait_for_stop(min(0.5, remaining))
            if info is not None:
                self.state = STOPPED
                return info
            r, _, _ = select.select([client], [], [], 0)
            if r and client.recv(1, socket.MSG_PEEK) == b"":
                return None                     # client gone; caller restores

    def _restore(self) -> None:
        """release()/disconnect: put the machine back in its desired state.
        Monitor commands stop the CPU as a side effect; only an explicit
        resume sets RUNNING, so restoring means EXIT iff desired RUNNING."""
        if self.state == RUNNING:
            try:
                self.mon.resume()
            except (ConnectionError, TimeoutError, OSError):
                pass                            # VICE gone; loops will notice


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="petlib.daemon")
    ap.add_argument("--name", required=True)
    ap.add_argument("--vice-port", type=int, required=True)
    ap.add_argument("--socket", required=True)
    a = ap.parse_args(argv)

    mon = MonitorClient(port=a.vice_port)
    mon.connect(deadline=10.0)
    mon.ping()
    mon.resume()                                # connect-stop answered; RUNNING

    try:
        os.unlink(a.socket)
    except FileNotFoundError:
        pass
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listen.bind(a.socket)
    listen.listen(1)
    print(f"pet daemon up: session={a.name} vice_port={a.vice_port}", flush=True)
    try:
        PetDaemon(mon, listen, a.name).serve_forever()
    except Exception:
        traceback.print_exc()
        raise
    finally:
        try:
            os.unlink(a.socket)
        except FileNotFoundError:
            pass
        mon.close()


if __name__ == "__main__":
    main()
