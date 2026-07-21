---
name: 6502-debugging
description: Use when a PET program misbehaves at runtime — crashes, corruption, wrong values, dead input, visual glitches — and you need a procedure, not a guess. Symptom-indexed playbook of runtime debugging procedures using pet-tools.
---

# 6502 debugging playbook

Procedures that turn a symptom into a verified cause using `pet` commands.
Follow the procedure before forming theories — each one exists because
improvising in its situation reliably wastes time. The companion
references are the `pet-development` skill's diagnosis table (quick
symptom→cause lookups) and the `6502-assembly` skill's gotchas (the bugs
you write, rather than find).

## Rule zero: prove you are debugging the binary you think you are

The most expensive class of debugging failure is the hunt for a "bug"
that does not exist: a rebuild failed silently and every observation is
of the *previous* binary. Before trusting any runtime evidence:

1. `pet status` — read the `program:` line and look for
   `STALE (source changed since load)`. Stale means rebuild and reload
   before doing anything else.
2. If in doubt, spot-check code bytes: `pet mem read <label> 8` and compare
   against the assembler listing. Two minutes here beats hours of
   fiction-driven debugging.
3. A failed `pet run` says loudly that the emulator still runs the previous
   program. Believe it.

## Triage: the first three commands

For any misbehavior, in order: `pet status` (running or stopped? stale?),
`pet screen` (what does the program think is happening?), `pet reg` (where
is PC — in your code, in ROM, or in the weeds?). If PC is in unmapped or
BSS space, the crash already happened; the question becomes "what jumped
here," not "what is wrong here."

## Something is corrupting memory

Symptom: a variable changes that "nothing writes to"; code bytes change;
behavior degrades over time. Do not read code looking for the writer —
trap it:

    pet watch add <addr> --store
    pet wait --break <ID>

The machine halts ON the writing instruction; `pet reg` and the PC symbol
name the culprit. Pass the watchpoint's ID to `--break` so a leftover
breakpoint cannot intercept the wait. One watchpoint routinely finds in
seconds what an hour of code-reading cannot. If the writes are legitimate
but wrong (right routine, wrong index), add a condition:
`pet break add <label> --condition 'X > 4'`.

## A loop goes wrong partway / the wrong actor moves

Symptom of a **register clobber**: a helper called inside the loop
destroys X or Y. Two procedures:

- Audit by isolation: `pet call <helper> --x 3` then `pet reg` — did X
  survive? Repeat for each helper the loop body calls. (In YAML:
  `call: { routine: helper, x: 3 }` then `assert: { reg: x, equals: 3 }`.)
- Audit in place: `pet until <loop-label>`, note X, `pet step --over`
  through the body watching for the register to change across a `jsr`.

Clobber bugs cluster in helpers added to an existing loop late in
development (sound triggers, HUD updates) — audit those first.

## Reproducing a timing-dependent bug deterministically

Wall-clock time is poison under `--warp` (seconds of your time are emulated
minutes). Rebuild the failure state explicitly instead of replaying to it:

1. `pet until <tick-label>` — stop at the frame anchor.
2. `pet mem write --stdin` — poke the exact state (positions, timers,
   flags) that precedes the failure.
3. `pet until <tick-label> --count N` — advance exactly N frames.
4. Inspect. Every run is now identical; bisect N to find the failing frame.

Encode the reproduction as YAML `poke:`/`until:`/`assert:` steps
immediately — the reproduction *is* the regression test.

## Testing one routine without the rest of the program

`pet call <routine>` emulates a JSR in isolation: fake return address on
the stack, optional `--a/--x/--y` on entry, halts at the routine's own RTS
with registers and memory holding its results. Poke inputs first, call,
assert after. Use it to prove a suspect routine innocent (or guilty)
without the game loop muddying the evidence, and as the YAML `call:` step
for permanent routine-level unit tests. A `call` timeout means the routine
never returned from that entry state — itself a finding (runaway loop, or
you called a non-subroutine).

## Waiting for something that might stop happening

`pet until <label>` deadlocks if the program can stop visiting the label
(death, menu, pause). For transitions, set a breakpoint at a path that
MUST execute and `pet wait --break <ID>`; for transient values that polling
would miss at warp, use a store watchpoint instead of `pet wait --mem`.

## Visual glyph bugs

`pet screen` decodes graphics to Unicode look-alikes — good for reading,
ambiguous for identity (several PET codes map to similar glyphs). To
assert exactly which character is in a cell: `pet screen --codes` (raw
code matrix) or `pet mem get '@row,col'`. For pixel truth:
`pet screen --png shot.png --scale 3`.

## Inspection discipline (warp)

End every inspection batch STOPPED (`pet until`, `pet step`, or a fired
`pet wait --break` all leave the machine halted, and it stays halted across
commands). A machine left running between two inspection commands has
played on for emulated minutes; conclusions drawn across that gap compare
two different worlds. Batch reads while stopped; `pet continue` only when
you mean "let time pass."
