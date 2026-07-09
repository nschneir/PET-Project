"""MCP server exposing pet-tools to MCP-native AI clients (spec §3.3).

Thin wrappers over the same petlib operations the CLI uses; CLI and MCP are
interchangeable against the same session registry. Tools return the same
structured data as the CLI's --json. Raised petlib exceptions surface as MCP
tool errors with their actionable messages intact.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .ops import parse_number, parse_ref, pc_symbol, session_labels
from .screen import read_screen_text, save_screenshot_png
from .session import Session

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


def main() -> None:
    srv.run()


if __name__ == "__main__":
    main()
