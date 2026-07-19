; cutscenes.s — the three story acts (spec §15), staged with MULTI-CHAR
; sprites (2x2 rounded munchers with chomping mouths, 2x2 ghosts, a 2x2
; stork) rather than the single-cell gameplay glyphs — the acts are not
; bound to the maze grid, so they get the bigger, friendlier cast.
; game_state 7. SPACE skips. All art is original PETSCII composition.
;
; act_t advances every second jiffy. Sprites move whole cells at their own
; per-sprite rates (ticks per step).

; sprite kinds
K_MUNCH = 0                     ; 2x2 ball, animated mouth toward travel
K_GHOST = 1                     ; 2x2 hooded ghost
K_STORK = 2                     ; 2x2 bird
K_CHAR  = 3                     ; single character (bundle, Munchkin)

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
        ldx     #3              ; all sprite slots off
ael:    sta     s_on,x
        dex
        bpl     ael
        jsr     clrscr
        jsr     marquee         ; a static frame of the marquee border
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
        ldy     act_no
        cpy     #2
        beq     a2_set
        bcs     a3_set
; --- Act 1: he enters left (Ivy trailing), she right (Pixie trailing) ---
a1_set: ldx     #0              ; him
        jsr     s_defm
        lda     #2
        sta     s_x
        lda     #13
        sta     s_y
        lda     #1
        sta     s_dx
        ldx     #1              ; Ivy behind him
        jsr     s_defg
        lda     #0
        sta     s_x+1
        lda     #13
        sta     s_y+1
        lda     #1
        sta     s_dx+1
        ldx     #2              ; her
        jsr     s_defm
        lda     #35
        sta     s_x+2
        lda     #10
        sta     s_y+2
        lda     #$FF
        sta     s_dx+2
        ldx     #3              ; Pixie behind her
        jsr     s_defg
        lda     #37
        sta     s_x+3
        lda     #10
        sta     s_y+3
        lda     #$FF
        sta     s_dx+3
        jmp     ae_go
; --- Act 2: first chase pass ---
a2_set: jsr     a2_p1
        jmp     ae_go
; --- Act 3: proud parents, stork inbound with the bundle ---
a3_set: ldx     #0              ; him, parked bottom-left
        jsr     s_defm
        lda     #7
        sta     s_x
        lda     #19
        sta     s_y
        jsr     spr_draw
        ldx     #2              ; her beside him
        jsr     s_defm
        lda     #11
        sta     s_x+2
        lda     #19
        sta     s_y+2
        jsr     spr_draw
        ldx     #1              ; the stork
        lda     #1
        sta     s_on+1
        lda     #K_STORK
        sta     s_kind+1
        lda     #0
        sta     s_x+1
        sta     s_dy+1
        sta     s_fr+1
        lda     #4
        sta     s_y+1
        lda     #1
        sta     s_dx+1
        lda     #4
        sta     s_rate+1
        sta     s_cnt+1
        ldx     #3              ; the bundle, slung behind the beak
        lda     #1
        sta     s_on+3
        lda     #K_CHAR
        sta     s_kind+3
        lda     #G_BALL
        sta     s_chr+3
        lda     #0
        sta     s_x+3
        sta     s_dy+3
        sta     s_fr+3
        lda     #6
        sta     s_y+3
        lda     #1
        sta     s_dx+3
        lda     #4
        sta     s_rate+3
        sta     s_cnt+3
ae_go:  lda     #7
        sta     game_state
        jmp     jsync

; s_defm/s_defg: X = slot: define a muncher / ghost, parked, rate 3
s_defm: lda     #1
        sta     s_on,x
        lda     #K_MUNCH
        sta     s_kind,x
        jmp     s_defc
s_defg: lda     #1
        sta     s_on,x
        lda     #K_GHOST
        sta     s_kind,x
s_defc: lda     #0
        sta     s_dx,x
        sta     s_dy,x
        sta     s_fr,x
        lda     #3
        sta     s_rate,x
        sta     s_cnt,x
        rts

; ---- sprite draw / erase / step ----
; spr_addr: PTR = screen row s_y, Y = s_x
spr_addr:
        ldy     s_y,x
        lda     rowscr_lo,y
        sta     PTR
        lda     rowscr_hi,y
        sta     PTR+1
        ldy     s_x,x
        rts

spr_erase:
        lda     s_on,x
        bne     se0
        rts
se0:    jsr     spr_addr
        lda     #G_SPACE
        sta     (PTR),y
        lda     s_kind,x
        cmp     #K_CHAR
        beq     se_done
        lda     #G_SPACE
        iny
        sta     (PTR),y
        lda     PTR
        clc
        adc     #40
        sta     PTR
        bcc     se1
        inc     PTR+1
