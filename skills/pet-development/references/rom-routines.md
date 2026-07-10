# PET ROM routine catalog

The kernal jump table is stable across BASIC 2.0/4.0 PETs. These are the
routines pet-tools ships labels for (the same set `pet rom disasm` annotates).
Register conventions below are the standard kernal contracts; **confirm the
exact behavior on your machine with `pet rom disasm NAME`** — the jump table
entries are `JMP` vectors into version-specific ROM.

## Kernal jump table

| Addr | Name   | Contract                                                     |
|------|--------|--------------------------------------------------------------|
| FFC0 | OPEN   | Open a logical file (params set up via SETLFS/SETNAM path).  |
| FFC3 | CLOSE  | Close a logical file (A = logical file number).              |
| FFC6 | CHKIN  | Set an open file as the input channel (X = logical number).  |
| FFC9 | CHKOUT | Set an open file as the output channel (X = logical number). |
| FFCC | CLRCHN | Restore default input/output channels.                       |
| FFCF | CHRIN  | Read one byte from the current input channel into A.         |
| FFD2 | CHROUT | Write the PETSCII byte in A to the current output channel.   |
| FFD5 | LOAD   | Load/verify from a device.                                   |
| FFD8 | SAVE   | Save a memory range to a device.                             |
| FFE1 | STOP   | Test the STOP key (Z set when pressed).                      |
| FFE4 | GETIN  | Get one byte from the keyboard buffer into A (0 if empty).   |
| FFE7 | CLALL  | Close all open files and restore default channels.          |

CHROUT (`jsr $FFD2` with `CHROUT = $FFD2`) is the workhorse for printing from
assembly — see the `6502-assembly` skill. Note CHROUT takes **PETSCII**, not a
screen code (see petscii.md).

## Hardware vectors

| Addr | Name      | Meaning                    |
|------|-----------|----------------------------|
| FFFA | NMI_VEC   | Non-maskable interrupt.    |
| FFFC | RESET_VEC | Power-on / reset entry.    |
| FFFE | IRQ_VEC   | Maskable interrupt (60 Hz jiffy + keyboard scan run from here). |

## BASIC zero-page pointers (cross-reference)

| Addr | Name   | Meaning                          |
|------|--------|----------------------------------|
| 0028 | TXTTAB | Start of BASIC text (= $0401).   |
| 002A | VARTAB | End of program / start of vars.  |

Full zero-page pointer chain: zero-page.md.
