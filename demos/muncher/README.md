# Ms. Muncher (work in progress)

An arcade-faithful maze-chase homage for the Commodore PET 4032 — original
name, cast (Ms. Muncher, Mr. Muncher, Munchkin; ghosts Bruiser, Pixie, Ivy,
Sable), PETSCII art, and original music. Pure 6502 assembly, 40×25 character
mode, one CB2 voice.

Built and tested with the `pet` CLI:

```sh
pet session start --model pet4032 --warp --headless
pet run demos/muncher/muncher.s
pet test run demos/muncher/muncher-test.yaml
```

Status: under construction — see `AUDIT.md` for the fidelity log and
`docs/superpowers/plans/2026-07-18-ms-muncher.md` for the plan.
