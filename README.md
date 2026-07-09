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
    pet reg                                # CPU registers
    pet session stop

Every command takes `--json` for machine-readable output — the intended
interface for AI agents.

## Demos

`demos/` holds one-shot prompts paired with reference BASIC and assembly
solutions and expected screen output. The integration suite builds and runs
each demo on an emulated PET, so they double as end-to-end tests.

## Status

Control plane and build pipeline complete: sessions, screen, memory,
registers, `pet build` (ca65/ld65), `pet basic` (petcat), `pet load`/`pet run`.
Coming next: symbolic debugging (breakpoints/step/wait), disk images,
test runner, MCP server, Claude skills. Design: `docs/superpowers/specs/`.

## License

MIT. VICE is a separate GPLv2+ program invoked as a subprocess; it is not
bundled and must be installed separately.
