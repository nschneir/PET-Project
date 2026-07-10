"""The `pet` command-line interface. Thin layer over petlib; all commands
support --json for machine-readable output."""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import click

from .basic import BasicError, detokenize, tokenize
from .build import BuildError, build_asm
from .disasm import disassemble
from .disk import DiskError, create_image, get_file, list_files, put_file
from .machines import get_profile
from .ops import (
    parse_number,
    parse_ref,
    pc_symbol as _pc_symbol,
    run_until,
    session_labels,
    wait_for_break,
    wait_for_mem,
    wait_for_text,
)
from .romdoc import identify, rom_labels
from .protocol import CP_EXEC, CP_LOAD, CP_STORE
from .screen import read_screen_text, save_screenshot_png
from .session import Session, SessionError
from .symbols import format_addr
from .testing import TestError, load_test, program_test, run_test
from .text import ascii_to_petscii


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


def resolve_ref(ctx: click.Context, labels: dict[str, int], ref: str) -> int:
    try:
        return parse_ref(labels, ref)
    except KeyError as e:
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
@click.option("--disk", "disk8", default=None, help="Attach a d64/d80/d82 image to drive 8.")
@click.pass_context
def session_start(ctx, model, name, headless, warp, disk8):
    try:
        s = Session.launch(model=model, name=name, headless=headless, warp=warp, disk8=disk8)
    except (SessionError, DiskError, KeyError) as e:
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
    sym = _pc_symbol(session_labels(s), regs)
    human = "  ".join(f"{k}={v:04x}" for k, v in sorted(regs.items()))
    if sym:
        human += f"  ({sym})"
    emit(ctx, {"registers": regs, "pc_symbol": sym}, human)


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


@main.command("build")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--model", default="pet4032", show_default=True)
@click.pass_context
def build_cmd(ctx, source, output, model):
    """Assemble 6502 source to a .prg (+ VICE label file) with ca65/ld65."""
    try:
        profile = get_profile(model)
        res = build_asm(source, out_prg=output, basic_start=profile.basic_start)
    except (BuildError, KeyError) as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"prg": str(res.prg), "labels": str(res.labels)},
         f"built {res.prg} (labels: {res.labels})")


@main.group()
def basic() -> None:
    """Tokenize, detokenize, and type Commodore BASIC programs."""


@basic.command("tokenize")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--model", default="pet4032", show_default=True)
@click.pass_context
def basic_tokenize(ctx, source, output, model):
    out = output or source.with_suffix(".prg")
    try:
        profile = get_profile(model)
        prg = tokenize(source, out, profile.basic_version)
    except (BasicError, KeyError) as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"prg": str(prg)}, f"tokenized to {prg}")


@basic.command("detokenize")
@click.argument("prg", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--model", default="pet4032", show_default=True)
@click.pass_context
def basic_detokenize(ctx, prg, model):
    try:
        profile = get_profile(model)
        listing = detokenize(prg, profile.basic_version)
    except (BasicError, KeyError) as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"listing": listing}, listing.rstrip("\n"))


@basic.command("type")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--run", "do_run", is_flag=True, help="Type RUN after the program.")
@click.pass_context
def basic_type(ctx, source, do_run):
    """Type a BASIC program into the running PET via the keyboard."""
    s = attach(ctx)
    text = source.read_text()
    if not text.endswith("\n"):
        text += "\n"
    if do_run:
        text += "run\n"
    try:
        petscii = ascii_to_petscii(text)
    except ValueError as e:
        fail(ctx, str(e))
        return
    with s.monitor() as mon:
        try:
            mon.keyboard_feed(petscii)
        finally:
            mon.resume()
    emit(ctx, {"typed": str(source), "run": do_run},
         f"typed {source}{' and RUN' if do_run else ''}")


