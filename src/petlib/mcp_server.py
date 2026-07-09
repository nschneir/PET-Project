"""MCP server exposing pet-tools to MCP-native AI clients (spec §3.3).

Thin wrappers over the same petlib operations the CLI uses; CLI and MCP are
interchangeable against the same session registry. Tools return the same
structured data as the CLI's --json. Raised petlib exceptions surface as MCP
tool errors with their actionable messages intact.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .ops import (
    parse_number,
    parse_ref,
    pc_symbol,
    run_until,
    session_labels,
    wait_for_break,
    wait_for_mem,
    wait_for_text,
)
from .protocol import CP_EXEC, CP_LOAD, CP_STORE
from .screen import read_screen_text, save_screenshot_png
from .session import Session
from .symbols import format_addr

srv = FastMCP("pet-tools")


def _attach(session: str | None = None) -> Session:
    return Session.attach(session)


@srv.tool()
def pet_session_list() -> dict:
    """List running emulated PET sessions (name, model, pid, monitor port)."""
    return {"sessions": [
        {"name": s.name, "model": s.model, "pid": s.pid, "port": s.port}
        for s in Session.list_all()
    ]}


@srv.tool()
def pet_session_start(model: str = "pet4032", name: str | None = None,
                      disk: str | None = None) -> dict:
    """Boot a fresh emulated PET (headless, warp). Models: pet2001, pet3032,
    pet4032, pet8032, pet8296. Optionally attach a d64/d80/d82 disk image."""
    s = Session.launch(model=model, name=name, headless=True, warp=True,
                       disk8=disk)
    return {"name": s.name, "model": s.model, "pid": s.pid, "port": s.port}


@srv.tool()
def pet_session_stop(name: str | None = None) -> dict:
    """Stop a running PET session (the only one if name is omitted)."""
    s = Session.attach(name)
    s.stop()
    return {"stopped": s.name}


@srv.tool()
def pet_session_reset(hard: bool = False, session: str | None = None) -> dict:
    """Reset the PET (soft, or hard power-cycle). Leaves the machine running."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            mon.reset(hard=hard)
        finally:
            mon.resume()
    return {"reset": s.name, "hard": hard}


@srv.tool()
def pet_screen_text(session: str | None = None) -> dict:
    """Read the PET screen as plain text. This is the PREFERRED way to see
    program output — faster and more reliable than screenshots for AI use."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            text = read_screen_text(mon, s.profile)
        finally:
            mon.resume()
    return {"text": text, "rows": text.splitlines()}


@srv.tool()
def pet_screenshot(path: str, session: str | None = None) -> dict:
    """Save a PNG screenshot. Prefer pet_screen_text for reading output;
    use this only when pixel-level appearance matters."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            w, h = save_screenshot_png(mon, path)
        finally:
            mon.resume()
    return {"png": path, "width": w, "height": h}


@srv.tool()
def pet_mem_read(addr: str, length: int = 256, session: str | None = None) -> dict:
    """Read emulated memory. addr accepts $hex, 0xhex, decimal, or a symbol
    from the loaded label file. Returns hex-encoded bytes."""
    s = _attach(session)
    a = parse_ref(session_labels(s), addr)
    with s.monitor() as mon:
        try:
            data = mon.memory_read(a, length)
        finally:
            mon.resume()
    return {"addr": a, "length": len(data), "hex": data.hex()}


@srv.tool()
def pet_mem_write(addr: str, values: list[int], session: str | None = None) -> dict:
    """Write bytes to emulated memory. addr accepts $hex/0xhex/decimal/symbol."""
    s = _attach(session)
    a = parse_ref(session_labels(s), addr)
    with s.monitor() as mon:
        try:
            mon.memory_write(a, bytes(values))
        finally:
            mon.resume()
    return {"addr": a, "written": len(values)}


