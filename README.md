<p align="center">
  <img src="img/logo.png" alt="PET Project logo" width="360">
</p>

# PET Project

AI-oriented toolset for developing and debugging Commodore PET software
(Commodore BASIC and 6502 assembly) on the VICE emulator.

> The Python package is imported as `petlib`, installed as `pet-tools`, and
> driven by the `pet` command-line tool.

## Install

Requires **Python 3.11+**, **VICE 3.5+** (provides `xpet` and `petcat`), and
the **cc65** suite (`ca65`/`ld65`, for assembling 6502 programs). Then install
this package.

macOS (Homebrew):

    brew install vice cc65
    pip install -e .

Debian / Ubuntu:

    sudo apt install vice cc65
    pip install -e .

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

    pet test run mytest.yaml               # declarative YAML test (spec §8)
    pet test demos                         # run every demo as a test

Every command takes `--json` for machine-readable output — the intended
interface for AI agents.

## Using with AI coding agents

**Any agent with a shell needs zero setup.** Run `pet --help`, give every
command `--json` for machine-readable output, and point the agent at the full
reference in [`docs/cli.md`](docs/cli.md) and the skills in
[`skills/`](skills/). That is the whole integration for a shell-capable agent.

**MCP.** For MCP-native clients, the `pet-tools-mcp` server exposes the same
operations as MCP tools over stdio, sharing the session registry with the CLI —
use either interchangeably. The standard config block is:

```json
{
  "mcpServers": {
    "pet-tools": { "command": "pet-tools-mcp" }
  }
}
```

Per-agent specifics (config file + where to put project instructions;
**agent configs verified July 2026** — conventions change, so check current
docs if something has moved):

- **Claude Code** — instructions in `CLAUDE.md`; skills go in
  `.claude/skills/<name>/` (copy or symlink this repo's `skills/*`). Add the
  MCP with `claude mcp add pet-tools -- pet-tools-mcp`, or a project
  `.mcp.json` holding the block above.
- **OpenAI Codex** — instructions in `AGENTS.md`; add the MCP with
  `codex mcp add pet-tools -- pet-tools-mcp`, or edit `~/.codex/config.toml`
  (project-scoped `.codex/config.toml` for trusted projects) with
  `[mcp_servers.pet_tools]` / `command = "pet-tools-mcp"`.
- **Cursor** — rules in `.cursor/rules/*.mdc` (or a plain `AGENTS.md`); MCP in
  `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) using the block
  above.
- **Gemini CLI** — instructions in `GEMINI.md`; MCP in `.gemini/settings.json`
  (project) or `~/.gemini/settings.json` under `mcpServers`.
- **Google Antigravity** — instructions via `AGENTS.md`; MCP in the shared
  `~/.gemini/config/mcp_config.json` (or the MCP store → Manage MCP Servers →
  View raw config), using the block above.

Whichever agent you use, point its instructions file (`CLAUDE.md` / `AGENTS.md`
/ `GEMINI.md` / Cursor rules) at
[`skills/pet-development/SKILL.md`](skills/pet-development/SKILL.md) so the agent
learns the PET workflows and the machine references.

## Demos

`demos/` holds one-shot prompts paired with reference BASIC and assembly
solutions and expected screen output. The integration suite builds and runs
each demo on an emulated PET, so they double as end-to-end tests. Run them
all with `pet test demos` — demos and YAML tests share one execution engine.

## Status

Control plane, build pipeline, debugging surface, disk/ROM tooling, the
scripted test runner, and the MCP server complete: sessions, screen, memory,
registers, `pet build` (ca65/ld65), `pet basic` (petcat), `pet load`/`pet run`,
symbolic breakpoints and watchpoints with conditions, `pet step`/`finish`/
`continue`/`until`, the `pet wait` synchronization primitive, `pet disk`
(create/ls/put/get/boot via c1541), `pet rom info`/`disasm`, `pet test`
(declarative YAML tests + demos), and `pet-tools-mcp` (MCP server). Coming
next: Claude skills + reference docs (and the install/agent-onboarding
README section). Design: `docs/superpowers/specs/`.

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
