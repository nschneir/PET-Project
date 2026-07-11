"""MCP server exposing pet-tools to MCP-native AI clients (spec §3.3).

Thin wrappers over the same petlib operations the CLI uses; CLI and MCP are
interchangeable against the same session registry. Tools return the same
structured data as the CLI's --json. Raised petlib exceptions surface as MCP
tool errors with their actionable messages intact.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .basic import tokenize
from .build import build_asm
from .disasm import disassemble
from .disk import create_image, get_file, list_files, put_file
from .machines import get_profile
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
from .packaging import package_program
from .protocol import CP_EXEC, CP_LOAD, CP_STORE
from .romdoc import identify, rom_labels
from .screen import read_screen_text, save_screenshot_png
from .session import Session
from .symbols import format_addr
from .testing import load_test, program_test, run_test
from .text import ascii_to_petscii

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
    """Boot a fresh emulated PET (headless, warp). Models: pet2001-4k,
    pet2001, pet3032, pet4032, pet8032, pet8296. Optionally attach a
    d64/d80/d82 disk image."""
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
            mon.release()
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
def pet_until(ref: str, timeout: float = 30.0, count: int = 1,
              session: str | None = None) -> dict:
    """Run until an address/symbol is executed count times; machine stays
    stopped there. count>1 = deterministic frame stepping on a loop label."""
    s = _attach(session)
    labels = session_labels(s)
    addr = parse_ref(labels, ref)
    out = run_until(s, addr, timeout, count=count)
    if out["registers"] is None:
        raise RuntimeError(
            f"timeout: {format_addr(labels, addr)} reached "
            f"{out['reached']}/{count} time(s) in {timeout}s")
    return {**_stopped_regs(s, out["registers"]), "count": count}


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


@srv.tool()
def pet_build(source: str, model: str = "pet4032") -> dict:
    """Assemble 6502 source (ca65 syntax) to a .prg + VICE label file."""
    profile = get_profile(model)
    res = build_asm(Path(source), basic_start=profile.basic_start)
    return {"prg": str(res.prg), "labels": str(res.labels)}


@srv.tool()
def pet_package(source: str, output: str | None = None, title: str | None = None,
                model: str = "pet4032") -> dict:
    """Package a .s/.bas/.prg into an artifact any VICE user can run: a .prg,
    or (when output ends in .d64/.d80/.d82) a disk image whose first file is
    the program so `xpet out.d64` autostarts it. Returns the exact run
    command in "run"."""
    return package_program(Path(source), out=output, title=title, model=model)


@srv.tool()
def pet_run(source: str, session: str | None = None) -> dict:
    """Build/tokenize a .bas/.s/.prg as needed, then load and RUN it on the
    running PET. Registers assembly symbols on the session automatically."""
    s = _attach(session)
    src = Path(source).resolve()
    ext = src.suffix.lower()
    labels_path = None
    if ext == ".prg":
        prg = src
    elif ext == ".bas":
        prg = tokenize(src, src.with_suffix(".prg"), s.profile.basic_version)
    elif ext == ".s":
        res = build_asm(src, basic_start=s.profile.basic_start)
        prg, labels_path = res.prg, res.labels
    else:
        raise ValueError(f"cannot run {ext!r} files (use .bas, .s, or .prg)")
    with s.monitor() as mon:
        try:
            mon.autostart(Path(prg).resolve(), run=True)
        finally:
            mon.resume()
    if labels_path:
        s.set_labels_path(str(labels_path))
    return {"source": str(src), "prg": str(prg),
            "symbols": str(labels_path) if labels_path else None}


@srv.tool()
def pet_load(prg: str, run: bool = True, symbols: str | None = None,
             session: str | None = None) -> dict:
    """Load a .prg via autostart (optionally without RUN); optionally
    register a VICE label file for symbolic debugging."""
    s = _attach(session)
    p = Path(prg).resolve()
    with s.monitor() as mon:
        try:
            mon.autostart(p, run=run)
        finally:
            mon.resume()
    if symbols:
        s.set_labels_path(str(Path(symbols).resolve()))
    return {"loaded": str(p), "run": run, "symbols": symbols}


@srv.tool()
def pet_basic_type(text: str, run: bool = False,
                   session: str | None = None) -> dict:
    """Type BASIC program text into the running PET via the keyboard
    (keywords may be upper or lower case; each line ends with \\n).
    Set run=true to type RUN afterwards."""
    s = _attach(session)
    if not text.endswith("\n"):
        text += "\n"
    if run:
        text += "run\n"
    petscii = ascii_to_petscii(text)
    with s.monitor() as mon:
        try:
            mon.keyboard_feed(petscii)
        finally:
            mon.release()
    return {"typed_chars": len(petscii), "run": run}


@srv.tool()
def pet_disk_create(image: str, label: str = "disk", disk_id: str = "00") -> dict:
    """Create a blank d64/d80/d82 disk image."""
    return {"image": str(create_image(Path(image), label=label, disk_id=disk_id))}


@srv.tool()
def pet_disk_ls(image: str) -> dict:
    """List the directory of a disk image."""
    return list_files(Path(image))


@srv.tool()
def pet_disk_put(image: str, file: str, name: str | None = None) -> dict:
    """Copy a host file onto a disk image."""
    return {"image": image, "name": put_file(Path(image), Path(file), name)}


@srv.tool()
def pet_disk_get(image: str, name: str, dest: str) -> dict:
    """Copy a file off a disk image to the host."""
    return {"dest": str(get_file(Path(image), name, Path(dest)))}


@srv.tool()
def pet_disk_boot(image: str, session: str | None = None) -> dict:
    """Attach a disk image to the running PET and LOAD+RUN its first file."""
    s = _attach(session)
    p = Path(image).resolve()
    with s.monitor() as mon:
        try:
            mon.autostart(p, run=True)
        finally:
            mon.resume()
    return {"booted": str(p)}


@srv.tool()
def pet_rom_info(session: str | None = None) -> dict:
    """Identify the loaded ROM set (names + content hashes)."""
    s = _attach(session)
    with s.monitor() as mon:
        try:
            return identify(mon)
        finally:
            mon.release()


@srv.tool()
def pet_rom_disasm(start: str, length: int = 32,
                   session: str | None = None) -> dict:
    """Disassemble live memory with ROM + session symbol annotations.
    start accepts $hex/0xhex/decimal or a symbol (e.g. CHROUT)."""
    s = _attach(session)
    labels = {**rom_labels(s.profile.basic_version), **session_labels(s)}
    addr = parse_ref(labels, start)
    with s.monitor() as mon:
        try:
            data = mon.memory_read(addr, length)
        finally:
            mon.release()
    return {"start": addr, "length": length,
            "lines": disassemble(data, addr, labels)}


@srv.tool()
def pet_test_run(yaml_file: str) -> dict:
    """Run a declarative YAML test (boots its own fresh PET; see spec §8)."""
    return run_test(load_test(Path(yaml_file))).to_dict()


@srv.tool()
def pet_test_programs(directory: str = "tests/programs") -> dict:
    """Run every example-program directory (program + expect.txt) as a test."""
    results = [run_test(program_test(d))
               for d in sorted(Path(directory).iterdir())
               if (d / "expect.txt").exists()]
    return {"passed": all(r.passed for r in results),
            "tests": [r.to_dict() for r in results]}


def main() -> None:
    srv.run()


if __name__ == "__main__":
    main()
