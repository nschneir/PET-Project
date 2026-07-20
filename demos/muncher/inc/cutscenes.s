; cutscenes.s — the three story acts (spec §15), staged with LARGE
; multi-character sprites: 10x6 rounded munchers (she wears a bow) with
; real mouth wedges, 10x6 ghosts with eyes and a textured hem, a 10x6
; stork, a composed heart, and a tiny Munchkin. The acts own the whole
; screen, so the cast can be theatre-sized; a 60-cell blit costs ~1.1K
; cycles of the 16.6K-cycle frame — nowhere near the budget.
; game_state 7. SPACE skips. All art is original PETSCII composition.
;
; act_t advances every second jiffy. Sprites move whole cells at their own
; rates; a sprite that walks off an edge erases itself and switches off.

; sprite kinds
K_HIM   = 0                     ; 10x6 muncher
K_HER   = 1                     ; 10x6 muncher + bow overlay
K_GHOST = 2                     ; 10x6 ghost
K_STORK = 3                     ; 10x6 bird
K_HEART = 4                     ; 4x3 heart, static
K_BABY  = 5                     ; 3x2 little one
K_CHAR  = 6                     ; single character (the bundle)

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
        ldy     act_no          ; title card (no marquee: the cast is big)
        lda     actstr-1,y
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        lda     #<(SCREEN+1*40+12)
        sta     PTR
        lda     #>(SCREEN+1*40+12)
        sta     PTR+1
        jsr     puts
        lda     act_no          ; the act's original tune
        clc
        adc     #FX_ACT1-1
        jsr     snd_play
        ldy     act_no
        cpy     #2
        bne     :+
        jmp     a2_set
:       bcc     :+
        jmp     a3_set
:
; --- Act 1: he crosses low chased by Ivy, she crosses high chased by
; Pixie; they pull up short of each other and rise; the ghosts pile in ---
a1_set: ldx     #0              ; he crosses the low lane...
        lda     #K_HIM
        jsr     s_def
        lda     #5
        sta     s_rate
        sta     s_cnt
        lda     #0
        sta     s_x
        lda     #12
        sta     s_y
        lda     #1
        sta     s_dx
        ldx     #1              ; ...with Ivy on his tail (enters later)
        lda     #K_GHOST
        jsr     s_def
        lda     #0
        sta     s_x+1
        sta     s_on+1
        lda     #12
        sta     s_y+1
        lda     #1
        sta     s_dx+1
        lda     #5
        sta     s_rate+1
        sta     s_cnt+1
        ldx     #2              ; she crosses the high lane...
        lda     #K_HER
        jsr     s_def
        lda     #30
        sta     s_x+2
        lda     #5
        sta     s_y+2
        sta     s_rate+2
        sta     s_cnt+2
        lda     #$FF
        sta     s_dx+2
        ldx     #3              ; ...Pixie close behind (enters later)
        lda     #K_GHOST
        jsr     s_def
        lda     #30
        sta     s_x+3
        lda     #0
        sta     s_on+3
        lda     #5
        sta     s_y+3
        sta     s_rate+3
        sta     s_cnt+3
        lda     #$FF
        sta     s_dx+3
        jmp     ae_go
; --- Act 2: first chase pass ---
a2_set: jsr     a2_p1
        jmp     ae_go
; --- Act 3: proud parents; the stork brings a bundle ---
a3_set: ldx     #0
        lda     #K_HIM
        jsr     s_def
        lda     #4
        sta     s_x
        lda     #15
        sta     s_y
        jsr     spr_draw
        ldx     #2
        lda     #K_HER
        jsr     s_def
        lda     #24
        sta     s_x+2
        lda     #15
        sta     s_y+2
        jsr     spr_draw
        ldx     #1              ; the stork
        lda     #K_STORK
        jsr     s_def
        lda     #0
        sta     s_x+1
        lda     #3
        sta     s_y+1
        lda     #1
        sta     s_dx+1
        lda     #4
        sta     s_rate+1
        ldx     #3              ; the bundle, slung under the beak
        lda     #K_CHAR
        jsr     s_def
        lda     #G_BALL
        sta     s_chr+3
        lda     #8
        sta     s_x+3
        lda     #7
        sta     s_y+3
        lda     #1
        sta     s_dx+3
        lda     #4
        sta     s_rate+3