@main.command("load")
@click.argument("prg", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--run/--no-run", "do_run", default=True, show_default=True)
@click.option("--symbols", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.pass_context
def load_cmd(ctx, prg, do_run, symbols):
    """Load (and by default RUN) a .prg on the running PET via autostart."""
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.autostart(prg.resolve(), run=do_run)
        finally:
            mon.resume()
    if symbols:
        s.set_labels_path(str(symbols.resolve()))
    emit(ctx, {"loaded": str(prg.resolve()), "run": do_run,
               "symbols": str(symbols.resolve()) if symbols else None},
         f"autostarted {prg}{'' if do_run else ' (no RUN)'}")


@main.command("run")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def run_cmd(ctx, source):
    """Build/tokenize SOURCE as needed, then load and RUN it."""
    s = attach(ctx)
    src = source.resolve()
    ext = src.suffix.lower()
    labels = None
    try:
        if ext == ".prg":
            prg = src
        elif ext == ".bas":
            prg = tokenize(src, src.with_suffix(".prg"), s.profile.basic_version)
        elif ext == ".s":
            res = build_asm(src, basic_start=s.profile.basic_start)
            prg, labels = res.prg, res.labels
        else:
            fail(ctx, f"don't know how to run {ext!r} files (use .bas, .s, or .prg)")
            return
    except (BasicError, BuildError) as e:
        fail(ctx, str(e))
        return
    with s.monitor() as mon:
        try:
            mon.autostart(prg, run=True)
        finally:
            mon.resume()
    if labels:
        s.set_labels_path(str(labels))
    emit(ctx, {"source": str(src), "prg": str(prg),
               "symbols": str(labels) if labels else None},
         f"running {prg}")


@main.group("break")
def break_() -> None:
    """Manage breakpoints (VICE exec checkpoints)."""


@break_.command("add")
@click.argument("ref")
@click.option("--condition", default=None, help="VICE condition, e.g. 'A != 0'.")
@click.option("--temporary", is_flag=True)
@click.pass_context
def break_add(ctx, ref, condition, temporary):
    s = attach(ctx)
    labels = session_labels(s)
    addr = resolve_ref(ctx, labels, ref)
    with s.monitor() as mon:
        try:
            ck = mon.checkpoint_set(addr, op=CP_EXEC, temporary=temporary)
            if condition:
                mon.condition_set(ck.number, condition)
        finally:
            mon.resume()
    emit(ctx, {"id": ck.number, "address": format_addr(labels, addr),
               "condition": condition, "temporary": temporary},
         f"breakpoint #{ck.number} at {format_addr(labels, addr)}"
         + (f" when {condition}" if condition else ""))


def _op_name(op: int) -> str:
    parts = []
    if op & CP_EXEC:
        parts.append("exec")
    if op & CP_LOAD:
        parts.append("load")
    if op & CP_STORE:
        parts.append("store")
    return "|".join(parts)


@break_.command("list")
@click.pass_context
def break_list(ctx):
    s = attach(ctx)
    labels = session_labels(s)
    with s.monitor() as mon:
        try:
            cks = mon.checkpoint_list()
        finally:
            mon.resume()
    rows = [{"id": ck.number, "address": format_addr(labels, ck.start),
             "end": ck.end, "op": _op_name(ck.op), "enabled": ck.enabled,
             "hits": ck.hit_count, "has_condition": ck.has_condition}
            for ck in cks]
    human = "\n".join(
        f"#{r['id']}  {r['address']}  {r['op']}"
        f"  {'on' if r['enabled'] else 'off'}  hits={r['hits']}"
        + ("  [cond]" if r["has_condition"] else "")
        for r in rows
    ) or "no breakpoints"
    emit(ctx, {"breakpoints": rows}, human)


@break_.command("remove")
@click.argument("ck_id", type=int)
@click.pass_context
def break_remove(ctx, ck_id):
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.checkpoint_delete(ck_id)
        finally:
            mon.resume()
    emit(ctx, {"removed": ck_id}, f"removed #{ck_id}")


@break_.command("enable")
@click.argument("ck_id", type=int)
@click.pass_context
def break_enable(ctx, ck_id):
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.checkpoint_toggle(ck_id, True)
        finally:
            mon.resume()
    emit(ctx, {"enabled": ck_id}, f"enabled #{ck_id}")


@break_.command("disable")
@click.argument("ck_id", type=int)
@click.pass_context
def break_disable(ctx, ck_id):
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.checkpoint_toggle(ck_id, False)
        finally:
            mon.resume()
    emit(ctx, {"disabled": ck_id}, f"disabled #{ck_id}")


@main.group()
def watch() -> None:
    """Manage watchpoints (VICE load/store checkpoints)."""


@watch.command("add")
@click.argument("ref")
@click.option("--load", "on_load", is_flag=True)
@click.option("--store", "on_store", is_flag=True)
@click.option("--length", default=1, show_default=True)
@click.pass_context
def watch_add(ctx, ref, on_load, on_store, length):
    s = attach(ctx)
    labels = session_labels(s)
    addr = resolve_ref(ctx, labels, ref)
    op = (CP_LOAD if on_load else 0) | (CP_STORE if on_store else 0)
    if not op:
        op = CP_LOAD | CP_STORE
    with s.monitor() as mon:
        try:
            ck = mon.checkpoint_set(addr, addr + length - 1, op=op)
        finally:
            mon.resume()
    emit(ctx, {"id": ck.number, "address": format_addr(labels, addr),
               "length": length, "op": _op_name(op)},
         f"watchpoint #{ck.number} at {format_addr(labels, addr)} len={length} ({_op_name(op)})")


def _emit_stopped_regs(ctx, labels, regs):
    sym = _pc_symbol(labels, regs)
    human = "  ".join(f"{k}={v:04x}" for k, v in sorted(regs.items()))
    if sym:
        human += f"  ({sym})"
    emit(ctx, {"registers": regs, "pc_symbol": sym, "stopped": True},
         human + "  [stopped]")


@main.command("step")
@click.argument("count", default="1")
@click.option("--over", is_flag=True, help="Step over JSR subroutines.")
@click.pass_context
def step_cmd(ctx, count, over):
    """Execute N instructions; the machine stays stopped."""
    s = attach(ctx)
    labels = session_labels(s)
    with s.monitor() as mon:
        regs = mon.step(parse_number(count), over=over)
    _emit_stopped_regs(ctx, labels, regs)


@main.command("finish")
@click.pass_context
def finish_cmd(ctx):
    """Run until the current subroutine returns; stays stopped."""
    s = attach(ctx)
    labels = session_labels(s)
    with s.monitor() as mon:
        regs = mon.finish()
    _emit_stopped_regs(ctx, labels, regs)


@main.command("continue")
@click.pass_context
def continue_cmd(ctx):
    """Resume execution."""
    s = attach(ctx)
    with s.monitor() as mon:
        mon.resume()
    emit(ctx, {"running": True}, "running")


@main.command("until")
@click.argument("ref")
@click.option("--timeout", default=30.0, show_default=True)
@click.pass_context
def until_cmd(ctx, ref, timeout):
    """Run until REF (address or symbol) is executed; stays stopped there."""
    s = attach(ctx)
    labels = session_labels(s)
    addr = resolve_ref(ctx, labels, ref)
    regs = run_until(s, addr, timeout)
    if regs is None:
        fail(ctx, f"timeout: {format_addr(labels, addr)} not reached in {timeout}s")
        return
    _emit_stopped_regs(ctx, labels, regs)


@main.command("wait")
@click.option("--text", "text_cond", default=None, help="Wait for screen text.")
@click.option("--mem", "mem_cond", default=None, help="ADDR=VALUE, e.g. '$1000=42'.")
@click.option("--break", "break_cond", is_flag=True, help="Wait for a checkpoint hit.")
@click.option("--timeout", default=30.0, show_default=True)
@click.pass_context
def wait_cmd(ctx, text_cond, mem_cond, break_cond, timeout):
    """Block until a condition fires; reports which one in JSON."""
    if sum(bool(x) for x in (text_cond, mem_cond, break_cond)) != 1:
        fail(ctx, "give exactly one of --text, --mem, --break")
        return
    s = attach(ctx)
    labels = session_labels(s)

    if break_cond:
        out = wait_for_break(s, timeout)
        if not out.get("fired"):
            fail(ctx, f"timeout: no checkpoint hit within {timeout}s")
            return
        sym = _pc_symbol(labels, out.pop("registers"))
        emit(ctx, {"fired": "break", "checkpoint": out["checkpoint"],
                   "pc": out["pc"], "pc_symbol": sym, "elapsed": out["elapsed"]},
             f"breakpoint #{out['checkpoint']} hit at {format_addr(labels, out['pc'])}")
        return

    if text_cond:
        out = wait_for_text(s, text_cond, timeout)
        if out["fired"]:
            emit(ctx, {"fired": "text", "elapsed": out["elapsed"]}, "text condition met")
            return
        fail(ctx, f"timeout after {timeout}s waiting for --text {text_cond}"
                  f"; last screen:\n{out['screen']}")
        return

    try:
        addr_s, _, val_s = mem_cond.partition("=")
        addr = resolve_ref(ctx, labels, addr_s.strip())
        want = parse_number(val_s.strip())
    except ValueError:
        fail(ctx, f"bad --mem condition {mem_cond!r}; use ADDR=VALUE")
        return
    out = wait_for_mem(s, addr, want, timeout)
    if out["fired"]:
        emit(ctx, {"fired": "mem", "elapsed": out["elapsed"]}, "mem condition met")
        return
    fail(ctx, f"timeout after {timeout}s waiting for --mem {mem_cond}")


@main.group()
def disk() -> None:
    """Create and manipulate d64/d80/d82 disk images."""


@disk.command("create")
@click.argument("image", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--label", default="disk", show_default=True)
@click.option("--id", "disk_id", default="00", show_default=True)
@click.pass_context
def disk_create(ctx, image, label, disk_id):
    try:
        img = create_image(image, label=label, disk_id=disk_id)
    except DiskError as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"image": str(img), "label": label}, f"created {img} (label {label!r})")


@disk.command("ls")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def disk_ls(ctx, image):
    try:
        d = list_files(image)
    except DiskError as e:
        fail(ctx, str(e))
        return
    human = "\n".join(
        [f'"{d["label"]}"']
        + [f"{f['blocks']:>4}  {f['name']:<18} {f['type']}" for f in d["files"]]
        + [f"{d['blocks_free']} blocks free"]
    )
    emit(ctx, d, human)


@disk.command("put")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("name", required=False, default=None)
@click.pass_context
def disk_put(ctx, image, file, name):
    try:
        cbm = put_file(image, file, name)
    except DiskError as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"image": str(image), "name": cbm}, f"wrote {file} as {cbm!r}")