se1:    lda     #G_SPACE
        sta     (PTR),y
        dey
        sta     (PTR),y
se_done:rts

spr_draw:
        lda     s_on,x
        bne     sd0
        rts
sd0:    jsr     spr_addr
        lda     s_kind,x
        cmp     #K_CHAR
        bne     sd1
        lda     s_chr,x
        sta     (PTR),y
        rts
sd1:    cmp     #K_GHOST
        bne     sd2
        lda     #<spr_ghost
        sta     PTR2
        lda     #>spr_ghost
        sta     PTR2+1
        jmp     sd_2x2
sd2:    cmp     #K_STORK
        bne     sd3
        lda     #<spr_stork
        sta     PTR2
        lda     #>spr_stork
        sta     PTR2+1
        jmp     sd_2x2
sd3:    lda     s_fr,x          ; muncher: closed / open toward travel
        and     #1
        beq     sd_closed
        lda     s_dx,x
        cmp     #1
        beq     sd_or
        lda     #<spr_openl
        sta     PTR2
        lda     #>spr_openl
        sta     PTR2+1
        jmp     sd_2x2
sd_or:  lda     #<spr_openr
        sta     PTR2
        lda     #>spr_openr
        sta     PTR2+1
        jmp     sd_2x2
sd_closed:
        lda     #<spr_ball
        sta     PTR2
        lda     #>spr_ball
        sta     PTR2+1
sd_2x2: ldy     #0
        lda     (PTR2),y
        ldy     s_x,x
        sta     (PTR),y
        ldy     #1
        lda     (PTR2),y
        ldy     s_x,x
        iny
        sta     (PTR),y
        lda     PTR
        clc
        adc     #40
        sta     PTR
        bcc     sd4
        inc     PTR+1
sd4:    ldy     #2
        lda     (PTR2),y
        ldy     s_x,x
        sta     (PTR),y
        ldy     #3
        lda     (PTR2),y
        ldy     s_x,x
        iny
        sta     (PTR),y
        rts

; spr_step: X = slot. Rate-timed one-cell move with chomp animation.
spr_step:
        lda     s_on,x
        bne     ss0
        rts
ss0:    lda     s_dx,x
        ora     s_dy,x
        bne     ss1
        rts                     ; parked
ss1:    dec     s_cnt,x
        beq     ss2
        rts
ss2:    lda     s_rate,x
        sta     s_cnt,x
        jsr     spr_erase
        lda     s_x,x
        clc
        adc     s_dx,x
        sta     s_x,x
        lda     s_y,x
        clc
        adc     s_dy,x
        sta     s_y,x
        inc     s_fr,x
        jmp     spr_draw

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
ak2:    ldx     #0              ; all sprites tick
        jsr     spr_step
        ldx     #1
        jsr     spr_step
        ldx     #2
        jsr     spr_step
        ldx     #3
        jsr     spr_step
        lda     act_no
        cmp     #2
        bne     :+
        jmp     ak_a2
:       bcc     :+
        jmp     ak_a3
:
; --- Act 1 script (event-driven on positions) ---
        lda     act_ph
        bne     ak1_5
        lda     s_x+2           ; her x - his x <= 5: the near-miss
        sec
        sbc     s_x
        cmp     #6
        bcc     :+
        jmp     ak_out
:
        lda     #0              ; both dart upward
        sta     s_dx
        sta     s_dx+2
        lda     #$FF
        sta     s_dy
        sta     s_dy+2
        inc     act_ph
        rts
ak1_5:  cmp     #1
        bne     ak1_7
        lda     s_x+3           ; the shadows crash into each other
        sec
        sbc     s_x+1
        cmp     #3
        bcc     :+
        jmp     ak_out
:
        ldx     #1
        jsr     spr_erase
        lda     #0
        sta     s_on+1
        ldx     #3
        jsr     spr_erase
        lda     #0
        sta     s_on+3
        inc     act_ph
        rts
ak1_7:  cmp     #2
        bne     ak1_9
        lda     s_y             ; each pulls up at the meeting height —
        cmp     #8              ; watched separately so neither overshoots
        bcs     ak17a           ; into the marquee border
        lda     #0
        sta     s_dy
ak17a:  lda     s_y+2
        cmp     #8
        bcs     ak17b
        lda     #0
        sta     s_dy+2
ak17b:  lda     s_dy
        ora     s_dy+2
        beq     :+
        jmp     ak_out
:
        lda     s_x             ; ...and hearts bloom between them
        clc
        adc     s_x+2
        lsr
        tay
        iny
        lda     s_y
        tax
        lda     rowscr_lo,x
        sta     PTR
        lda     rowscr_hi,x
        sta     PTR+1
        lda     #G_HEART
        sta     (PTR),y
        inc     act_ph
        lda     act_t
        clc
        adc     #60
        sta     act_h
        rts