ae_go:  lda     #7
        sta     game_state
        jmp     jsync

; s_def: X = slot, A = kind: on, parked, rate 3
s_def:  sta     s_kind,x
        lda     #1
        sta     s_on,x
        lda     #0
        sta     s_dx,x
        sta     s_dy,x
        sta     s_fr,x
        lda     #3
        sta     s_rate,x
        sta     s_cnt,x
        rts

; ---- blit: rectangle W=bw H=bh at (s_x,s_y) of slot X.
; bspace=0: art from (PTR2), read linearly. bspace=1: spaces (erase). ----
blit:   lda     by
        sta     brow
        lda     #0
        sta     brr
        sta     bidx
bl1:    ldy     brow
        lda     rowscr_lo,y
        sta     PTR
        lda     rowscr_hi,y
        sta     PTR+1
        ldy     bx
        lda     #0
        sta     bcc2
bl2:    lda     bspace
        beq     bl_art
        lda     #G_SPACE
        bne     bl3
bl_art: sty     btmpy
        ldy     bidx
        lda     (PTR2),y
        inc     bidx
        ldy     btmpy
bl3:    sta     (PTR),y
        iny
        inc     bcc2
        lda     bcc2
        cmp     bw
        bne     bl2
        inc     brow
        inc     brr
        lda     brr
        cmp     bh
        bne     bl1
        rts

; kdims: set bw/bh from the slot's kind
kdims:  ldy     s_kind,x
        lda     k_w,y
        sta     bw
        lda     k_h,y
        sta     bh
        rts

spr_erase:
        lda     s_on,x
        bne     se0
        rts
se0:    lda     s_kind,x
        cmp     #K_CHAR
        bne     se1
        jsr     spr_addr1
        lda     #G_SPACE
        sta     (PTR),y
        rts
se1:    jsr     kdims
        lda     s_x,x
        sta     bx
        lda     s_y,x
        sta     by
        lda     #1
        sta     bspace
        jmp     blit

spr_addr1:                      ; PTR/Y for a single-char sprite
        ldy     s_y,x
        lda     rowscr_lo,y
        sta     PTR
        lda     rowscr_hi,y
        sta     PTR+1
        ldy     s_x,x
        rts

spr_draw:
        lda     s_on,x
        bne     sd0
        rts
sd0:    lda     s_kind,x
        cmp     #K_CHAR
        bne     sd1
        jsr     spr_addr1
        lda     s_chr,x
        sta     (PTR),y
        rts
sd1:    cmp     #K_HER
        beq     sd_m
        cmp     #K_HIM
        beq     sd_m
        tay                     ; fixed-art kinds
        lda     artlo,y
        sta     PTR2
        lda     arthi,y
        sta     PTR2+1
        jmp     sd_go
sd_m:   lda     s_dx,x          ; parked munchers sit with a closed
        ora     s_dy,x          ; mouth (the "they meet" pose)
        beq     sd_ball
        lda     s_fr,x          ; moving: ball / wedge toward travel
        and     #1
        beq     sd_ball
        lda     s_dx,x
        cmp     #1
        beq     sd_r
        lda     #<art_openl
        sta     PTR2
        lda     #>art_openl
        sta     PTR2+1
        jmp     sd_go
sd_r:   lda     #<art_openr
        sta     PTR2
        lda     #>art_openr
        sta     PTR2+1
        jmp     sd_go
sd_ball:lda     #<art_ball
        sta     PTR2
        lda     #>art_ball
        sta     PTR2+1
sd_go:  jsr     kdims
        lda     s_x,x
        sta     bx
        lda     s_y,x
        sta     by
        lda     #0
        sta     bspace
        jsr     blit
        lda     s_kind,x        ; her bow, perched on the crown
        cmp     #K_HER
        bne     sd_done
        ldy     s_y,x
        lda     rowscr_lo,y
        sta     PTR
        lda     rowscr_hi,y
        sta     PTR+1
        lda     s_x,x
        clc
        adc     #3
        tay
        lda     #233            ; left loop, knot, right loop
        sta     (PTR),y
        iny
        lda     #G_BALL
        sta     (PTR),y
        iny
        lda     #95
        sta     (PTR),y
