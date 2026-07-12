# Invaders (PET 4032) — Fidelity Audit Log

Demo 06 dogfood. Game: `invaders.s` (3295-byte .prg incl. BASIC stub).
All evidence gathered from the RUNNING game on VICE xpet (pet4032, warp,
headless) via the `pet` CLI — frame-stepped with `pet until tick`, driven by
poking $97 (held keys) and `pet key type` (title), never inferred from source.

## Iteration 1 — evaluate

| Spec bullet | Verdict | Evidence (from the running machine) |
|---|---|---|
| Formation 5×11, three classes (30/20/20/10/10 per row) | **PASS** | Rack drawn rows 2-6, 11 columns pitch 2 (alienX dump 9..29); classes: top ○/● (87/81), rows 2-3 ♠/♣ (65/88), rows 4-5 ╳/♦ (86/90) — `march-frameA/B.png`; PTS table 3/2/2/1/1 units → 11·30+22·20+22·10 = **990/wave**; kill of bottom-row alien paid 10 (score 0→1 unit, HUD `SCORE 00010`) |
| Two-shape animation as it marches | **PASS** | sweepF toggles per sweep (0→1 over one 56-tick sweep, watched stopped); `march-frameA.png` vs `march-frameB.png` one sweep apart show flipped glyphs, including the mid-sweep ripple (moved aliens wear the new frame, unmoved the old — the arcade artifact) |
| One-invader-per-tick march engine, sweep order | **PASS** | 56 ticks stepped: every alienX advanced exactly 1; mcur returned to its start; 1 wrap tick per sweep. Sweep order is index order (top-left→bottom-right; arcade went bottom-up — same rhythm, noted as a variance, not player-visible) |
| Edge → drop one row & reverse | **PASS** | Free-run: alienY all +1 after edge contact, mdx 1→255; over minutes the rack descended 2→19 by repeated bounces |
| Speed-up **emergent**, never scripted | **PASS** | Same engine, no speed table anywhere: 20 stepped ticks moved alien0 **0 steps with 55 alive** vs **10 steps solo** (sweep shrinks from 56 ticks to 2). Final invader crosses the screen in ~1.3 s — visibly frantic |
| Player: laser base, 3 lives, extra at 1500, one shot | **PASS** | 3 lives at newgame (`LIVES 3` + spare icons); second fire ignored while shotA=1 (fire path exits); score 1490→1500 paid exactly one extra base (lives 3→4, extraF latched, `LIVES 4`) |
| Bombs: ≤3, three flavours, from lowest live in column | **PASS** | 3 slots only (4th drop attempt requeues, `bombTmr=8`); flavours cycle 0,1,2 — all three photographed in flight (`bombs3.png`: `!` at pace 4, thin bar at 2, ╲/╱ wiggler at 3 with sideways drift); fresh bomb spawned at (15,7) = the LOWEST live alien of column x=15 (column aliens y=3..7) |
| Bomb & player shot cancel | **PASS** | Shot into a falling bomb's cell: shotA=0, bombA=0, `*` flash at the meeting cell (verified both directions: shot-into-bomb and bomb-into-shot paths exist; shot-into-bomb exercised live) |
| Shields: 4 bunkers, erode from BOTH sides, damage states | **PASS** | 4 bunkers 4×2 at cols 5/14/23/32, rows 19-20, built solid ($A0). Bomb fire from above: cells $A0→$66→$20 observed in RAM; player shot from below: cell (6,20) $A0→$66, shot spent. Marching aliens also wipe shield cells they pass through (march erase). `shields-eroding.png` |
| Mystery UFO: periodic, warbling, 50–300 | **PASS** | Spawns every 1500 ticks (~25 s), `<=>` crosses row 1 at 1 col/2 ticks (RAM: 3c 3d 3e gliding); warble = FX_UFO on the idle voice (ACR=$10, alternating 90/110 periods via restart, watched 6 consecutive ticks incl. priority handoff from an invader-crunch) |
| UFO secret: 300 on 23rd shot, then every 15th | **PASS** | shotCnt=23 kill → +300 exactly (HUD 00300, `300` flashed at the kill site); shotCnt=38 → +300; shotCnt=25 → +100 (off-cycle table 50/100/150/100) |
| Waves: 2-9 one step lower, 10 resets | **PASS** | Wave 1 top row 2 → wave 2 top row 3 (formtop=3, HUD `WAVE 02`, screen one line lower); wave 9→10 clear: formtop back to **2** (`WAVE 10` shown) |
| Game ends: lives out or invader reaches baseline | **PASS** | 3rd death → `GAME OVER`; forced drop to row 23 → invaded=1 → `GAME OVER` (invasion path) |
| HUD always visible; hi-score survives the session | **PASS** | Row 0 `SCORE/HI/WAVE` + row 24 `LIVES n` + spare icons live-update; game 1 ended at 1500 → title `HI 01500` → game 2 HUD `SCORE 00000  HI 01500` |
| Title: big name, SCORE ADVANCE TABLE, ? MYSTERY, press-any-key | **PASS** | `title.png`: SPACE INVADERS in 3×5 solid-block letters, `*SCORE ADVANCE TABLE*` with the real glyphs (`<=> = ? MYSTERY`, ○=30, ♠=20, ╳=10), `PRESS ANY KEY TO PLAY`; GETIN starts a game; attract loops game-over→title |
| Sound: CB2 voice, 4-note bass heartbeat locked to march, distinct effects, priorities | **PASS** | Heartbeat fired from the sweep-wrap itself (tempo = sweep rate, so it quickens as the rack thins, structurally); mid-note capture: ACR=$10, SR=$0F rotating (read 30), T2 counting under the written period (189<200), notes cycle 200/215/230/245; distinct shot zap (diving pitch), invader crunch ($55 pattern), UFO warble, player explosion ($6E rumble). Priorities live-verified: explosion pri 4 owned the voice through the death freeze; crunch(3) → warble(1) handoff observed. Voice fully released ($E848=0, $E84B=0) after every effect |
| Jiffy pacing; redraw only changed cells; no hot-path ROM calls | **PASS** | One tick per $8F change (`pace`); march touches exactly 2 cells/move; projectiles erase+draw their own cells; full repaints only at screen setup. ROM calls in play: none (GETIN only on title/game-over, CHROUT only in field setup). Input from $97 key-down state — held A/D verified moving 1 col/3 ticks, space fires |
| Cycle budget of the per-tick invader update | **PASS** | march ≈ **210 cycles** typical (find+erase+step+draw incl. two plotaddr at ~46 ea); worst case +54 dead-skips ≈ 9 cy each ≈ **~700**. Whole tick worst ≈ 2.5 k cycles vs 16.6 k budget (1 MHz / 60 Hz) — >6× headroom, no overruns (pacing loop always reached the next jiffy) |
| Fits comfortably in 32K | **PASS** | 3295-byte .prg loading at $0401; BSS ends < $1200; screen at $8000 untouched by code/data |

