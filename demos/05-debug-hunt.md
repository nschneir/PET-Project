# Debug hunt *(not yet dogfooded)*

Paste this prompt (including the listing) into your agent:

> This Commodore BASIC program is supposed to print the 12-times table from
> `12 X 1 = 12` through `12 X 12 = 144`, but it misbehaves. Using the pet
> CLI on a PET 4032 (see skills/pet-development/SKILL.md and docs/cli.md),
> run it, observe what actually happens, find every bug — use the tooling
> to inspect rather than just eyeballing the listing — fix it, and prove
> the fixed version prints all twelve correct lines.
>
> ```
> 10 for i=0 to 12
> 20 t=12*1
> 30 print "12 x";i;"=";t
> 40 next j
> ```

**What success looks like:** the agent runs the broken program, reads the
actual error/output from the screen (`?NEXT WITHOUT FOR` from the `next j`,
the off-by-one start at 0, and the `12*1` that should be `12*i`), fixes all
three, and shows a screen ending in `12 X 12 = 144`.
