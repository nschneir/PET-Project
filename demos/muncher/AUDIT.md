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
