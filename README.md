<p align="center">
  <img src="img/logo.png" alt="PET Project logo" width="360">
</p>

# PET Project

AI-oriented toolset for developing and debugging Commodore PET software
(Commodore BASIC and 6502 assembly) on the VICE emulator.

> The Python package is imported as `petlib`, installed as `pet-tools`, and
> driven by the `pet` command-line tool.

## Requirements

- Python 3.11+
- VICE 3.5+ with `xpet` and `petcat` on PATH (macOS: `brew install vice`; Debian/Ubuntu: `apt install vice`)
- cc65 suite (`ca65`/`ld65`) for assembling 6502 programs (macOS: `brew install cc65`; Debian/Ubuntu: `apt install cc65`)

## Quickstart

    pip install -e .
    pet session start --model pet4032      # boot an emulated PET 4032
    pet run demos/hello-basic/program.bas  # tokenize + load + RUN
    pet run demos/hello-asm/program.s      # assemble + load + RUN (needs cc65)
    pet screen                             # read the screen as text
    pet basic type prog.bas --run          # type a program via the keyboard
    pet mem read '$8000' 64                # hex dump of screen RAM
    pet break add start                    # symbolic breakpoint (uses .lbl symbols)
    pet wait --break                       # block until it fires
    pet step 5 && pet reg                  # single-step, inspect (PC annotated)
    pet continue                           # resume
    pet disk create work.d64 && pet disk put work.d64 game.prg game
    pet session start --disk work.d64      # boot with the disk attached
    pet disk boot work.d64                 # or attach+run mid-session
    pet rom info                           # identify the loaded ROM set
    pet rom disasm CHROUT 16               # annotated live disassembly
    pet session stop

Every command takes `--json` for machine-readable output — the intended
interface for AI agents.

## Demos

`demos/` holds one-shot prompts paired with reference BASIC and assembly
solutions and expected screen output. The integration suite builds and runs
each demo on an emulated PET, so they double as end-to-end tests.

## Status

Control plane, build pipeline, debugging surface, and disk/ROM tooling
complete: sessions, screen, memory, registers, `pet build` (ca65/ld65),
`pet basic` (petcat), `pet load`/`pet run`, symbolic breakpoints and
watchpoints with conditions, `pet step`/`finish`/`continue`/`until`, the
`pet wait` synchronization primitive, `pet disk` (create/ls/put/get/boot via
c1541), and `pet rom info`/`disasm`. Coming next: the scripted test runner,
then the MCP server and Claude skills. Design: `docs/superpowers/specs/`.

ROM tooling reads ROM bytes from your running emulator and ships only
original label annotations — no Commodore-copyrighted code lives in this repo.

## AI Disclosure

PET Project is developed primarily by AI — Anthropic's Claude, working
through Claude Code — under human direction: a human sets the goals,
reviews the designs and plans, and approves the work; the AI writes the
specs, plans, code, tests, and documentation. Every change is verified by
the automated test suite, including integration tests that run against a
real VICE emulator, before it lands. The project also exists *for* AI use —
these tools are built so AI agents can write and debug Commodore PET
software — making it a working example of AI-built developer tooling.

## License

MIT. VICE is a separate GPLv2+ program invoked as a subprocess; it is not
bundled and must be installed separately.
