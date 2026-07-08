# pet-tools

AI-oriented toolset for developing and debugging Commodore PET software
(Commodore BASIC and 6502 assembly) on the VICE emulator.

## Requirements

- Python 3.11+
- VICE 3.5+ with `xpet` on PATH (macOS: `brew install vice`; Debian/Ubuntu: `apt install vice`)

## Quickstart

    pip install -e .
    pet session start --model pet4032      # boot an emulated PET 4032
    pet screen                             # read the screen as text
    pet screen --png shot.png              # ... or as an image
    pet mem read '$8000' 64                # hex dump of screen RAM
    pet mem write '$8000' 8 9              # poke screen codes "HI"
    pet reg                                # CPU registers
    pet session stop

Every command takes `--json` for machine-readable output — the intended
interface for AI agents.

## Status

Control plane complete (this plan: sessions, screen, memory, registers).
Coming next: build pipeline (ca65/petcat), symbolic debugging, disk images,
test runner, MCP server, Claude skills. Design: `docs/superpowers/specs/`.

## License

MIT. VICE is a separate GPLv2+ program invoked as a subprocess; it is not
bundled and must be installed separately.
