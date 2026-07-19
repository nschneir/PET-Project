; hud.s — scoring (BCD), the HUD side panel, score popups, the top-5
; high-score table with arcade initials entry, game over, board clear.
;
; Score layout: 3 BCD bytes, score[0]=tens/units .. score[2]=hundred-
; thousands/ten-thousands. Extra life at 10,000 exactly once (spec §12).

; addscore indices
SC_DOT   = 0                    ; 10
SC_ENER  = 1                    ; 50
SC_GH1   = 2                    ; 200 400 800 1600 (chain = SC_GH1+chain-1)
SC_FRUIT = 6                    ; +fkind: 100 200 500 700 1000 2000 5000

HUDBASE = SCREEN+29

        .segment "CODE"

; ---- hs_seed: boot-only default table (5000..1000, "AAA") ----
hs_seed:
        ldx     #14
hz1:    lda     #1              ; 'A'
        sta     hs_nm,x
        lda     #0
        sta     hs_sc,x
        dex
        bpl     hz1
        ldx     #0
        ldy     #5
hz2:    tya
        pha
        asl                     ; entry value: (5-rank) thousands, BCD $x0
        asl
        asl
        asl
        sta     hs_sc+1,x
        inx
        inx
        inx
        pla
        tay
        dey
        bne     hz2
        rts

; ---- hud_init: static labels + zeroed dynamic fields ----
hud_init:
        ldx     #0
hi1:    lda     txt_1up,x
        beq     hi2
        sta     SCREEN+2*40+29,x
        inx
        bne     hi1
hi2:    ldx     #0
hi3:    lda     txt_high,x
        beq     hi4
        sta     SCREEN+5*40+29,x
        inx
        bne     hi3
hi4:    ldx     #0
hi5:    lda     txt_round,x
        beq     hi6
        sta     SCREEN+8*40+29,x
        inx
        bne     hi5
hi6:    jsr     drawscore
        jsr     drawhi
        jsr     drawround
        jsr     drawlives
        rts

; ---- addscore: A = point-table index. BCD add + extra life + hiscore ----
addscore:
        sta     sctmp
        txa
        pha
        lda     sctmp
        asl
        clc
        adc     sctmp           ; *3
        tax
        sed
        clc
        lda     score
        adc     pts,x
        sta     score
        lda     score+1
        adc     pts+1,x
        sta     score+1
        lda     score+2
        adc     pts+2,x
        sta     score+2
        cld
        lda     extra_given     ; one bonus life at 10,000
        bne     as1
        lda     score+2
        beq     as1
        inc     extra_given
        inc     lives
        inc     fanfare_ev
        jsr     drawlives
        lda     #FX_EXTRA
        jsr     snd_play
as1:    sec                     ; hiscore chases the live score
        lda     hiscore
        sbc     score
        lda     hiscore+1
        sbc     score+1
        lda     hiscore+2
        sbc     score+2
        bcs     as2
        lda     score
        sta     hiscore
        lda     score+1
        sta     hiscore+1
        lda     score+2
        sta     hiscore+2
        jsr     drawhi
as2:    jsr     drawscore
        pla
        tax
        rts

; ---- drawscore/drawhi: 6 BCD digits into the HUD ----
drawscore:
        lda     score
        sta     d6buf
        lda     score+1
        sta     d6buf+1
        lda     score+2
        sta     d6buf+2
        lda     #<(SCREEN+3*40+29)
        sta     PTR
        lda     #>(SCREEN+3*40+29)
        sta     PTR+1
        jmp     draw6
drawhi: lda     hiscore
        sta     d6buf
        lda     hiscore+1
        sta     d6buf+1
        lda     hiscore+2
        sta     d6buf+2
        lda     #<(SCREEN+6*40+29)
        sta     PTR
        lda     #>(SCREEN+6*40+29)
        sta     PTR+1
