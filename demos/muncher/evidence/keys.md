# T1 discovery evidence — glyphs and keys (PET 4032)

## Glyphs

Method: poked screen codes 64–127 into screen RAM as a spaced grid with
digit rulers (`evidence/charset-zoom2.png`), read at 4× upscale. The
`pet screen` text decoder collapses graphics to `·`, so identification was
visual, from the PNG.

Identified and recorded in `inc/zp.inc`: ball 81, ring 87, heart 83,
diamond 90, club 88, spade 65, quarter-arcs ╭╮╰╯ = 85/73/74/75, lines
─ 64 / │ 93, sharp corners ┌┐└┘ = 112/110/109/122, tees ├┤┬┴ =
107/115/114/113, cross 91, checkerboard 102, solid 160 (reverse space),
quadrants ▗ 108 / ▖ 123 (from the invaders demo, same charset).

**Half-block fusion test** (`/tmp` pair grid, verdict from screenshot):
candidates rendered as [right-half-in-left-cell][left-half-in-right-cell]
beside a solid-block reference.

| Pair | Verdict |
|---|---|
| 225 + 97 (horizontal) | fuses into one centred square — **chosen** |
| 106 + 116, 103 + 101, 225 + 117 | thin bars / uneven — rejected |
| 98 over 226 (vertical) | fuses into one centred square — **chosen** |
| 121 over 119, 111 over 100 | thin dashes — rejected |

So the blob renderer uses: straddle-right = 225 then 97; straddle-down =
98 over 226. The reverse-video complements (97↔225, 98↔226) are exact,
which also gives free reverse-video blobs for frightened ghosts.

## Keys

The 4032 (BASIC 4 editor ROM) stores the *decoded PETSCII* of the held key
at $97 ($E556 `sta $97` from the decode table at $E73E) — established on
the machine during the invaders demo (see demos/invaders/AUDIT.md,
iteration 3). `pet key hold` targets the same contract. Values recorded:
W=$57 A=$41 S=$53 D=$44 SPACE=$20 1=$31 2=$32 3=$33.

Known constraint: single-key rollover (ROM exposes one held key). Four-way
steering needs only one key at a time, so this is acceptable; noted for
the playability audit.

Deliberate deviation from the plan: the "poke G_BALL, read it back" YAML
step was dropped — it would only test `pet mem write`, not the program.
The fusion screenshot is the real verification.
