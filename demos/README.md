# Demos — prompts to try with your AI agent

Each file in this directory is a ready-to-paste prompt for an AI coding agent
set up with this toolset (see the README's "Using with AI coding agents").
Paste one into your agent and watch it write, run, and debug real Commodore
PET software on the emulated machine.

They're graded — start at 01 if you're new:

| # | Demo | Language | Shows off | Status |
|---|------|----------|-----------|--------|
| 01 | Guess the number | BASIC | The write→run→verify loop | ✅ passed |
| 02 | Bouncing ball | BASIC | Screen-memory animation | ✅ passed |
| 03 | Sieve benchmark | BASIC + asm | Timing, iteration, a ~93× asm speedup | ✅ passed |
| 04 | Snake | 6502 assembly | The full assembler + debugger workflow | not yet |
| 05 | Debug hunt | BASIC + debugger | Breakpoints, stepping, memory inspection | not yet |

Dogfooding status: each prompt is validated by handing it to a real AI agent
(given only this toolset) and confirming the result independently. Demos 01–03
have passed on the first agent attempt; each file carries its dogfood date.
Prompts not yet validated are marked *(not yet dogfooded)*.

Reference example programs with expected output (runnable as regression tests
via `pet test programs`) live in `tests/programs/` — solutions that come out
of these demos particularly well can graduate there.
