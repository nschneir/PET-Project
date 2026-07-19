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
        sta     mstyle          ; maze 1: line-and-arc walls
        jsr     unpack_maze
        jsr     draw_maze
        jsr     init_actors
        jsr     player_init
        lda     #$B5            ; RNG seed (game start reseeds from the
        sta     rng             ; jiffy clock; tests poke their own)
        lda     #$27
        sta     rng+1
        lda     #1
        sta     board
        lda     #3
        sta     lives
        lda     #0
        sta     game_state
        sta     death_t
        sta     gdmode
        sta     frite_t
        sta     frite_t+1
        sta     elvl
        sta     gameover_ev
        jsr     ghost_init
        jsr     fruit_init
        jsr     hs_seed
        lda     #0
        sta     score
        sta     score+1
        sta     score+2
        sta     hiscore
        sta     hiscore+1
        sta     hiscore+2
        sta     extra_given
        sta     pop_t
        jsr     hud_init
        lda     #0              ; the ghost world sleeps until a game
        sta     gon             ; actually starts (T12 title flow); tests
                                ; and players enable it explicitly
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
        sta     SCREEN+999      ; debug echo cell @24,39 — raw byte on purpose
:       ldy     game_state
        beq     playing
        dey
        beq     dying
        dey
        beq     gover
        dey
        beq     inits
        jsr     boardclr_tick   ; game_state 4
        jmp     loop
playing:jsr     player_input    ; A still holds the key-down byte
        jsr     player_tick
        jsr     ghosts_tick
        jsr     fruit_tick
        jsr     popup_tick
        lda     gon             ; parked pre-game limbo: SPACE starts
        bne     :+
        lda     KEYDOWN
        cmp     #K_SP
        bne     :+
        jsr     newgame
:       jmp     loop
dying:  jsr     death_tick
        jmp     loop
gover:  jsr     gameover_tick
        jmp     loop
inits:  jsr     initials_tick
        jmp     loop

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

; banner: write MS. MUNCHER in the HUD panel, row 0 cols 29-39
banner: ldx     #0
:       lda     bantxt,x
        beq     :+
        sta     SCREEN+29,x
        inx
        bne     :-
:       rts

        .include "inc/mazes.s"
        .include "inc/engine.s"
        .include "inc/player.s"
        .include "inc/ghosts.s"
        .include "inc/fruit.s"
        .include "inc/hud.s"

        .segment "RODATA"
bantxt: .byte   13,19,46,32,13,21,14,3,8,5,18,0   ; "MS. MUNCHER"

        .segment "BSS"
tickcnt: .res 2                 ; jiffies since start (test/measure anchor)
overruns:.res 1                 ; frames whose work exceeded one jiffy