sd_done:rts

; spr_step: X = slot. Rate-timed one-cell move; edge exits switch off.
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
        jsr     kdims
        ; would this step leave the stage? then bow out gracefully
        lda     s_x,x
        clc
        adc     s_dx,x
        sta     bnx
        bmi     ss_off          ; past the left edge
        clc
        adc     bw
        cmp     #41
        bcs     ss_off          ; past the right edge
        lda     s_y,x
        clc
        adc     s_dy,x
        sta     bny
        cmp     #3
        bcc     ss_park         ; never rise over the title card
        clc
        adc     bh
        cmp     #26
        bcs     ss_off          ; past the bottom
        jsr     spr_erase
        lda     bnx
        sta     s_x,x
        lda     bny
        sta     s_y,x
        inc     s_fr,x
        jmp     spr_draw
ss_park:lda     #0
        sta     s_dy,x
        jmp     spr_draw        ; settle into the parked pose
ss_off: jsr     spr_erase
        lda     #0
        sta     s_on,x
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
        lda     act_t           ; the chasers file in behind their marks
        cmp     #4
        bne     :+
        lda     #1
        sta     s_on+1
:       cmp     #8
        bne     :+
        lda     #1
        sta     s_on+3
:       lda     s_x+2           ; two columns shy of touching: pull up
        sec
        sbc     s_x
        cmp     #15
        bcs     ak1_out
        lda     #0
        sta     s_dx
        sta     s_dx+2
        lda     #$FF
        sta     s_dy
        sta     s_dy+2
        ldx     #1              ; the shadows crash off-stage (implied)
        jsr     spr_erase
        lda     #0
        sta     s_on+1
        ldx     #3
        jsr     spr_erase
        lda     #0
        sta     s_on+3
        inc     act_ph
        rts
ak1_5:  cmp     #1
        bne     ak1_7
        lda     s_dy            ; both parked at the top (ss_park)?
        ora     s_dy+2
        beq     :+
        rts
:       lda     s_x             ; a heart blooms between them (direct
        clc                     ; blit — every slot is in use)
        adc     #10
        sta     bx
        lda     #5
        sta     by
        lda     #4
        sta     bw
        lda     #3
        sta     bh
        lda     #<art_heart
        sta     PTR2
        lda     #>art_heart
        sta     PTR2+1
        lda     #0
        sta     bspace
        jsr     blit
        inc     act_ph
        lda     act_t
        clc
        adc     #110
        sta     act_h
        rts
ak1_7:  cmp     #2
        bne     ak1_out
        lda     act_t
        cmp     act_h
        bcc     ak1_out
        jmp     act_end
ak1_out:rts
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
        rts                     ; the breather: empty stage, music plays
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
        lda     s_x+3           ; the bundle is over the gap: let go
        cmp     #17
        bcc     ak_out
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
        lda     s_y+3           ; touchdown between the parents
        cmp     #14
        bcc     ak_out
        lda     #0
        sta     s_dy+3
        ldx     #3              ; the bundle pops open: little Munchkin
        jsr     spr_erase
        lda     #K_BABY
        sta     s_kind+3
        ldx     #3
        jsr     spr_draw
        lda     rowscr_lo+10    ; and a heart above the little one
        sta     PTR
        lda     rowscr_hi+10
        sta     PTR+1
        ldy     s_x+3
        lda     #G_HEART
        sta     (PTR),y
        inc     act_ph
        lda     act_t
        clc
        adc     #60
        sta     act_h
        rts
ak3_4:  lda     act_t
        cmp     act_h
        bcs     :+
        jmp     ak_out
:       jmp     act_end
ak_out: rts

