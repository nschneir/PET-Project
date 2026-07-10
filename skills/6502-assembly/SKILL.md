---
name: 6502-assembly
description: Use when writing or debugging 6502 assembly for the Commodore PET with ca65/ld65 via pet build or pet run. Covers the PET program skeleton, the BASIC SYS stub, calling ROM routines, and 6502 gotchas.
---

# 6502 assembly for the PET

Assemble with ca65/ld65 through `pet build FILE.s` (produces a `.prg` plus a
VICE label file) or run in one step with `pet run FILE.s` (assembles, loads,
and RUNs, registering the labels on the session for symbolic debugging). The
machine-level reference for addresses and ROM routines is the `pet-development`
skill's reference files (memory map, ROM routines, zero page, PETSCII).

## The program skeleton

A PET program loads at `$0401` and needs a tiny BASIC stub so that `RUN`
transfers control to your machine code. This skeleton assembles as-is (it is
the project's `hello-asm` demo):

```asm
; print a message via the ROM CHROUT routine, then return to BASIC.
; Layout: 2-byte load address ($0401), then a BASIC stub "10 SYS 1037",
; then code at $040D (= 1037).

CHROUT = $FFD2

        .segment "LOADADDR"
        .word   $0401

        .segment "EXEHDR"
        .word   nextln          ; pointer to next BASIC line
        .word   10              ; line number 10
        .byte   $9E, "1037", $00 ; SYS 1037
nextln: .word   $0000           ; end of BASIC program

        .segment "CODE"
start:  ldx     #0
loop:   lda     msg,x
        beq     done
        jsr     CHROUT
        inx
        bne     loop
done:   rts

msg:    .byte   "HELLO FROM ASM", $0D, $00
```

### Why SYS 1037

The load address `$0401` is emitted by the `LOADADDR` segment (not loaded into
RAM as data — it is the PRG header). Starting at `$0401` the `EXEHDR` segment
lays down a single BASIC line — next-line pointer, line number 10, the `SYS`
token `$9E`, the digits `"1037"`, and a `$00` terminator — followed by the
`$0000` end-of-program marker. That stub occupies 12 bytes (`$0401`–`$040C`),
so your `CODE` segment begins at `$040D`, which is decimal **1037**. Hence
`SYS 1037` jumps to `start`. Change the message and the code, not the stub.

Segments available in the linker config: `CODE`, `RODATA`, `DATA`, `BSS`
(and `ZEROPAGE`). Put executable code and mutable data in `CODE`/`DATA`,
constants in `RODATA`, and uninitialized storage in `BSS`.

## Calling ROM

Define the entry point and `jsr` it. CHROUT (`$FFD2`) prints the PETSCII byte
in `A` to the current output channel; return to BASIC with `rts`. The full
kernal jump table (CHRIN, GETIN, STOP, OPEN/CLOSE, …) and register conventions
are in the `pet-development` skill's ROM-routines reference. CHROUT expects
**PETSCII**, not a screen code — see that skill's PETSCII reference.

## 6502 gotchas

- The NMOS 6502 has **no** `BRA` (unconditional branch) and none of the 65C02
  additions — use `jmp` or a always-true conditional branch.
- Branches (`beq`, `bne`, …) reach only **±127 bytes**; use `jmp` for longer
  jumps.
- Zero page is scarce and shared with BASIC/kernal — see the
  `pet-development` skill's zero-page reference before claiming zero-page
  locations.
- `jsr` pushes the return address **minus one**; `rts` compensates. This
  matters if you manipulate the stack directly.

## Debugging

`pet run FILE.s` registers the labels, so you can `pet break add start`, then
`pet wait --break`, `pet reg`, `pet step`, and `pet mem read` your data by
symbol. Disassemble live memory (with your labels and ROM labels) via
`pet rom disasm start 32`.
