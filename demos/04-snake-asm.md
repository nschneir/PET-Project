# Snake in 6502 assembly *(not yet dogfooded)*

Paste this prompt into your agent:

> Using the pet CLI (see skills/pet-development/SKILL.md, the 6502-assembly
> skill, and docs/cli.md), build a Snake game for a PET 4032 in 6502
> assembly: the snake moves continuously on the 40×25 screen (screen memory
> at $8000), W/A/S/D steer it, it grows when it eats a `*` placed at random
> positions, and the game ends with `GAME OVER — SCORE n` if it hits the
> border or itself. Read the keyboard with the GETIN ROM routine. Use the
> debugger (breakpoints, `pet step`, memory inspection) when something
> misbehaves rather than guessing. Prove it works by playing a few moves
> with keyboard input and showing me screens of the snake moving, eating,
> and the game-over.

**What success looks like:** an assembled program with a BASIC SYS stub, a
main loop with a speed delay, GETIN-based steering, and screenshots/screen
text showing movement, growth, and the game-over message. This is the
flagship demo — expect the agent to lean on the debugger to get there.
