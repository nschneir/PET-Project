# PET hardware overview

Base addresses of the I/O chips (all in the `$E800-$EFFF` window). This is an
orientation map, not a register-level reference — for exact bit meanings, poke
with `pet mem read`/`pet mem write` and read the ROM with `pet rom disasm`.

| Base  | Chip  | Role                                                        |
|-------|-------|-------------------------------------------------------------|
| E810  | PIA1  | Keyboard matrix scan (row select out, columns in); screen blank and cassette lines. |
| E820  | PIA2  | IEEE-488 data lines.                                        |
| E840  | VIA   | IEEE-488 control, user port, CB2 sound, timers.            |
| E880  | CRTC  | Video timing — register select `$E880`, data `$E881`. **CRTC models only** (4032/8032/8296). |

Notes:

- The keyboard is scanned from the IRQ handler on the ~60 Hz jiffy interrupt.
  For automation, feed the keyboard through `pet basic type` (or the keyboard-
  feed path) rather than poking the PIA1 matrix directly.
- **IEEE-488** is the PET's peripheral bus — disk drives and printers live here
  as devices 8 and up. pet-tools drives disks through disk images and `pet disk`
  / VICE, so you rarely touch the bus registers directly.
- Sound is a single square wave gated on the VIA's CB2 line — there is no
  dedicated sound chip.