@disk.command("get")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("name")
@click.argument("dest", required=False, default=None,
                type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def disk_get(ctx, image, name, dest):
    dest = dest or Path(f"{name}.prg")
    try:
        out = get_file(image, name, dest)
    except DiskError as e:
        fail(ctx, str(e))
        return
    emit(ctx, {"image": str(image), "name": name, "dest": str(out)},
         f"read {name!r} to {out}")


@disk.command("boot")
@click.argument("image", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def disk_boot(ctx, image):
    """Attach IMAGE to the running PET and LOAD+RUN its first file."""
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.autostart(image.resolve(), run=True)
        finally:
            mon.resume()
    emit(ctx, {"booted": str(image.resolve())}, f"booting {image}")


@main.group()
def rom() -> None:
    """Identify and disassemble the machine's ROMs (read from the live machine)."""


@rom.command("info")
@click.pass_context
def rom_info(ctx):
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            info = identify(mon)
        finally:
            mon.resume()
    human = "\n".join(
        [f"basic:  {info['basic']}", f"kernal: {info['kernal']}",
         f"editor: {info['editor']}"]
        + [f"hash {k}: {v}" for k, v in info["hashes"].items()]
    )
    emit(ctx, info, human)


@rom.command("disasm")
@click.argument("start")
@click.argument("length", default="32")
@click.pass_context
def rom_disasm(ctx, start, length):
    """Disassemble live memory with ROM + session label annotations."""
    s = attach(ctx)
    labels = {**rom_labels(s.profile.basic_version), **session_labels(s)}
    addr = resolve_ref(ctx, labels, start)
    n = parse_number(length)
    with s.monitor() as mon:
        try:
            data = mon.memory_read(addr, n)
        finally:
            mon.resume()
    lines = disassemble(data, addr, labels)
    emit(ctx, {"start": addr, "length": n, "lines": lines}, "\n".join(lines))


@main.group("test")
def test_() -> None:
    """Run declarative YAML tests and example programs on a fresh emulated PET."""


def _emit_test_results(ctx, results) -> None:
    all_pass = all(r.passed for r in results)
    lines = []
    for r in results:
        lines.append(f"{'PASS' if r.passed else 'FAIL'}  {r.name}  "
                     f"({r.machine}, {r.elapsed}s)")
        for st in r.steps:
            lines.append(f"  {'ok  ' if st.ok else 'FAIL'} step {st.index} "
                         f"{st.kind}: {st.detail}")
        if not r.passed:
            lines.append("  --- screen at failure ---")
            lines.extend(f"  | {ln}" for ln in r.screen.splitlines())
    emit(ctx, {"passed": all_pass, "tests": [r.to_dict() for r in results]},
         "\n".join(lines))
    if not all_pass:
        sys.exit(1)


@test_.command("run")
@click.argument("yaml_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_context
def test_run(ctx, yaml_file):
    """Run one YAML test file (spec §8 format)."""
    try:
        spec = load_test(yaml_file)
        result = run_test(spec)
    except (TestError, KeyError, BasicError, BuildError, SessionError) as e:
        fail(ctx, str(e))
        return
    _emit_test_results(ctx, [result])


@test_.command("programs")
@click.argument("directory", default="tests/programs",
                type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def test_programs(ctx, directory):
    """Run every example program in DIRECTORY as a generated test."""
    program_dirs = sorted(d for d in directory.iterdir() if (d / "expect.txt").exists())
    if not program_dirs:
        fail(ctx, f"no example programs found in {directory}")
        return
    results = []
    for d in program_dirs:
        try:
            results.append(run_test(program_test(d)))
        except (TestError, KeyError, BasicError, BuildError, SessionError) as e:
            fail(ctx, f"{d.name}: {e}")
            return
    _emit_test_results(ctx, results)


@main.group()
def key() -> None:
    """Feed keyboard input to the running PET."""


@key.command("type")
@click.argument("text")
@click.pass_context
def key_type(ctx, text):
    """Type TEXT into the running PET (\\n = RETURN). For whole programs
    prefer `pet basic type`; this is for interactive input and game keys."""
    try:
        petscii = ascii_to_petscii(text)
    except ValueError as e:
        fail(ctx, str(e))
        return
    s = attach(ctx)
    with s.monitor() as mon:
        try:
            mon.keyboard_feed(petscii)
        finally:
            mon.resume()
    emit(ctx, {"typed_chars": len(petscii)}, f"typed {text!r}")
