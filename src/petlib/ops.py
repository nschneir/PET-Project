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
            mon.release()


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
                mon.release()
        if val == value:
            return {"fired": "mem", "elapsed": round(time.monotonic() - start, 3)}
        time.sleep(0.4)
    return {"fired": None, "timeout": timeout, "last_value": val}


def wait_for_break(session, timeout: float = 30.0) -> dict:
    """Checkpoint-hit wait, robust under warp.

    The hit flag on a stopped checkpoint is the durable source of truth:
    a stop=True checkpoint freezes the machine until a client resumes it,
    and the flag is visible in CHECKPOINT_LIST even when the STOPPED event
    was lost (Plan 03 verified; the connect-stop/resume race destroys queued
    events, which is what made event-only waiting flaky under --warp).
    The STOPPED event is kept as a fast-path only; every loop iteration
    re-polls the flags, so a missed event costs at most one poll slice.
    Timeout leaves the machine RUNNING (the documented contract)."""
    start = time.monotonic()
    deadline = start + timeout

    def _fired(mon, number, pc=None):
        regs = mon.registers()
        return {"fired": "break", "checkpoint": number,
                "pc": pc if pc is not None else regs.get("PC"),
                "registers": regs,
                "elapsed": round(time.monotonic() - start, 3)}

    with session.monitor() as mon:
        while True:
            hit = next((ck for ck in mon.checkpoint_list() if ck.hit), None)
            if hit is not None:
                return _fired(mon, hit.number)          # machine stays stopped
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                mon.resume()                             # timeout: leave it running
                return {"fired": None, "timeout": timeout}
            mon.resume()                                 # the list stopped the machine
            info = mon.wait_for_stop(min(1.0, remaining))
            if info is not None and info.checkpoint is not None:
                return _fired(mon, info.checkpoint, info.pc)
            # Slice elapsed, or a STOPPED with no checkpoint id (e.g. another
            # client's connect-stop): loop — the flag poll decides.


def run_until(session, addr: int, timeout: float = 30.0, count: int = 1) -> dict:
    """Run until addr is executed `count` times; the machine stays stopped at
    the final arrival ("frame stepping" when addr is a main-loop label).

    Uses a persistent checkpoint plus the same durable-flag polling as
    wait_for_break (hit / hit_count survive a lost STOPPED event). Returns
    {"registers": regs-or-None, "reached": k, "count": count}; registers is
    None on timeout, in which case the checkpoint is removed and the machine
    is left running."""
    start = time.monotonic()
    deadline = start + timeout
    with session.monitor() as mon:
        ck = mon.checkpoint_set(addr, op=CP_EXEC, temporary=False)
        for i in range(count):
            mon.resume()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    mon.checkpoint_delete(ck.number)
                    mon.resume()
                    return {"registers": None, "reached": i, "count": count}
                info = mon.wait_for_stop(min(1.0, remaining))
                if info is not None and info.checkpoint == ck.number:
                    break
                cur = next((c for c in mon.checkpoint_list()
                            if c.number == ck.number), None)
                if cur is not None and (cur.hit or cur.hit_count > i):
                    break                        # durable flag caught it
                mon.resume()                     # the list stopped the machine
        regs = mon.registers()
        mon.checkpoint_delete(ck.number)
        return {"registers": regs, "reached": count, "count": count}


def find_bytes(mon, start: int, length: int, pattern: bytes,
               limit: int = 256) -> tuple[list[int], bool]:
    """Addresses of every occurrence of `pattern` in [start, start+length),
    clamped to the 64 KB space. Returns (matches, truncated); truncated is
    True when `limit` clipped the list. One bulk read; does not resume."""
    n = max(0, min(length, 0x10000 - start))
    data = mon.memory_read(start, n)
    matches: list[int] = []
    truncated = False
    i = data.find(pattern)
    while i != -1:
        if len(matches) >= limit:
            truncated = True
            break
        matches.append(start + i)
        i = data.find(pattern, i + 1)
    return matches, truncated


def clear_checkpoints(mon, include_mask: int, exclude_mask: int = 0) -> list[int]:
    """Delete every checkpoint whose op matches include_mask (and none of
    exclude_mask); returns the removed checkpoint ids."""
    removed = []
    for ck in mon.checkpoint_list():
        if (ck.op & include_mask) and not (ck.op & exclude_mask):
            mon.checkpoint_delete(ck.number)
            removed.append(ck.number)
    return removed


def machine_state(session) -> str:
    """'running' / 'stopped' via the session daemon; 'unknown' without one
    (a direct monitor connection stops the CPU, so the question is only
    answerable via the daemon). Never raises."""
    if not getattr(session, "socket", None):
        return "unknown"
    try:
        with session.monitor() as mon:
            status = getattr(mon, "status", None)
            return status() if status else "unknown"
    except (ConnectionError, TimeoutError, OSError):
        return "unknown"