@srv.tool()
def pet_reg_get(session: str | None = None) -> dict:
    """Read CPU registers. PC is annotated with the nearest symbol when a
    label file is loaded."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            regs = mon.registers()
        finally:
            mon.resume()
    return {"registers": regs, "pc_symbol": pc_symbol(session_labels(s), regs)}


@srv.tool()
def pet_reg_set(name: str, value: str, session: str | None = None) -> dict:
    """Set a CPU register (e.g. PC, A, X, Y). value accepts $hex/0xhex/decimal."""
    s = _attach(session)
    v = parse_number(value)
    with s.monitor() as mon:
        try:
            mon.set_register(name, v)
        finally:
            mon.resume()
    return {"register": name.upper(), "value": v}


@srv.tool()
def pet_break_add(ref: str, condition: str | None = None,
                  temporary: bool = False, session: str | None = None) -> dict:
    """Set a breakpoint at an address or symbol. Machine keeps running;
    use pet_wait_break to block until it fires."""
    s = _attach(session)
    labels = session_labels(s)
    addr = parse_ref(labels, ref)
    with s.monitor() as mon:
        try:
            ck = mon.checkpoint_set(addr, op=CP_EXEC, temporary=temporary)
            if condition:
                mon.condition_set(ck.number, condition)
        finally:
            mon.resume()
    return {"id": ck.number, "address": format_addr(labels, addr),
            "condition": condition, "temporary": temporary}


@srv.tool()
def pet_break_list(session: str | None = None) -> dict:
    """List breakpoints/watchpoints with hit counts."""
    s = _attach(session)
    labels = session_labels(s)
    with s.monitor() as mon:
        try:
            cks = mon.checkpoint_list()
        finally:
            mon.resume()
    return {"breakpoints": [
        {"id": ck.number, "address": format_addr(labels, ck.start), "end": ck.end,
         "op": ck.op, "enabled": ck.enabled, "hits": ck.hit_count,
         "has_condition": ck.has_condition}
        for ck in cks
    ]}


@srv.tool()
def pet_break_remove(checkpoint_id: int, session: str | None = None) -> dict:
    """Remove a breakpoint/watchpoint by id."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            mon.checkpoint_delete(checkpoint_id)
        finally:
            mon.resume()
    return {"removed": checkpoint_id}


@srv.tool()
def pet_watch_add(ref: str, on_load: bool = False, on_store: bool = False,
                  length: int = 1, session: str | None = None) -> dict:
    """Set a watchpoint on a memory range (default: both load and store)."""
    s = _attach(session)
    labels = session_labels(s)
    addr = parse_ref(labels, ref)
    op = (CP_LOAD if on_load else 0) | (CP_STORE if on_store else 0)
    if not op:
        op = CP_LOAD | CP_STORE
    with s.monitor() as mon:
        try:
            ck = mon.checkpoint_set(addr, addr + length - 1, op=op)
        finally:
            mon.resume()
    return {"id": ck.number, "address": format_addr(labels, addr), "length": length}


def _stopped_regs(s, regs: dict) -> dict:
    return {"registers": regs, "pc_symbol": pc_symbol(session_labels(s), regs),
            "stopped": True}


@srv.tool()
def pet_step(count: int = 1, over: bool = False, session: str | None = None) -> dict:
    """Execute N instructions. The machine STAYS STOPPED afterwards; use
    pet_continue to resume."""
    s = _attach(session)
    with s.monitor() as mon:
        regs = mon.step(count, over=over)
    return _stopped_regs(s, regs)


@srv.tool()
def pet_finish(session: str | None = None) -> dict:
    """Run until the current subroutine returns. Machine stays stopped."""
    s = _attach(session)
    with s.monitor() as mon:
        regs = mon.finish()
    return _stopped_regs(s, regs)


@srv.tool()
def pet_continue(session: str | None = None) -> dict:
    """Resume execution after a breakpoint/step."""
    s = _attach(session)
    with s.monitor() as mon:
        mon.resume()
    return {"running": True}


@srv.tool()
def pet_until(ref: str, timeout: float = 30.0, session: str | None = None) -> dict:
    """Run until an address/symbol is executed; machine stays stopped there."""
    s = _attach(session)
    labels = session_labels(s)
    addr = parse_ref(labels, ref)
    regs = run_until(s, addr, timeout)
    if regs is None:
        raise RuntimeError(
            f"timeout: {format_addr(labels, addr)} not reached in {timeout}s")
    return _stopped_regs(s, regs)


@srv.tool()
def pet_wait_text(text: str, timeout: float = 30.0,
                  session: str | None = None) -> dict:
    """Block until TEXT appears on the screen. A timeout returns
    {"fired": null, "screen": ...} (not an error) so you can inspect what
    the program actually displayed."""
    return wait_for_text(_attach(session), text, timeout)


@srv.tool()
def pet_wait_mem(addr: str, equals: str, timeout: float = 30.0,
                 session: str | None = None) -> dict:
    """Block until the byte at addr equals the value ($hex/decimal accepted)."""
    s = _attach(session)
    return wait_for_mem(s, parse_ref(session_labels(s), addr),
                        parse_number(equals), timeout)


@srv.tool()
def pet_wait_break(timeout: float = 30.0, session: str | None = None) -> dict:
    """Block until a breakpoint/watchpoint fires; reports checkpoint id, PC,
    and registers. Machine is left stopped when it fires."""
    s = _attach(session)
    out = wait_for_break(s, timeout)
    if out.get("fired"):
        out["pc_symbol"] = pc_symbol(session_labels(s), out.pop("registers"))
    return out


def main() -> None:
    srv.run()


if __name__ == "__main__":
    main()
