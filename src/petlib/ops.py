"""Shared high-level operations used by both the CLI and the MCP server.

One implementation of the wait/until primitives and symbol plumbing so the
two front ends cannot drift.
"""

from __future__ import annotations

import time

from .protocol import CP_EXEC
from .screen import read_screen_text
from .symbols import load_labels, nearest, resolve


def parse_number(s) -> int:
    s = str(s).strip()
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def parse_ref(labels: dict[str, int], ref) -> int:
    r = str(ref)
    if r.startswith(("$", "0x", "0X")) or r.isdigit():
        return parse_number(r)
    return resolve(labels, r)  # KeyError with candidates on unknown symbol


def session_labels(s) -> dict[str, int]:
    if isinstance(s.labels, str) and s.labels:
        try:
            return load_labels(s.labels)
        except OSError:
            return {}
    return {}


def pc_symbol(labels: dict[str, int], regs: dict[str, int]) -> str | None:
    pc = regs.get("PC")
    if pc is None or not labels:
        return None
    hit = nearest(labels, pc)
    if hit is None:
        return None
    name, off = hit
    return f"{name}+{off}" if off else name


def _screen(session) -> str:
    with session.monitor() as mon:
        try:
            return read_screen_text(mon, session.profile)
        finally:
            mon.resume()


def wait_for_text(session, text: str, timeout: float = 30.0) -> dict:
    start = time.monotonic()
    deadline = start + timeout
    last = ""
    while time.monotonic() < deadline:
        last = _screen(session)
        if text in last:
            return {"fired": "text", "elapsed": round(time.monotonic() - start, 3)}
        time.sleep(0.4)
    return {"fired": None, "timeout": timeout, "screen": last}


def wait_for_mem(session, addr: int, value: int, timeout: float = 30.0) -> dict:
    start = time.monotonic()
    deadline = start + timeout
    val = None
    while time.monotonic() < deadline:
        with session.monitor() as mon:
            try:
                val = mon.memory_read(addr, 1)[0]
            finally:
                mon.resume()
        if val == value:
            return {"fired": "mem", "elapsed": round(time.monotonic() - start, 3)}
        time.sleep(0.4)
    return {"fired": None, "timeout": timeout, "last_value": val}


def wait_for_break(session, timeout: float = 30.0) -> dict:
    """Checkpoint-hit wait. Checks already-hit checkpoints first: if a hit
    happened while no client was connected, the events are lost but the
    machine sits stopped with the hit flag set (Plan 03 verified)."""
    start = time.monotonic()
    with session.monitor() as mon:
        hit = next((ck for ck in mon.checkpoint_list() if ck.hit), None)
        if hit is not None:
            regs = mon.registers()
            return {"fired": "break", "checkpoint": hit.number,
                    "pc": regs.get("PC"), "registers": regs,
                    "elapsed": round(time.monotonic() - start, 3)}
        mon.resume()
        info = mon.wait_for_stop(timeout)
        if info is None:
            return {"fired": None, "timeout": timeout}
        regs = mon.registers()
        return {"fired": "break", "checkpoint": info.checkpoint,
                "pc": info.pc, "registers": regs,
                "elapsed": round(time.monotonic() - start, 3)}


def run_until(session, addr: int, timeout: float = 30.0) -> dict | None:
    """Temporary exec checkpoint + run; registers at stop (machine stays
    stopped), or None on timeout."""
    with session.monitor() as mon:
        mon.checkpoint_set(addr, op=CP_EXEC, temporary=True)
        mon.resume()
        info = mon.wait_for_stop(timeout)
        if info is None:
            return None
        return mon.registers()
