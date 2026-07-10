# Cookbook — tested recipes to copy and adapt

Every program here is complete, runs on a PET 4032, and is exercised by
`tests/test_docs_cookbook.py` (the assembly ones are built with real ca65;
the flagship ones run live on the emulator). Copy a recipe, rename things,
and build from there — they encode the conventions that trip people up
(lowercase BASIC, screen codes for pokes, jiffy pacing, the SYS stub).

## BASIC recipes

### Game loop: non-blocking key read + jiffy pacing

`GET` returns immediately (empty string when no key), and the jiffy clock
`TI` ticks 60×/second — together they make a fixed-rate game loop. This one
prints a dot per frame at ~10 frames/second and quits on `Q`:

```basic
100 print "press q to quit"
110 t=ti
120 get k$
130 if k$="q" then print "bye" : end
140 rem --- update and draw the frame here ---
150 print ".";
160 if ti-t<6 goto 160
170 goto 110
```

Line 160 is the pacer: wait until 6 jiffies (1/10 s) have passed since the
frame started. Lower the 6 for a faster game.

### Poke characters at a screen position

Screen RAM starts at 32768 ($8000); the cell at row R (0–24), column C
(0–39) is `32768 + 40*R + C`. POKE **screen codes**, not PETSCII or CHR$
values (42 below is the screen code for `*`; letters are 1–26):

```basic
100 rem three stars on row 5, from column 10
110 for i=0 to 2
120 poke 32768 + 40*5 + 10 + i, 42
130 next i
140 print : print "done"
```

### Sound: a beep subroutine

Three pokes start a tone, two stop it (see the hardware reference for how
this works). Keep the subroutine and call it wherever a game needs a beep:

```basic
100 gosub 900
110 print "beeped" : end
900 rem --- beep for a quarter second ---
910 poke 59467,16 : poke 59466,15 : poke 59464,150
920 t=ti
930 if ti-t<15 goto 930
940 poke 59464,0 : poke 59467,0
950 return
```

Vary 59464 (the pitch: lower = higher note) and the 15-jiffy duration.

## Assembly recipes

### Game loop: poll GETIN, move a ball, pace with the jiffy clock

The complete shape of an action game: clear the screen, then loop —
read the keyboard without blocking (`GETIN` returns 0 in A when no key),
update, draw to screen RAM, and pace by watching the jiffy clock's low
byte. `Q` quits cleanly back to BASIC. A ball sweeps along row 12:

```asm
; ball.s — a moving ball paced at ~10 steps/second; Q quits.
CHROUT = $FFD2
GETIN  = $FFE4
JIFFLO = $8F                    ; low byte of the jiffy clock (60 Hz)
ROW12  = $8000 + 40*12          ; screen RAM, row 12

        .segment "LOADADDR"
        .word   $0401
        .segment "EXEHDR"
        .word   nextln
        .word   10
        .byte   $9E, "1037", $00
nextln: .word   $0000

        .segment "CODE"
start:  lda     #$93
        jsr     CHROUT          ; clear the screen
main:   jsr     GETIN           ; key in A, or 0 if none
        cmp     #'Q'
        beq     done
        ldx     pos             ; erase the ball...
        lda     #$20            ; screen code for space
        sta     ROW12,x
        inx                     ; ...move right, wrapping at column 40...
        cpx     #40
        bne     nowrap
        ldx     #0
nowrap: stx     pos
        lda     #$2A            ; ...and redraw (screen code for *)
        sta     ROW12,x
        ldy     #6              ; pace: wait 6 jiffies (1/10 s)
pace:   lda     JIFFLO
w1:     cmp     JIFFLO
        beq     w1              ; spin until the clock ticks once
        dey
        bne     pace
        jmp     main
done:   rts                     ; back to BASIC (READY.)

pos:    .byte   0
```

To steer instead of auto-move, compare A against `#'A'`/`#'D'` after GETIN
and adjust `pos` accordingly; for keys *held down* (no repeat delay), read
the key-down location `$97` instead — see the hardware reference.

### Sound: a beep from machine code

Same three VIA registers as the BASIC version, timed by the jiffy clock:

```asm
; beep.s — quarter-second beep, then OK.
CHROUT = $FFD2
JIFFLO = $8F

        .segment "LOADADDR"
        .word   $0401
        .segment "EXEHDR"
        .word   nextln
        .word   10
        .byte   $9E, "1037", $00
nextln: .word   $0000

        .segment "CODE"
start:  lda     #$10
        sta     $E84B           ; shift register free-runs under timer 2
        lda     #$0F
        sta     $E84A           ; square-wave bit pattern
        lda     #150
        sta     $E848           ; pitch
        ldy     #15             ; ~1/4 second
bpace:  lda     JIFFLO
bw:     cmp     JIFFLO
        beq     bw
        dey
        bne     bpace
        lda     #0
        sta     $E848           ; silence...
        sta     $E84B           ; ...and release CB2
        lda     #'O'
        jsr     CHROUT
        lda     #'K'
        jsr     CHROUT
        rts
```

## Verifying a recipe-based program

Run it and assert on the screen, exactly like the tests here do:

```
pet run mygame.s
pet wait --text "expected output"
pet screen
```

or wrap it in a YAML test (`pet test run` — format in docs/cli.md).
