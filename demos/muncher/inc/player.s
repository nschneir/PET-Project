; player.s — Ms. Muncher: input, steering (with the arcade cornering
; advantage), and dot eating. Actor 0. HOT PATH (runs every jiffy).
;
; Steering rules (spec §4/§8):
;  - keys latch a wanted direction; the latch persists (buffered pre-turn)
;  - a reversal applies immediately, anywhere
;  - a perpendicular turn applies at a cell centre when legal, and grants
;    one free half-step in the new direction — the cornering advantage
;    (arcade Ms. Pac-Man gains ground on every corner; ghosts never do)
; Eating (spec §8): landing on a dotted centre removes the dot and stalls
; her one jiffy (three for an energizer). Those stalls reproduce the
; arcade's "slower while eating dots" speed rows almost exactly:
; 80%->0.889*80~=71, 90%->79, 100%->87.

        .segment "CODE"

; ---- player_init: place Ms. Muncher at the start cells, facing left ----
player_init:
        ldx     #0
        lda     #27             ; straddling cols 13/14 (spec §5)
        sta     ax
        lda     #38             ; row 19
        sta     ay
        lda     #DIR_NONE       ; parked until the READY sequence releases
        sta     adir            ; her (T7); tests poke their own state
        sta     pwant
        lda     #G_BALL
        sta     aglyph
        lda     #0
        sta     aspd
        sta     pchomp
        rts

; ---- player_input: A = key-down byte read at the top of the tick ----
player_input:
        cmp     #K_W
        bne     pi1
        lda     #DIR_UP
        sta     pwant
        rts
pi1:    cmp     #K_A
        bne     pi2
        lda     #DIR_LEFT
        sta     pwant
        rts
pi2:    cmp     #K_S
        bne     pi3
        lda     #DIR_DOWN
        sta     pwant
        rts
pi3:    cmp     #K_D
        bne     pi4
        lda     #DIR_RIGHT
        sta     pwant
pi4:    rts

; ---- player_tick: steer, step, eat. Call once per jiffy with X=0 ----
player_tick:
        ldx     #0
        lda     pwant
        cmp     adir
        beq     pt_step         ; already going that way
        tay
        lda     opptbl,y
        cmp     adir
        bne     pt_turn
        tya                     ; reversal: apply anywhere, instantly
        sta     adir
        jmp     pt_step
pt_turn:lda     pwant
        cmp     #DIR_NONE
        beq     pt_step         ; nothing wanted yet
        lda     adir
        cmp     #DIR_NONE
        bne     pt_turn2
        ldy     pwant           ; parked (game/respawn start): any legal
        jsr     canmove_dir     ; wanted direction gets her moving
        bcs     pt_step
        lda     pwant
        sta     adir
        jmp     pt_step
pt_turn2:
        lda     ax              ; perpendicular turn: only at a centre
        ora     ay
        and     #1
        bne     pt_step
        ldy     pwant
        jsr     canmove_dir
        bcs     pt_step         ; wall that way: stay buffered
        lda     pwant
        sta     adir
        jsr     force_step      ; the cornering advantage: free half-step
pt_step:ldx     #0
        lda     ax              ; remember pre-step position: eating only
        sta     ppx             ; happens on a LANDING, not while parked
        lda     ay              ; on a dotted centre
        sta     ppy
        jsr     step_actor
        lda     ax
        cmp     ppx
        bne     pt_landchk
        lda     ay
        cmp     ppy
        beq     pt_out          ; didn't move this jiffy
pt_landchk:
        ; landed on a centre? then eat and animate the chomp
        lda     ax
        ora     ay
        and     #1
        bne     pt_out
        lda     ay              ; cell = (ax/2, ay/2)
        lsr
        tay
        lda     m28_lo,y
        clc
        adc     #<dots
        sta     PTR
        lda     m28_hi,y
        adc     #>dots
        sta     PTR+1
        lda     ax
        lsr
        tay
        lda     (PTR),y
        cmp     #1
        beq     pt_dot
        cmp     #2
        beq     pt_ener
pt_anim:lda     pchomp          ; chomp: alternate ball / open-mouth glyph
        eor     #1
        sta     pchomp
        bne     pt_mouth
        lda     #G_BALL
        sta     aglyph
        jmp     pt_paint
pt_mouth:
        ldy     adir
        lda     mouthtbl,y
        sta     aglyph
pt_paint:                       ; repaint in place so the chomp shows the
        jsr     blob_addr       ; frame she LANDED, not one step late
        lda     aglyph
        sta     (PTR2),y
pt_out: rts
pt_dot: lda     #0              ; eat: clear the cell, fix the save-under
        sta     (PTR),y
        sta     eat_ev
        inc     eat_ev          ; eat_ev=1: a dot was eaten this jiffy
        lda     #G_SPACE
        sta     asave0
        lda     #1
        sta     apause          ; the arcade per-dot chew stall
        lda     #SC_DOT
        jsr     addscore
        jsr     dec_dots
        jmp     pt_anim
pt_ener:lda     #0
        sta     (PTR),y
        lda     #2
        sta     eat_ev          ; eat_ev=2: energizer (frightened flow)
        lda     #G_SPACE
        sta     asave0
        lda     #3
        sta     apause
        lda     #SC_ENER
        jsr     addscore
        jsr     dec_dots
        jmp     pt_anim

dec_dots:
        lda     dots_left
        bne     dd1
        dec     dots_left+1
dd1:    dec     dots_left
        lda     dots_left
        ora     dots_left+1
        bne     dd2
        lda     #4              ; board cleared: celebrate + next board
        sta     game_state
        lda     #0
        sta     death_t
dd2:    rts

        .segment "RODATA"
opptbl:  .byte  DIR_DOWN, DIR_RIGHT, DIR_UP, DIR_LEFT, DIR_NONE
mouthtbl:.byte  G_HALF_B, G_HALF_R, G_HALF_T, G_HALF_L, G_BALL
         ; mouth opens toward travel: the missing half faces the direction

        .segment "BSS"
pwant:  .res 1                  ; buffered wanted direction
pchomp: .res 1
ppx:    .res 1                  ; pre-step position (landing detector)
ppy:    .res 1
eat_ev: .res 1                  ; 0 none, 1 dot, 2 energizer (consumed by T7+)
