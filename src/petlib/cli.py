"""The `pet` command-line interface. Thin layer over petlib; all commands
support --json for machine-readable output."""

from __future__ import annotations

import json as _json
import sys

import click

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
