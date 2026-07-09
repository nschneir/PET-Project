# PET Project demo prompt library

Each demo directory contains:

- `prompt.md` — a self-contained one-shot prompt an AI could be given
- a reference solution: `program.bas` (Commodore BASIC, petcat conventions:
  keywords and string text lowercase) or `program.s` (ca65 assembly)
- `expect.txt` — screen text that must appear after the program runs
  (one required substring per non-empty line)

The integration test suite builds and runs every reference solution on an
emulated PET and asserts the expectations, so these demos are end-to-end
tests of the whole toolchain. The prompts double as one-shot AI evaluation
tasks (harness planned for the skills phase).