ak1_9:  lda     act_t
        cmp     act_h
        bcs     :+
        jmp     ak_out
:       jmp     act_end
; --- Act 2 script: five passes, the last two double speed ---
ak_a2:  lda     act_ph
        tay
        lda     act_t
        cmp     a2times,y
        bcs     :+
        jmp     ak_out
:       inc     act_ph
        cpy     #0
        bne     ak2_1
        jsr     a2_p2
        rts
ak2_1:  cpy     #1
        bne     ak2_2
        jsr     a2_p3
        rts
ak2_2:  cpy     #2
        bne     ak2_3
        lda     #0              ; the breather
        sta     s_dx
        sta     s_dx+2
        rts
ak2_3:  cpy     #3
        bne     ak2_4
        jsr     a2_p4
        rts
ak2_4:  cpy     #4
        bne     ak2_5
        jsr     a2_p5
        rts
ak2_5:  jmp     act_end
; --- Act 3 script ---
ak_a3:  lda     act_ph
        bne     ak3_2
        lda     s_x+1           ; over the drop point: let go
        cmp     #17
        bcs     :+
        jmp     ak_out
:
        lda     #0
        sta     s_dx+3
        lda     #1
        sta     s_dy+3
        lda     #3
        sta     s_rate+3
        inc     act_ph
        rts
ak3_2:  cmp     #1
        bne     ak3_4
        lda     s_y+3           ; touchdown by the parents
        cmp     #19
        bcs     :+
        jmp     ak_out
:
        lda     #0
        sta     s_dy+3
        lda     #G_RING         ; the bundle pops open: little Munchkin
        sta     s_chr+3
        ldx     #3
        jsr     spr_draw
        lda     #G_HEART        ; the family moment
        sta     SCREEN+18*40+10
        sta     SCREEN+18*40+13
        inc     act_ph
        lda     act_t
        clc
        adc     #50
        sta     act_h
        rts
ak3_4:  lda     act_t
        cmp     act_h
        bcs     :+
        jmp     ak_out
:       jmp     act_end
ak_out: rts

; act 2 pass setups (her and him take turns leading, rows alternate)
a2_p1:  ldx     #0
        jsr     s_defm
        lda     #8
        sta     s_x
        lda     #9
        sta     s_y
        lda     #1
        sta     s_dx
        ldx     #2
        jsr     s_defm
        lda     #1
        sta     s_x+2
        lda     #9
        sta     s_y+2
        lda     #1
        sta     s_dx+2
        rts
a2_p2:  jsr     a2_clr
        ldx     #0
        jsr     s_defm
        lda     #30
        sta     s_x
        lda     #12
        sta     s_y
        lda     #$FF
        sta     s_dx
        ldx     #2
        jsr     s_defm
        lda     #37
        sta     s_x+2
        lda     #12
        sta     s_y+2
        lda     #$FF
        sta     s_dx+2
        rts
a2_p3:  jsr     a2_clr
        jsr     a2_p1
        lda     #14
        sta     s_y
        sta     s_y+2
        rts
a2_p4:  jsr     a2_clr
        jsr     a2_p2
        lda     #2              ; double time
        sta     s_rate
        sta     s_rate+2
        rts
a2_p5:  jsr     a2_clr
        jsr     a2_p1
        lda     #2
        sta     s_rate
        sta     s_rate+2
        rts
a2_clr: ldx     #0
        jsr     spr_erase
        ldx     #2
        jmp     spr_erase

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
a2times:.byte 55, 110, 165, 180, 215, 240
; 2x2 sprite art (original PETSCII composition): a rounded ball from the
; four filled-quadrant corner characters; the mouth is a diagonal wedge
; facing the travel direction; the ghost is a reverse-video arc hood over
; a reverse-checkerboard skirt; the stork is a wing stroke and a head.
spr_ball:  .byte 254, 252, 251, 236
spr_openr: .byte 254, 205, 251, 206
spr_openl: .byte 206, 252, 205, 236
spr_ghost: .byte 85+128, 73+128, 102+128, 102+128
spr_stork: .byte  78,  87,  77,  32

        .segment "BSS"
act_no: .res 1
act_ph: .res 1
act_t:  .res 1
act_h:  .res 1
act_from:.res 1
s_on:   .res 4
s_kind: .res 4
s_x:    .res 4
s_y:    .res 4
s_dx:   .res 4
s_dy:   .res 4
s_rate: .res 4
s_cnt:  .res 4
s_fr:   .res 4
s_chr:  .res 4
