# Demos — prompts to try with your AI agent

Each file in this directory is a ready-to-paste prompt for an AI coding agent
set up with this toolset (see the README's "Using with AI coding agents").
Paste one into your agent and watch it write, run, and debug real Commodore
PET software on the emulated machine.

They're graded — start at 01 if you're new:

| # | Demo | Language | Shows off |
|---|------|----------|-----------|
| 01 | Guess the number | BASIC | The write→run→verify loop |
| 02 | Bouncing ball | BASIC | Screen-memory animation |
| 03 | Sieve benchmark | BASIC | Timing, iteration on a real algorithm |
| 04 | Snake | 6502 assembly | The full assembler + debugger workflow |
| 05 | Debug hunt | BASIC + debugger | Breakpoints, stepping, memory inspection |

Dogfooding status: these prompts are validated against a real agent before a
release; a prompt that hasn't been through a successful run yet is marked
*(not yet dogfooded)* in its file; validated ones carry their dogfood date.

Reference example programs with expected output (runnable as regression tests
via `pet test programs`) live in `tests/programs/` — solutions that come out
of these demos particularly well can graduate there.