draw6:  ldx     #2
d61:    lda     d6buf,x
        pha
        lsr
        lsr
        lsr
        lsr
        clc
        adc     #48
        ldy     dcol,x
        sta     (PTR),y
        pla
        and     #$0F
        clc
        adc     #48
        iny
        sta     (PTR),y
        dex
        bpl     d61
        rts

; ---- drawround / drawlives ----
drawround:
        lda     board
        ldx     #48
        cmp     #10
        bcc     dr1
        sec
        sbc     #10
        ldx     #49             ; '1x'
        cmp     #10
        bcc     dr1
        sec
        sbc     #10
        ldx     #50
dr1:    clc
        adc     #48
        stx     SCREEN+9*40+29
        sta     SCREEN+9*40+30
        rts
drawlives:
        ldx     #0
dl1:    lda     #G_SPACE
        cpx     lives
        bcs     dl2
        lda     #G_BALL
dl2:    sta     SCREEN+11*40+29,x
        inx
        cpx     #5
        bne     dl1
        rts

; ---- popup: 4-char value at the event cell for ~3/4 s ----
; A = value-string index (same indexing as addscore), X = actor whose cell
popup_at:
        sta     sctmp
        lda     pop_t
        bne     pu_out          ; one at a time; latest loses
        txa
        pha
        lda     ay,x
        lsr
        tay
        lda     rowscr_lo,y
        sta     pop_addr
        lda     rowscr_hi,y
        sta     pop_addr+1
        lda     ax,x
        lsr
        cmp     #24             ; clip so 4 chars stay inside the maze
        bcc     pu1
        lda     #24
pu1:    clc
        adc     pop_addr
        sta     pop_addr
        bcc     pu2
        inc     pop_addr+1
pu2:    lda     pop_addr
        sta     PTR
        lda     pop_addr+1
        sta     PTR+1
        lda     sctmp           ; save under + draw the 4 chars, forward
        asl
        asl
        tax
        ldy     #0
pu3:    lda     (PTR),y
        sta     pop_save,y
        lda     valstr,x
        sta     (PTR),y
        inx
        iny
        cpy     #4
        bne     pu3
        lda     #45
        sta     pop_t
        pla
        tax
pu_out: rts

popup_tick:
        lda     pop_t
        bne     pt1x
        rts
pt1x:   dec     pop_t
        bne     pt2x
        lda     pop_addr        ; expired: restore what was underneath
        sta     PTR
        lda     pop_addr+1
        sta     PTR+1
        ldy     #3
pt3x:   lda     pop_save,y
        sta     (PTR),y
        dey
        bpl     pt3x
pt2x:   rts

; ---- board clear: celebrate + next board (progression tables in T11) ----
boardclr_tick:
        inc     death_t         ; reuse the sequence timer
        lda     death_t
        cmp     #16
        bcc     bc_flash
        cmp     #60
        bcc     bc_wait
        lda     #0              ; next board
        sta     death_t
        sta     game_state
        inc     board
        lda     board
        cmp     #22
        bcc     bc1
        lda     #21             ; tables saturate; the game runs forever
        sta     board
bc1:    jsr     maze_select
        jsr     unpack_maze
        jsr     draw_maze
        jsr     init_actors
        jsr     player_init
        jsr     ghost_init
        jsr     fruit_init
        jsr     drawround
        lda     #0
        sta     frite_t
        sta     frite_t+1
        sta     elvl
        sta     gdmode
        rts
bc_flash:
        lda     death_t         ; wall flash: alternate maze style briefly
        and     #4
        beq     bcf1
        lda     #2              ; solid pulse
        bne     bcf2
bcf1:   lda     #0
bcf2:   sta     mstyle
        jsr     draw_maze
bc_wait:rts

; ---- game over + initials entry ----
gameover_tick:
        inc     death_t
        lda     death_t
        cmp     #1
        bne     go1
        ldx     #0