### Documented approximations (PET hardware/ROM realities)
- **Character-cell sprites.** No bitmap mode: each invader is one character,
  two-frame animation via glyph pairs; the base is 3 characters. This is the
  nearest PET-charset equivalent of the arcade's bitmapped sprites.
- **Single-key rollover.** The ROM keyboard scanner exposes ONE held key at
  $97 (the spec mandates $97 input). While space is physically held, A/D
  read as released, so firing pauses sliding for the fraction of a second
  the key is down. Matrix-level scanning could fix it but would break the
  spec's own poke-$97 test protocol and its "the IRQ scanner maintains it"
  instruction. Noted as inherent to the prescribed input method.
- **One voice.** Effects duck each other by priority (spec-sanctioned:
  "effects interrupt the heartbeat, the player's own explosion outranks
  everything").
- **March sweep order** is top-left→bottom-right (arcade: bottom-up). Same
  one-per-tick rhythm and emergent speed-up; only the direction of the
  mid-sweep ripple differs.
- **UFO direction** is always left→right (arcade alternates by shot parity).

## Iteration 1 — review findings (all fixed & re-verified)
1. **Stale ordnance pixels after respawn** — clearfx cleared flags but not
   screen cells; a leftover `<=>` could even be shot for ghost points.
   → clearfx now lifts shot/bomb/UFO/popup pixels. *Re-verified:* bombs
   photographed in flight, death forced, cells read back as spaces.
2. **Ghost-UFO payout guard** — smufo now requires ufoA=1; synthetic `<=>`
   debris shot through pays 0 (score unchanged, shot flew on).
3. **Score display overflow past 99,990** — thousands digit would leave the
   digit range; score now clamps at 9999 units. *Re-verified:* 9990 + kill →
   HUD `SCORE 99990`, bytes 15/39.
4. **Cold-start HUD garbage on first title** (`SCORE ;6900 WAVE 10`) —
   score/wave now zeroed before the first titlescreen. *Re-verified:* fresh
   boot title shows `SCORE 00000 … WAVE 01`.
   Also: comment corrections ($97 holds PETSCII, not a matrix index), dead
   `SCREEN` equate removed, bomb grace periods added (120 ticks at wave
   start, 60 after respawn — the arcade doesn't open fire instantly).

## Iteration 2 — evaluate
Re-ran the regression sweep post-fixes: title → game → march/animation →
bombs (3 flavours) → shield erosion both sides → death/respawn (clean
field) → UFO + secret → wave advance → wave-10 reset → invasion game over →
attract → second game with surviving HI. All PASS, no new findings.

## Iteration 2 — review
Second full-source read: no dead code, no unbounded loops, all branches in
range (clearfx relocation fixed the range errors), zero-page use confined to
$FB-$FE, BSS state fully initialized (gz block + explicit inits), voice
always released. Nothing left worth fixing. **Audit closed: every bullet
PASS; permanent variances documented above as PET realities.**
