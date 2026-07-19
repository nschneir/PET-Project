# Speed & playability measurements

All values measured in the running machine via the YAML suite (jiffy-exact
`until`-on-`tick` counts), not computed from source. Arcade 100% = speed
increment $50 = 18.75 half-cells/s.

## T5 audit (protocol rows 1–2)

| Measurement | Expected | Measured | Verdict |
|---|---|---|---|
| 50 half-cells @ $50 (100%) across dotted row 3, 24 chew stalls | 184 jiffies | ax=52 at exactly t=184 (yaml a) | PASS |
| 25 half-cells @ $28 (50%) across dotless row | 160 jiffies | ax=27 at exactly t=160 (yaml b) | PASS |
| Eating-speed ratio emerging from 1-jiffy/dot stalls | 71/80 ≈ 0.89 | 160/184 earned-vs-wall = 0.87 over the run (asymptotic 8/9 = 0.889) | PASS |
| Energizer = 3-jiffy stall | +3 jiffies | yaml (c): pin at t=14 = 8 move + 3 + 1 stalls | PASS |
| Tunnel void = 4 hidden half-steps at actor speed | 10 jiffies at $80 | yaml (d): emerge on t=10 | PASS |
| Cornering advantage = one free half-step per corner | 2 jiffies gained at $80 | yaml (f): centre (6,2) at t=14 (a ghost turning at the centre would arrive t=16) | PASS |

## T6 audit (protocol rows 3–4)

| Measurement | Expected | Measured | Verdict |
|---|---|---|---|
| Ghost 75% ($3C): 50 half-cells, no eating | 214 jiffies (50·256/60 rounded up) | yaml (D): ax=51 at t=213, ax=52 at exactly t=214 | PASS |
| Ghost/player speed ratio 75/80 | ghosts measurably slower | 214 vs 160 earned jiffies for the same distance | PASS |
| Tunnel zone 40% ($20) + void at tunnel speed | mouth at t=56, emerge t=88 | yaml (E): ahid=4 at t=56, visible at col 27 on t=88 | PASS |
| Scatter reversal timing | state edge reverses all active ghosts, chase timer 1200 | yaml (B): reversal on expiry, timer 1199 one tick later | PASS |
