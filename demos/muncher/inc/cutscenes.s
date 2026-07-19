; cutscenes.s — the three story acts (spec §15), staged on the gameplay
; engine: dots[] is blanked so the whole screen is corridor, actors are
; scripted directly (no AI, no collisions), and each act has its own
; original tune. game_state 7. SPACE skips.
;
; Act timing uses act_t, which advances every SECOND jiffy (range ~8 s
; per 256 counts); actor motion still runs at full engine speed.

        .segment "CODE"

; ---- act_enter: A = act 1-3. act_from: 0 = title keys, 1 = board flow ----
act_enter:
        sta     act_no
        jsr     snd_off
        lda     #FX_NONE
        sta     snd_cur
        lda     #0
        sta     gon
        sta     act_t
        sta     act_ph
        sta     act_h
        jsr     clrscr
        ; blank collision map: everything is open floor
        lda     #<dots
        sta     PTR
        lda     #>dots
        sta     PTR+1
        ldx     #3              ; 3 pages minus change covers 700 bytes
        lda     #0
        tay
ae1:    sta     (PTR),y
        iny
        bne     ae1
        inc     PTR+1
        dex
        bne     ae1
        jsr     marquee         ; a static frame of the marquee border
        jsr     init_actors
        ldy     act_no          ; title card
        lda     actstr-1,y
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        lda     #<(SCREEN+2*40+12)
        sta     PTR
        lda     #>(SCREEN+2*40+12)
        sta     PTR+1
        jsr     puts
        lda     act_no          ; the act's original tune
        clc
        adc     #FX_ACT1-1
        jsr     snd_play
        ldy     act_no          ; per-act cast placement
        cpy     #2
        beq     a2_set
        bcs     a3_set
; --- Act 1 setup: they enter from both sides, each with a shadow ---
a1_set: ldx     #0              ; her: from the right, chased by Pixie
        lda     #54
        jsr     acast
        lda     #24
        sta     ay
        ldx     #2
        lda     #G_PIXIE
        sta     aglyph+2
        lda     #1
        sta     arev+2
        lda     #64
        jsr     acast
        lda     #24
        sta     ay+2
        ldx     #6              ; him: from the left, chased by Ivy
        lda     #2
        jsr     acast_r
        lda     #28
        sta     ay+6
        ldx     #3
        lda     #G_IVY
        sta     aglyph+3
        lda     #1
        sta     arev+3
        lda     #248            ; just off the left edge (signed-ish start)
        sta     ax+3
        lda     #28
        sta     ay+3
        lda     #DIR_RIGHT
        sta     adir+3
        lda     #$48
        sta     aspd+3
        jmp     ae_go
; --- Act 2 setup: first chase pass ---
a2_set: jsr     a2_pass1
        jmp     ae_go
; --- Act 3 setup: proud parents + the stork ---
a3_set: ldx     #0
        lda     #16
        sta     ax
        lda     #42
        sta     ay
        lda     #G_BALL
        sta     aglyph
        jsr     draw_blob
        ldx     #6
        lda     #20
        sta     ax+6
        lda     #42
        sta     ay+6
        lda     #G_BALL
        sta     aglyph+6
        jsr     draw_blob
        ldx     #6              ; re-cast 6 as the stork up top
        lda     #0
        sta     ax+6
        lda     #8
        sta     ay+6
        lda     #22             ; 'V' wings
        sta     aglyph+6
        lda     #DIR_RIGHT
        sta     adir+6
        lda     #$40
        sta     aspd+6
        ldx     #5              ; the bundle rides under the beak
        lda     #0
        sta     ax+5
        lda     #8
        sta     ay+5
        lda     #G_BALL
        sta     aglyph+5
        lda     #DIR_NONE
        sta     adir+5
ae_go:  lda     #7
        sta     game_state
        jmp     jsync

; acast: X = actor: place at column A (half-cells) heading LEFT at $50
acast:  sta     ax,x
        lda     #G_BALL
        sta     aglyph,x
        lda     #DIR_LEFT
        sta     adir,x
        lda     #$50
        sta     aspd,x
        lda     #0
        sta     aacc,x
        sta     apause,x
        sta     ahid,x
        rts
; acast_r: same but heading RIGHT
acast_r:
        jsr     acast
        lda     #DIR_RIGHT
        sta     adir,x
        rts

; ---- act_tick ----
act_tick:
        lda     keybuf
        cmp     #K_SP
        bne     ak1
        jmp     act_end         ; skip
ak1:    lda     tickcnt         ; act_t advances every second jiffy
        and     #1
        bne     ak2
        inc     act_t
ak2:    lda     act_no
        cmp     #2
        bne     :+
        jmp     ak_a2
:       bcc     :+
        jmp     ak_a3
:
; --- Act 1 script ---
        ldx     #0
        jsr     step_actor
        ldx     #6
        jsr     step_actor
        lda     act_ph
        cmp     #2
        bcs     ak1_3           ; ghosts gone
        ldx     #2
        jsr     step_actor
        ldx     #3
        jsr     step_actor
ak1_3:  lda     act_ph
        bne     ak1_5
        lda     act_t           ; the near-miss: both dart upward
        cmp     #38
        bcs     :+
        jmp     ak_out
:
        lda     #DIR_UP
        sta     adir
        sta     adir+6
        inc     act_ph
        rts
