# Ms. Muncher — fidelity audit log

Verdicts come from the running game (screenshots, YAML runs, measurements),
never from reading source. Reference material:
`docs/superpowers/specs/assets/ms-muncher/` (arcade screenshots).

## T3 visual comparison #1 — maze 1 vs arcade (sw-maze1.jpg)

Evidence: `evidence/maze1-line.png` (final), test suite step 8-13.

| Feature | Verdict | Notes |
|---|---|---|
| 28-wide maze, full 25 rows, HUD right | PASS | |
| Two tunnel pairs (rows 6/14 ≈ arcade 8/17) | PASS | mouths open through border |
| Ghost house centred, door lintel | PASS | hollow box + `──` door |
| 4 corner energizers, cols 1/26 | PASS | flashing comes with T7 |
| Dot field density | PASS | 178 dots (checker-verified) |
| Rounded wall corners like the arcade | PASS | quarter-arc glyphs |
| Wall slabs | PASS w/ divergence | arcade fills slabs with colour; mono PET draws hollow perimeter outlines. First render was a rejected "waffle grid" (adjacency mask without the perimeter rule) — fixed same task. |
| Block-for-block layout match | DIVERGENCE (accepted) | 31→25-row adaptation per spec §5: junction topology and signature features preserved, straight runs shortened; mid-maze slabs read larger than arcade's. Revisit in T14 if it bothers. |

Iteration count note: maze renderer needed 2 visual iterations within T3
(waffle grid → perimeter outlines) before the verdict above.

## T7 — frightened / eyes / collision / death / elroy

Evidence: yaml F1–F8 (all green), `evidence/death-spin.png` (mid-spin frame:
she rotates through the four mouth glyphs and sinks — no fold-open collapse,
per the arcade Ms. difference).

| Feature | Verdict | Notes |
|---|---|---|
| Energizer: reversal + blue state + schedule pause | PASS | F1 |
| Blue times from the measured per-board table | PASS | F1 (360j board 1), F3 (board 17 reversal-only) |
| Fright end restores glyph/state | PASS | F2 |
| Ghost eaten → eyes + chain + gulp freeze | PASS | F4 |
| Eyes navigate home and re-emerge | PASS | F5 — needed region waypoints (see bug 2) |
| Death → swoon → respawn, global house counters armed | PASS | F6 |
| Elroy stages at scaled thresholds (+5%/+10%) | PASS | F7 |
| Swap-past collision (no pass-through bug) | PASS | F8 |

Two real AI bugs found by the runtime tests and fixed within T7:
1. **Ghost shuttle:** direction decisions re-ran every jiffy while parked on
   a centre, letting a ghost re-pick the direction it came from (its
   "reverse" rotates after the first re-decision). Fixed with a per-tile
   decision latch, invalidated by reversal events — matching the arcade's
   decide-once-per-tile behaviour.
2. **Eyes trap:** greedy distance-to-door navigation oscillated in the
   pocket below the ghost house (our 25-row adaptation has no upward exit
   near the door column there). Fixed with region waypoints: below → ring-top
   corner, ring top → door mouth, door column → interior.

## T11 visual comparison #2 — mazes 2-4 vs arcade (sw-maze2..4.jpg)

Evidence: `evidence/maze2-solid.png`, `maze3-checker.png`, `maze4-sharp.png`;
checker output (190/186/186 dots vs targets 188/186/182 ±8); progression
yaml block (rotation, styles, 14+ recolor swap all asserted).

| Feature | Verdict | Notes |
|---|---|---|
| Maze 2: tunnel pairs at very top + lower (arcade rows 1/23 → ours 1/19) | PASS | |
| Maze 3: single tunnel pair above centre (arcade 9 → ours 7) | PASS | |
| Maze 4: two tunnel pairs flanking the house (arcade 13/16 → ours 10/13) | PASS | |
| Distinct per-maze "colors" | PASS | line-arc / solid / checkerboard / sharp-line; solid style reads like the arcade's filled walls |
| 14+ recolor: shapes 3/4 swap styles | PASS | yaml-asserted |
| Block-for-block match | DIVERGENCE (accepted) | 25-row adaptations preserve tunnel topology, house, energizer corners; interior block layouts are original approximations |
| Fruit paths on all four mazes | PASS | host-validated cell-by-cell |

Known cosmetics for T14: maze 4's sharp corners show small gaps at a few
junctions; HUD lacks the current-board fruit icon and eaten-fruit history
stack (spec §3) — carried as open items.
