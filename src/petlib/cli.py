"""The `pet` command-line interface. Thin layer over petlib; all commands
support --json for machine-readable output."""

from __future__ import annotations

import json as _json
import sys

import click

from .machines import get_profile
from .screen import read_screen_text, save_screenshot_png
from .session import Session, SessionError


def emit(ctx: click.Context, data: dict, human: str) -> None:
    if ctx.obj["json"]:
        click.echo(_json.dumps(data))
    else:
        click.echo(human)


def fail(ctx: click.Context, message: str) -> None:
    if ctx.obj["json"]:
        click.echo(_json.dumps({"error": message}))
    else:
        click.echo(f"error: {message}", err=True)
    sys.exit(1)


def attach(ctx: click.Context) -> Session:
    try:
        return Session.attach(ctx.obj["session"])
    except SessionError as e:
        fail(ctx, str(e))
        raise AssertionError("unreachable")


@click.group()
@click.option("--json", "json_out", is_flag=True, help="Machine-readable JSON output.")
@click.option("--session", "-s", "session_name", default=None, help="Target session name.")
@click.pass_context
def main(ctx: click.Context, json_out: bool, session_name: str | None) -> None:
    """pet-tools: develop and debug Commodore PET software on VICE."""
    ctx.obj = {"json": json_out, "session": session_name}


@main.group()
def session() -> None:
    """Manage emulator sessions."""


@session.command("start")
@click.option("--model", default="pet4032", show_default=True)
@click.option("--name", default=None)
@click.option("--headless", is_flag=True)
@click.option("--warp", is_flag=True)
@click.pass_context
def session_start(ctx, model, name, headless, warp):
    try:
        s = Session.launch(model=model, name=name, headless=headless, warp=warp)
    except (SessionError, KeyError) as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"name": s.name, "model": s.model, "pid": s.pid, "port": s.port},
         f"started {s.model} session {s.name!r} (pid {s.pid}, monitor port {s.port})")


@session.command("list")
@click.pass_context
def session_list(ctx):
    live = Session.list_all()
    emit(ctx,
         {"sessions": [{"name": s.name, "model": s.model, "pid": s.pid, "port": s.port}
                       for s in live]},
         "\n".join(f"{s.name}  {s.model}  pid={s.pid}  port={s.port}" for s in live)
         or "no sessions running")


@session.command("stop")
@click.argument("name", required=False)
@click.pass_context
def session_stop(ctx, name):
    try:
        s = Session.attach(name or ctx.obj["session"])
    except SessionError as e:
        fail(ctx, str(e))
        return
    s.stop()
    emit(ctx, {"stopped": s.name}, f"stopped session {s.name!r}")


@session.command("reset")
@click.option("--hard", is_flag=True, help="Power-cycle instead of soft reset.")
@click.pass_context
def session_reset(ctx, hard):
    s = attach(ctx)
    with s.monitor() as mon:
        mon.reset(hard=hard)
        mon.resume()
    emit(ctx, {"reset": s.name, "hard": hard},
         f"{'hard' if hard else 'soft'} reset {s.name!r} (machine running)")


def parse_number(s: str) -> int:
    s = s.strip()
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def _hexdump(addr: int, data: bytes) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{addr + i:04x}: {hexpart:<47}  {asciipart}")
    return "\n".join(lines)


@main.command("screen")
@click.option("--png", "png_path", default=None, type=click.Path(dir_okay=False))
@click.pass_context
def screen_cmd(ctx, png_path):
    """Show the emulated screen (text by default, --png for an image)."""
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            if png_path:
                w, h = save_screenshot_png(mon, png_path)
                emit(ctx, {"png": png_path, "width": w, "height": h},
                     f"wrote {w}x{h} screenshot to {png_path}")
            else:
                text = read_screen_text(mon, s.profile)
                emit(ctx, {"text": text, "rows": text.splitlines()}, text)
        finally:
            mon.resume()


@main.group()
def mem() -> None:
    """Read and write emulated memory."""


@mem.command("read")
@click.argument("addr")
@click.argument("length", default="256")
@click.pass_context
def mem_read(ctx, addr, length):
    s = attach(ctx)
    start, n = parse_number(addr), parse_number(length)
    with s.monitor() as mon:
        try:
            data = mon.memory_read(start, n)
        finally:
            mon.resume()
    emit(ctx, {"addr": start, "length": len(data), "hex": data.hex()},
         _hexdump(start, data))


@mem.command("write")
@click.argument("addr")
@click.argument("values", nargs=-1, required=True)
@click.pass_context
def mem_write(ctx, addr, values):
    s = attach(ctx)
    start = parse_number(addr)
    data = bytes(parse_number(v) for v in values)
    with s.monitor() as mon:
        try:
            mon.memory_write(start, data)
        finally:
            mon.resume()
    emit(ctx, {"addr": start, "written": len(data)},
         f"wrote {len(data)} byte(s) at ${start:04x}")


@main.group(invoke_without_command=True)
@click.pass_context
def reg(ctx) -> None:
    """Show CPU registers (or `reg set NAME VALUE`)."""
    if ctx.invoked_subcommand is not None:
        return
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            regs = mon.registers()
        finally:
            mon.resume()
    human = "  ".join(f"{k}={v:04x}" for k, v in sorted(regs.items()))
    emit(ctx, {"registers": regs}, human)


@reg.command("set")
@click.argument("name")
@click.argument("value")
@click.pass_context
def reg_set(ctx, name, value):
    s = attach(ctx)
    v = parse_number(value)
    with s.monitor() as mon:
        try:
            mon.set_register(name, v)
        finally:
            mon.resume()
    emit(ctx, {"register": name.upper(), "value": v},
         f"{name.upper()} = ${v:04x}")
