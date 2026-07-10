---
name: pet-development
description: Use when developing, running, or debugging Commodore PET software (Commodore BASIC or 6502 assembly) on the VICE emulator with the pet CLI or the pet-tools MCP server. Covers the build/run/observe/debug loop, the stopped-state discipline, PET text encodings, and per-model differences.
---

# Developing for the Commodore PET

This skill drives an emulated Commodore PET through the `pet` command line (or
the equivalent `pet-tools` MCP tools). Full command reference: `docs/cli.md`.
Every command takes `--json` for machine-readable output.

## The loop

Write → run → observe → fix:

1. Write BASIC (`.bas`) or 6502 assembly (`.s`).
2. `pet run FILE` — tokenizes/assembles as needed, loads, and RUNs.
3. Observe with `pet screen` (decoded screen text) — this is the primary way
   to see output. Use `pet wait --text "..."` to block until expected output
   appears; loading and running take a few emulated seconds even in warp, so
   never assume a program has finished — wait for a signal.
4. Fix and repeat.

Start a machine with `pet session start` before anything else, and
`pet session stop` when done.

## Sessions and models

`pet session start --model pet4032` boots a PET 4032 (the default). Add
`--warp` to run at full speed for automation and `--headless` to suppress the
window. Models: `pet2001` (BASIC 1.0), `pet3032` (BASIC 2.0), `pet4032`
(BASIC 4.0), `pet8032` and `pet8296` (BASIC 4.0, 80-column). The 40- vs
80-column split matters when reading the screen; BASIC version matters for
which tokens and ROM routines exist.

## Writing BASIC

BASIC sources follow the `petcat` convention: **write keywords AND string
text in lowercase.** Lowercase ASCII maps to unshifted PETSCII, which the PET
displays as uppercase — so `10 print "hello"` shows on screen as
`10 PRINT "HELLO"`. Writing uppercase in the source produces shifted PETSCII,
which shows as graphics characters instead of letters. This is the single most
common mistake.

- `pet run prog.bas` — tokenize, load, and RUN in one step.
- `pet basic type prog.bas --run` — type the program in through the keyboard
  instead, which works mid-session and exercises the real ROM tokenizer.
- `pet basic tokenize` / `pet basic detokenize` — convert between `.bas` and
  `.prg` without a session.

## Writing assembly

6502 assembly is assembled with ca65/ld65 via `pet build` or run directly with
`pet run prog.s`. A PET program loads at `$0401` and needs a small BASIC `SYS`
stub so `RUN` starts it; the `6502-assembly` skill has the working skeleton and
the details. `pet run` on a `.s` file automatically registers the assembled
label file on the session, so you can immediately set symbolic breakpoints like
`pet break add start`.

## Debugging

Breakpoints and watchpoints are set while the machine runs, then you block on
them:

1. `pet break add SYMBOL` (or an address) — set an execution breakpoint. It
   also accepts `--condition 'A != 0'` and `--temporary`. Checkpoints survive a
   later `pet load`/`pet run`, so set the breakpoint first, then load.
2. `pet wait --break` — block until it fires; this leaves the machine stopped.
3. Inspect: `pet reg` (registers, PC annotated with the nearest symbol),
   `pet mem read ADDR LEN`, `pet break list`.
4. Single-step: `pet step N` (add `--over` to step over `JSR`s), `pet finish`
   (run to the current subroutine's return), or `pet until SYMBOL` (run to a
   point). Use `pet watch add ADDR --store` to break on writes.
5. `pet continue` to resume.

**The stopped-state rule.** Connecting to the emulator's monitor stops the CPU;
`pet` resumes it after each command *except* the four that intentionally leave
it stopped so you can inspect it: `pet step`, `pet finish`, `pet until`, and
`pet wait --break` when it fires. After any of those, the machine is paused
until you `pet continue` (or run another command that resumes it). Every other
command leaves the machine running.

## Text encodings — keep three straight

The PET uses three different byte encodings, and confusing them is a frequent
source of bugs:

- **ASCII** — what your host files and the CLI use.
- **PETSCII** — what the keyboard produces and what ROM output routines
  (CHROUT) consume. `$0D` is RETURN; letters are ASCII-uppercase codes.
- **Screen codes** — what actually sits in screen RAM at `$8000`. These are
  *not* PETSCII: `0` is `@`, `1`–`26` are `A`–`Z`, and bit 7 means reverse
  video. Reading screen RAM with `pet mem read '$8000'` shows raw screen codes;
  `pet screen` decodes them to text for you.

## Common pitfalls

- Uppercase in BASIC source → graphics garbage on screen (write lowercase).
- Forgetting to `pet wait` after `pet run` and reading the screen too early.
- Reading `$8000` and expecting ASCII — it holds screen codes.
- Assuming the machine is running after `pet step`/`finish`/`until` — it is
  stopped; `pet continue` to resume.

## Verifying a change

Prove a change works, don't assume it. Either assert on output with
`pet wait --text "EXPECTED"`, or write a declarative test and run it with
`pet test run mytest.yaml` (the YAML format is in the spec §8: a `program`,
optional `autorun`, and `wait`/`key`/`assert` steps). Existing example
programs can all be run as tests with `pet test demos`.

## References

Read the matching file when you need the detail:

- `references/memory-maps.md` — per-model memory layout (RAM, screen, ROM, I/O).
- `references/zero-page.md` — BASIC pointer chain and low-memory usage.
- `references/rom-routines.md` — kernal jump table and hardware vectors.
- `references/basic-internals.md` — program storage format and token table.
- `references/petscii.md` — the three text encodings and the screen-code table.
- `references/hardware.md` — I/O chip base addresses (PIA/VIA/CRTC), IEEE-488.