ak1_5:  cmp     #1
        bne     ak1_7
        lda     act_t           ; the shadows collide and vanish
        cmp     #55
        bcs     :+
        jmp     ak_out
:
        ldx     #2
        jsr     erase_blob
        ldx     #3
        jsr     erase_blob
        inc     act_ph
        rts
ak1_7:  cmp     #2
        bne     ak1_9
        lda     act_t           ; they stop at the top... and: a heart
        cmp     #50
        bcs     :+
        jmp     ak_out
:
        lda     #0
        sta     aspd
        sta     aspd+6
        lda     ax              ; heart above the midpoint
        clc
        adc     ax+6
        ror                     ; /2 keeping the carry out
        lsr
        tay
        lda     ay
        lsr
        tax
        dex
        lda     rowscr_lo,x
        sta     PTR
        lda     rowscr_hi,x
        sta     PTR+1
        lda     #G_HEART
        sta     (PTR),y
        inc     act_ph
        rts
ak1_9:  lda     act_t
        cmp     #120
        bcs     :+
        jmp     ak_out
:       jmp     act_end
; --- Act 2 script: five passes, the last two at double speed ---
ak_a2:  ldx     #0
        jsr     step_actor
        ldx     #6
        jsr     step_actor
        lda     act_ph
        tay
        lda     act_t
        cmp     a2times,y
        bcs     :+
        jmp     ak_out
:       inc     act_ph
        cpy     #0
        bne     ak2_1
        jsr     a2_pass2
        rts
ak2_1:  cpy     #1
        bne     ak2_2
        jsr     a2_pass3
        rts
ak2_2:  cpy     #2
        bne     ak2_3
        lda     #0              ; the breather: both freeze mid-screen
        sta     aspd
        sta     aspd+6
        rts
ak2_3:  cpy     #3
        bne     ak2_4
        jsr     a2_pass4
        rts
ak2_4:  cpy     #4
        bne     ak2_5
        jsr     a2_pass5
        rts
ak2_5:  jmp     act_end
; --- Act 3 script ---
ak_a3:  ldx     #6
        jsr     step_actor      ; the stork flaps on regardless
        lda     act_ph
        bne     ak3_2
        ; bundle rides two half-cells behind the beak
        ldx     #5
        jsr     erase_blob
        lda     ax+6
        sec
        sbc     #2
        bmi     ak3_0
        sta     ax+5
        ldx     #5
        jsr     draw_blob
ak3_0:  lda     ax+6            ; over the drop point: let go
        cmp     #28
        bcc     ak_out
        lda     #DIR_DOWN
        sta     adir+5
        lda     #$30
        sta     aspd+5
        inc     act_ph
        rts
ak3_2:  cmp     #1
        bne     ak3_4
        ldx     #5
        jsr     step_actor      ; the bundle falls
        lda     ay+5
        cmp     #42             ; touchdown by the parents
        bcc     ak_out
        lda     #0
        sta     aspd+5
        lda     #G_RING         ; the bundle pops open: little Munchkin
        sta     aglyph+5
        ldx     #5
        jsr     erase_blob
        jsr     draw_blob
        lda     #G_HEART        ; the family moment
        sta     SCREEN+19*40+9
        inc     act_ph
        lda     act_t
        clc
        adc     #40
        sta     act_h           ; end a beat later
        rts
ak3_4:  lda     act_t
        cmp     act_h
        bcc     ak_out
        jmp     act_end
ak_out: rts

; a2 passes: (her x, him x, row, dir, speed)
a2_pass1:
        ldx     #0
        lda     #2
        jsr     acast_r
        lda     #20
        sta     ay
        ldx     #6
        lda     #10
        jsr     acast_r
        lda     #20
        sta     ay+6
        rts
a2_pass2:
        ldx     #0
        lda     #52
        jsr     acast
        lda     #28
        sta     ay
        ldx     #6
        lda     #44
        jsr     acast
        lda     #28
        sta     ay+6
        rts
a2_pass3:
        jsr     a2_pass1
        lda     #32
        sta     ay
        sta     ay+6
        rts
a2_pass4:
        jsr     a2_pass2
        lda     #24
        sta     ay
        sta     ay+6
        lda     #$A0            ; double time
        sta     aspd
        sta     aspd+6
        rts
a2_pass5:
        jsr     a2_pass1
        lda     #$A0
        sta     aspd
        sta     aspd+6
        rts

; ---- act_end: back to the title, or on with the game ----
act_end:
        lda     act_from
        bne     ae_game
        jmp     title_enter
ae_game:jsr     bc_setup        ; next board begins
        lda     #0
        sta     game_state
        rts

        .segment "RODATA"
s_act1: .byte 1,3,20,32,49,32,32,20,8,5,25,32,13,5,5,20,0     ; ACT 1  THEY MEET
s_act2: .byte 1,3,20,32,50,32,32,20,8,5,32,3,8,1,19,5,0       ; ACT 2  THE CHASE
s_act3: .byte 1,3,20,32,51,32,32,10,21,14,9,15,18,0           ; ACT 3  JUNIOR
S_ACT1 = 10
S_ACT2 = 11
S_ACT3 = 12
actstr: .byte S_ACT1, S_ACT2, S_ACT3
a2times:.byte 62, 124, 186, 200, 234, 255

        .segment "BSS"
act_no: .res 1
act_ph: .res 1
act_t:  .res 1
act_h:  .res 1
act_from:.res 1