go0:    lda     txt_gover,x     ; "GAME OVER" centre
        beq     go1
        sta     SCREEN+12*40+9,x
        inx
        bne     go0
go1:    lda     death_t
        cmp     #150
        bcc     go_out
        jsr     hs_rank         ; C clear = made the table
        bcc     go_entry
        jmp     newgame
go_entry:
        lda     #0
        sta     death_t
        sta     ini_pos
        lda     #1              ; 'A'
        sta     ini_ch
        sta     ini_ch+1
        sta     ini_ch+2
        lda     #$FF
        sta     lastkey
        ldx     #0
go2:    lda     txt_inits,x
        beq     go3
        sta     SCREEN+14*40+7,x
        inx
        bne     go2
go3:    lda     #3
        sta     game_state
go_out: rts

initials_tick:
        jsr     ini_draw
        lda     KEYDOWN
        cmp     lastkey         ; edge-triggered: act once per press
        bne     it1
        rts
it1:    sta     lastkey
        cmp     #K_W
        bne     it2
        ldx     ini_pos
        ldy     ini_ch,x
        lda     nxtch,y
        sta     ini_ch,x
        rts
it2:    cmp     #K_S
        bne     it3
        ldx     ini_pos
        ldy     ini_ch,x
        lda     prvch,y
        sta     ini_ch,x
        rts
it3:    cmp     #K_D
        bne     it4
        lda     ini_pos
        cmp     #2
        bcs     it_out
        inc     ini_pos
        rts
it4:    cmp     #K_A
        bne     it5
        lda     ini_pos
        beq     it_out
        dec     ini_pos
        rts
it5:    cmp     #K_SP
        bne     it_out
        jsr     hs_insert
        jmp     newgame
it_out: rts

ini_draw:
        ldx     #2
id1:    lda     ini_ch,x
        cpx     ini_pos         ; the active slot blinks (reverse video)
        bne     id2
        ldy     tickcnt
        cpy     #128
        bcc     id2
        ora     #$80
id2:    sta     SCREEN+16*40+12,x
        dex
        bpl     id1
        rts

; ---- hs_rank: C clear if score beats entry 4 (the lowest) ----
hs_rank:
        lda     hs_sc+4*3+2
        cmp     score+2
        bcc     hr_yes
        bne     hr_no
        lda     hs_sc+4*3+1
        cmp     score+1
        bcc     hr_yes
        bne     hr_no
        lda     hs_sc+4*3
        cmp     score
        bcc     hr_yes
hr_no:  sec
        rts
hr_yes: clc
        rts

; ---- hs_insert: shift entries down from the right rank, write ours ----
hs_insert:
        ldx     #0              ; find rank: first entry our score beats
hs1:    txa
        asl
        clc
        adc     hsx3,x          ; X*3
        tay
        lda     hs_sc+2,y
        cmp     score+2
        bcc     hs_found
        bne     hs_next
        lda     hs_sc+1,y
        cmp     score+1
        bcc     hs_found
        bne     hs_next
        lda     hs_sc,y
        cmp     score
        bcc     hs_found
hs_next:inx
        cpx     #5
        bne     hs1
        rts                     ; (hs_rank said we qualify; never reached)
hs_found:
        stx     sctmp           ; shift 4..rank+1 down one
        ldx     #3
hs2:    cpx     sctmp
        bmi     hs3
        txa
        asl
        clc
        adc     hsx3,x
        tay
        lda     hs_sc,y
        sta     hs_sc+3,y
        lda     hs_sc+1,y
        sta     hs_sc+4,y
        lda     hs_sc+2,y
        sta     hs_sc+5,y
        lda     hs_nm,y
        sta     hs_nm+3,y
        lda     hs_nm+1,y
        sta     hs_nm+4,y
        lda     hs_nm+2,y
        sta     hs_nm+5,y
        dex
        cpx     sctmp
        bpl     hs2
