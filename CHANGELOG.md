# Changelog

All notable changes to PET Project (`pet-tools` / `petlib`). Dates are the
day the release was tagged.

## [1.1.0] — 2026-07-12

The dogfooding release: everything here came out of building real software
with the toolset — the six demo prompts, capped by an arcade-faithful
Invaders in 6502 assembly (demo 06, first-try pass; the playable
`invaders.d64` ships in `demos/invaders/`).

### Added
- **Per-session monitor daemon** — the machine's run/stop state persists
  across commands, so a breakpoint halt survives any number of inspection
  steps; `pet status` reports the tracked state (also on `pet reg`).
- **`pet package`** — one-step shareable artifacts: a `.prg`, or a
  `.d64`/`.d80`/`.d82` whose first file autostarts in stock VICE.
- **`pet key hold KEY --frames N --at LABEL`** — held-key game input via the
  `$97` key-down byte, re-poked before each frame-step (CLI + MCP).
- **Address forms** `symbol+offset` (`alienX+49`) and `@row,col` (screen
  cell, resolved against the session model's 40/80-column geometry),
  accepted everywhere an address is.
- **`poke:` and `until:` steps** in the `pet test run` YAML — deterministic
  frame-stepped game regression tests (see
  `demos/invaders/invaders-test.yaml`); step addresses take symbols,
  offsets, and `@row,col`.
- `pet mem find` byte-pattern search; decimal reads (`pet mem get`,
  `--decimal`, `bytes[]` in JSON output).
- `pet break clear` / `pet watch clear`.
- The `pet2001-4k` launch profile (the 4 KB entry-level 1977 PET).
- Cookbook recipes, all live-tested: held-key input ($97), charset
  switching, BASIC score HUD, decimal digits, IRQ wedge, note-table melody,
  Galois-LFSR random bytes, plotaddr, poked HUD text.
- Demos 05 (debug hunt) and 06 (Invaders) dogfooded — every demo has now
  passed on a real agent's first attempt.

### Performance
- **Fast frame stepping**: the `pet until --count` loop runs inside the
  session daemon, and the monitor consumes stop events the moment they land
  instead of listening out the poll window — 200 arrivals in ~0.3 s where
  each previously cost ~0.5 s.

### Fixed
- `pet package` run hints pin the emulated model
  (`xpet -model 4032 game.d64`): stock xpet boots its own default model,
  and ROM behavior differs silently between BASIC generations — the `$97`
  key-down byte holds decoded PETSCII on BASIC 4 but a raw matrix index on
  BASIC 2, which reads as a dead keyboard on an identical-looking screen.
- `pet until` / `pet wait` timeouts are loud about leaving the machine
  running (and `until` removes its checkpoint).

### Documentation
- `$97` semantics corrected in the zero-page and hardware references
  (PETSCII vs matrix index, with the scanner addresses pinned by live
  tests on pet4032 and pet3032).
- Warp discipline and wait-polling pitfalls in the pet-development skill;
  the BSS-is-not-in-the-.prg gotcha in the 6502-assembly skill.
- How `pet screen` decodes graphics/reverse-video, with live-verified
  free zero-page bytes for user ML pointers.

## [1.0.0] — 2026-07-10

Initial public release — the complete v1 toolset:

- **Sessions** on VICE xpet: launch/attach/stop, six machine profiles
  (pet2001 through pet8296), `--warp`/`--headless`/`--disk`.
- **Observe**: `pet screen` (decoded text or PNG), `pet mem read/write`,
  `pet reg` with PC symbol annotation.
- **Build & run**: `pet build` (ca65/ld65 with the PET SYS-stub linker
  config), `pet basic tokenize/detokenize/type` (petcat), `pet load` /
  `pet run` with automatic label registration.
- **Debug**: symbolic breakpoints and watchpoints with conditions,
  `pet step`/`finish`/`continue`/`until`, and the `pet wait`
  synchronization primitive (`--text` / `--mem` / `--break`).
- **Disks**: `pet disk create/ls/put/get/boot` via c1541.
- **ROM tools**: `pet rom info` (ROM-set identification) and annotated
  live disassembly — reading bytes from the user's emulator, shipping none.
- **Testing**: the declarative YAML runner (`pet test run`) and example
  programs as regression tests (`pet test programs`).
- **MCP server** (`pet-tools-mcp`) exposing the same operations as the CLI
  against the same sessions.
- **AI enablement**: the `pet-development` and `6502-assembly` skills, the
  machine/zero-page/ROM/PETSCII references, `docs/cli.md`, and the graded
  demo prompts (01–04 dogfooded at release).