; act 2 pass setups: both on one lane, the leader out front
a2_p1:  ldx     #0              ; he leads right along the upper lane
        lda     #K_HIM
        jsr     s_def
        lda     #14
        sta     s_x
        lda     #5
        sta     s_y
        lda     #1
        sta     s_dx
        ldx     #2
        lda     #K_HER
        jsr     s_def
        lda     #1
        sta     s_x+2
        lda     #5
        sta     s_y+2
        lda     #1
        sta     s_dx+2
        rts
a2_p2:  ldx     #0              ; she leads left along the lower lane
        lda     #K_HIM
        jsr     s_def
        lda     #29
        sta     s_x
        lda     #12
        sta     s_y
        lda     #$FF
        sta     s_dx
        ldx     #2
        lda     #K_HER
        jsr     s_def
        lda     #16
        sta     s_x+2
        lda     #12
        sta     s_y+2
        lda     #$FF
        sta     s_dx+2
        rts
a2_p3:  jsr     a2_p1
        lda     #16
        sta     s_y
        sta     s_y+2
        rts
a2_p4:  jsr     a2_p2
        lda     #2              ; double time
        sta     s_rate
        sta     s_rate+2
        rts
a2_p5:  jsr     a2_p1
        lda     #2
        sta     s_rate
        sta     s_rate+2
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
a2times:.byte 40, 80, 120, 135, 165, 195
k_w:    .byte 10, 10, 10, 10, 4, 3, 1
k_h:    .byte  6,  6,  6,  6, 3, 2, 1
artlo:  .byte 0, 0, <art_ghost, <art_stork, <art_heart, <art_baby, 0
arthi:  .byte 0, 0, >art_ghost, >art_stork, >art_heart, >art_baby, 0
; 10x6 muncher (solid 160, 3/4-round corners 254/252/251/236, jaw
; triangles 95/105/223/233), original composition
art_ball:
 .byte 32,32,254,160,160,160,160,252,32,32
 .byte 32,254,160,160,160,160,160,160,252,32
 .byte 254,160,160,160,160,160,160,160,160,252
 .byte 251,160,160,160,160,160,160,160,160,236
 .byte 32,251,160,160,160,160,160,160,236,32
 .byte 32,32,251,160,160,160,160,236,32,32
art_openr:
 .byte 32,32,254,160,160,160,160,252,32,32
 .byte 32,254,160,160,160,160,160,105,32,32
 .byte 254,160,160,160,160,160,105,32,32,32
 .byte 251,160,160,160,160,160,95,32,32,32
 .byte 32,251,160,160,160,160,160,95,32,32
 .byte 32,32,251,160,160,160,160,236,32,32
art_openl:
 .byte 32,32,254,160,160,160,160,252,32,32
 .byte 32,32,223,160,160,160,160,160,252,32
 .byte 32,32,32,223,160,160,160,160,160,252
 .byte 32,32,32,233,160,160,160,160,160,236
 .byte 32,32,233,160,160,160,160,160,236,32
 .byte 32,32,251,160,160,160,160,236,32,32
art_ghost:
 .byte 32,254,160,160,160,160,160,160,252,32
 .byte 254,160,160,160,160,160,160,160,160,252
 .byte 160,160,215,160,160,160,215,160,160,160
 .byte 160,160,160,160,160,160,160,160,160,160
 .byte 160,160,160,160,160,160,160,160,160,160
 .byte 230,230,230,230,230,230,230,230,230,230
art_stork:
 .byte 32,32,32,78,77,32,32,32,32,32
 .byte 32,32,78,160,160,77,32,32,32,32
 .byte 32,254,160,160,160,160,252,87,62,32
 .byte 32,251,160,160,160,160,236,32,32,32
 .byte 32,32,32,93,32,93,32,32,32,32
 .byte 32,32,32,74,32,74,32,32,32,32
art_heart:
 .byte 254,252,254,252
 .byte 160,160,160,160
 .byte 32,223,105,32
art_baby:
 .byte 254,160,252
 .byte 251,160,236

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
bw:     .res 1
bh:     .res 1
brow:   .res 1
brr:    .res 1
bidx:   .res 1
bcc2:   .res 1
btmpy:  .res 1
bspace: .res 1
bnx:    .res 1
bny:    .res 1
bx:     .res 1
by:     .res 1