hs3:    ldx     sctmp           ; write the new entry
        txa
        asl
        clc
        adc     hsx3,x
        tay
        lda     score
        sta     hs_sc,y
        lda     score+1
        sta     hs_sc+1,y
        lda     score+2
        sta     hs_sc+2,y
        lda     ini_ch
        sta     hs_nm,y
        lda     ini_ch+1
        sta     hs_nm+1,y
        lda     ini_ch+2
        sta     hs_nm+2,y
        rts

; ---- newgame: fresh game (T12 reroutes to the title instead) ----
newgame:
        lda     JIFFLO          ; reseed the anti-pattern randomiser
        sta     rng
        eor     #$5A
        ora     #1
        sta     rng+1
        lda     #0
        sta     score
        sta     score+1
        sta     score+2
        sta     extra_given
        sta     death_t
        sta     game_state
        sta     frite_t
        sta     frite_t+1
        sta     elvl
        sta     gdmode
        sta     gameover_ev
        lda     #3
        sta     lives
        lda     #1
        sta     board
        jsr     maze_select
        jsr     clrscr
        jsr     banner
        jsr     unpack_maze
        jsr     draw_maze
        jsr     init_actors
        jsr     player_init
        jsr     ghost_init
        jsr     fruit_init
        jsr     hud_init
        jsr     snd_init
        lda     #FX_JINGLE
        jmp     snd_play

        .segment "RODATA"
; BCD point values, 3 bytes each, low first
pts:    .byte $10,$00,$00, $50,$00,$00
        .byte $00,$02,$00, $00,$04,$00, $00,$08,$00, $00,$16,$00
        .byte $00,$01,$00, $00,$02,$00, $00,$05,$00, $00,$07,$00
        .byte $00,$10,$00, $00,$20,$00, $00,$50,$00
; 4-char value strings (screen codes), same indexing
valstr: .byte 32,32,49,48, 32,32,53,48
        .byte 32,50,48,48, 32,52,48,48, 32,56,48,48, 49,54,48,48
        .byte 32,49,48,48, 32,50,48,48, 32,53,48,48, 32,55,48,48
        .byte 49,48,48,48, 50,48,48,48, 53,48,48,48
dcol:   .byte 4, 2, 0          ; digit column pairs by byte index
txt_1up:  .byte 49,21,16,0                          ; "1UP"
txt_high: .byte 8,9,7,8,0                           ; "HIGH"
txt_round:.byte 18,15,21,14,4,0                     ; "ROUND"
txt_gover:.byte 7,1,13,5,32,15,22,5,18,0            ; "GAME OVER"
txt_inits:.byte 9,14,9,20,9,1,12,19,63,0            ; "INITIALS?"
hsx3:   .byte 0,1,2,3,4        ; X*3 helper: (X<<1)+hsx3[X] = X*3
; initials character cycle: A..Z, 0..9, space
nxtch:  .res 0
        .byte 0                 ; [0] unused
        .byte 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,48 ; A..Z ->
        .byte 0,0,0,0,0         ; 27-31 unused
        .byte 1                 ; [32] space -> A
        .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 ; 33-47 unused
        .byte 49,50,51,52,53,54,55,56,57,32 ; 48-57: 0..9 -> (9 -> space)
prvch:  .byte 0
        .byte 32,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25 ; A..Z <-
        .byte 0,0,0,0,0
        .byte 57                ; space <- 9
        .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        .byte 26,48,49,50,51,52,53,54,55,56 ; 0..9 <-

        .segment "BSS"
score:  .res 3
hiscore:.res 3
extra_given: .res 1
fanfare_ev:  .res 1
sctmp:  .res 2
pop_t:  .res 1
pop_addr:.res 2
pop_save:.res 4
d6buf:  .res 3
hs_sc:  .res 15                 ; 5 entries x 3 BCD bytes
hs_nm:  .res 15                 ; 5 entries x 3 initials (screen codes)
ini_pos:.res 1
ini_ch: .res 3
lastkey:.res 1
