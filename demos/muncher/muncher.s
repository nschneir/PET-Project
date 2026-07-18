; muncher.s — Ms. Muncher for the Commodore PET 4032 (40x25, 32K).
; An arcade-faithful maze-chase homage: original name, cast, art, and music.
; Pure 6502 with a BASIC SYS stub. Screen at $8000, jiffy-paced (60 Hz),
; 56x50 half-cell actor engine, CB2 sound. See AUDIT.md for the fidelity log.
; Spec: docs/superpowers/specs/2026-07-18-ms-muncher-design.md

        .include "inc/zp.inc"

; --------------------------------------------------------------------------
        .segment "LOADADDR"
        .word   $0401
        .segment "EXEHDR"
        .word   nextln
        .word   10
        .byte   $9E, "1037", $00
nextln: .word   $0000

        .segment "CODE"
start:  cld
        jsr     clrscr
        jsr     banner
        lda     #0
        sta     tickcnt
        sta     tickcnt+1
        sta     overruns

; ---------------------------- main loop -----------------------------------
; ONE game tick per jiffy. `tick` is the frame-step anchor: the runner's
; poke-$97-then-until protocol stops here, so KEYDOWN is read first, before
; the next IRQ rewrites it (the invaders lesson).
loop:   jsr     pace
        inc     tickcnt
        bne     tick
        inc     tickcnt+1
tick:   lda     KEYDOWN
        cmp     #$FF
        beq     :+              ; no key: keep last echo (sticky for tests)
        sta     SCREEN+39       ; debug echo cell @0,39 — raw byte on purpose
:       jmp     loop

pace:   lda     JIFFLO
pw:     cmp     JIFFLO
        beq     pw              ; wait for the jiffy clock to advance
        rts

; clrscr: fill all 1000 screen cells with spaces
clrscr: lda     #32
        ldx     #0
:       sta     SCREEN,x
        sta     SCREEN+250,x
        sta     SCREEN+500,x
        sta     SCREEN+750,x
        inx
        cpx     #250
        bne     :-
        rts

; banner: write MS. MUNCHER at row 0 col 0 (screen codes: A-Z = 1-26)
banner: ldx     #0
:       lda     bantxt,x
        beq     :+
        sta     SCREEN,x
        inx
        bne     :-
:       rts

        .segment "RODATA"
bantxt: .byte   13,19,46,32,13,21,14,3,8,5,18,0   ; "MS. MUNCHER"

        .segment "BSS"
tickcnt: .res 2                 ; jiffies since start (test/measure anchor)
overruns:.res 1                 ; frames whose work exceeded one jiffy
