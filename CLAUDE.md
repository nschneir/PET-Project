# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PET Project (package `petlib`, distributed as `pet-tools`): an AI-oriented toolset for developing and debugging Commodore PET software on the VICE emulator. Two front ends — the `pet` CLI and the `pet-tools-mcp` MCP server — drive the same session machinery. The repo is public at https://github.com/nschneir/PET-Project; design docs under `docs/superpowers/` are local-only (gitignored, purged from published history) — never commit or push them.

## Commands

```sh
pip install -e ".[dev]"        # install with pytest

pytest                          # full suite (vice-marked tests need xpet/VICE on PATH)
pytest -m "not vice"            # unit tests only — no emulator required
pytest tests/test_monitor.py    # one file
pytest tests/test_monitor.py::test_name   # one test

.venv/bin/python -m coverage run -m pytest && .venv/bin/python -m coverage combine && .venv/bin/python -m coverage report
                                # coverage (fail_under=90); subprocesses (daemon, MCP stdio) are measured too
```

Tests marked `@pytest.mark.vice` launch a real VICE emulator (`xpet`); everything else runs against `tests/fake_vice.py`, an in-process fake of the VICE binary monitor. `pet build` needs cc65 (`ca65`/`ld65`); `pet basic` needs `petcat`; `pet disk` needs `c1541` — all external subprocesses.

No linter/formatter is configured; match the existing style.

## Architecture

Layered, bottom-up in `src/petlib/`:

1. **`protocol.py`** — pure encode/decode of the VICE binary monitor protocol (API v2). No sockets.
2. **`monitor.py`** — `MonitorClient`, the socket client. Core contract: *processing any monitor command leaves the emulated machine STOPPED*; callers wanting it running must call `resume()`.
3. **The session daemon** (`daemon.py`, `rpc.py`, `daemon_client.py`) — VICE accepts only one monitor connection and resumes the CPU when it closes, so a per-session daemon process holds that single connection for the session's lifetime. Each `pet`/MCP command is a short-lived client on the session's unix socket; `DaemonMonitorClient` is a `MonitorClient` look-alike whose methods are JSON-lines RPC calls (`rpc.py` is the wire codec). This is what makes debug state (a breakpoint halt) persist across commands.
4. **`session.py`** — launch/attach/stop VICE, session records as JSON under `~/.pet-tools` (override with `PET_TOOLS_HOME`). `Session.monitor()` returns the daemon client.
5. **`ops.py`** — shared high-level operations (wait/until primitives, symbol resolution). Exists so the CLI and MCP server cannot drift; put new front-end-facing logic here, not in `cli.py` or `mcp_server.py`.
6. **Front ends** — `cli.py` (click; every command supports `--json`, the intended AI interface) and `mcp_server.py` (FastMCP; returns the same structured data as `--json`).

Supporting modules: `machines.py` (PET model profiles — RAM size, screen width, zero-page differences), `build.py` (ca65/ld65), `basic.py` (petcat tokenize/detokenize), `disk.py` (c1541 d64 images), `screen.py`/`text.py` (screen RAM ↔ text), `symbols.py` (.lbl label files), `disasm.py`, `romdoc.py` (ROM identification/annotation — ships only original label annotations, never Commodore ROM bytes), `packaging.py` (`pet package` → shareable .d64/.prg), `testing.py` (declarative YAML test runner).

## Docs are tested

The `tests/test_docs_*.py` files verify documentation against reality — e.g. every command path in `docs/cli.md` and the skills/README examples must exist in the real click tree (`tests/doc_helpers.py`). When you change the CLI surface, update `docs/cli.md`, `README.md`, and `skills/` in the same change or those tests fail.