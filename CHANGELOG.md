# Changelog

All notable changes to PET Project (`pet-tools` / `petlib`). Dates are the
day the release was tagged.

## [1.2.0] — 2026-07-21

The friction-fixes release: every change answers a concrete pain point hit
while building Ms. Muncher (demo 07, an arcade-faithful maze chaser in
`demos/muncher/`) with the 1.1 toolset.

### Added
- **Stale-binary guard** — the trap that cost the most dogfood time: a
  failed rebuild left the emulator running the previous binary while
  "verification" proceeded against it. `pet build` now records the full
  dependency list (ca65 `--create-dep`, so `.include`d files count);
  `pet run`/`pet load` stamp load provenance on the session; `pet status`
  reports the loaded program and a loud `STALE (source changed since
  load:)` line; a failed `pet run` says the emulator is still running the
  PREVIOUS program.
- **Unicode screen decoding** — `pet screen` now decodes graphics codes to
  real box/block/shape glyphs (`╭─╮ ● ▌ █ …`), with reverse-video codes
  mapped to their pixel-complement glyph where Unicode has one
  (`▌`↔`▐`, quadrants → `▛▜▙▟`, `$A0` → `█`); `--ansi-reverse` for
  terminal inverse on the rest, `--style ascii` for the legacy mapping.
  **Migration:** `wait --text` patterns matching the old `·` placeholder
  need updating (plain text is unaffected) — see docs/cli.md.
- **`pet screen --codes`** — the raw 25×40 screen-code matrix (exact glyph
  assertions), and **`pet screen --png --scale N`** — nearest-neighbour
  upscale (PET screens read better at 2–3×).
- **`pet session ensure`** — attach-or-start, idempotent; the recovery
  one-liner the daemon circuit-breaker error now points at. A test
  documents the `pet test run` isolation contract (throwaway uniquely
  named session, user sessions untouched).
- **CLI paper cuts** — `pet break rm` / `pet watch remove` / `pet watch
  rm`; `pet break add --once`; `pet wait --break CK_ID` (id filter so a
  leftover breakpoint can't intercept a watchpoint wait); `pet mem write
  --stdin` (batch `REF V1 V2 …` lines, heredoc-friendly).
- **Richer YAML asserts** — `equals_any` (alternatives), `mask`
  (`{and: $7f, equals: [...]}` — e.g. ignore the reverse-video bit), and
  `between` (`{min, max}` byte range).

### Fixed
- Unknown symbol in an arithmetic ref (`dots+82`) now reports the symbol
  (`dots`, with candidates), not the whole string.
- `wait_for_break`'s stop-event fast path respects the checkpoint filter.

### Documentation
- 6502-assembly skill: growing code breaks short branches (prefer `jmp`
  trampolines in blocks expected to grow); ca65 segment state carries
  across `.include` (start every include with an explicit `.segment`).
  Both hit repeatedly during the dogfood; pet-development cross-references
  the symptoms.

## [1.1.0] — 2026-07-12

The dogfooding release: everything here came out of building real software
with the toolset — the six demo prompts, capped by an arcade-faithful
Invaders in 6502 assembly (demo 06; the playable
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
- Demos 05 (debug hunt) and 06 (Invaders) dogfooded. 05 passed on the
  agent's first attempt; 06 needed one follow-up prompt — the first
  build's keyboard was dead under stock xpet's default model (the
  BASIC 2 vs 4 `$97` split fixed above).

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
