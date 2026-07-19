; ui.s — title screen, marquee, ghost roster parade, high-score display,
; attract demo, and the game-start flow (spec §14).
;
; game_state 5 = title, 6 = attract demo. Hidden keys 1/2/3 play the acts
; (wired in T13 via act_req).

MARQ_T = 4                      ; marquee rectangle rows 4-15, cols 7-32
MARQ_B = 15
MARQ_L = 7
MARQ_R = 32

        .segment "CODE"

; ---- title_enter: draw the static title and settle into attract ----
title_enter:
        jsr     snd_off
        lda     #FX_NONE
        sta     snd_cur
        lda     #0
        sta     gon
        sta     title_t
        sta     title_t+1
        sta     demo_mode
        jsr     clrscr
        ldx     #0
te1:    lda     ttl_recs,x      ; (rowcol-offset lo/hi, string index) recs
        cmp     #$FF
        beq     te2
        sta     PTR
        lda     ttl_recs+1,x
        sta     PTR+1
        lda     ttl_recs+2,x
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        jsr     puts
        inx
        inx
        inx
        bne     te1
te2:    jsr     hs_show
        jsr     big_title
        lda     #5
        sta     game_state
        rts

; ---- big_title: MS.MUNCHER in large rounded PETSCII letters, rows 0-2 ----
big_title:
        lda     #0
        sta     uitmp2          ; letter index 0-9
bt1:    lda     uitmp2
        cmp     #10
        bcs     bt_done
        tay
        lda     bigstr,y        ; glyph id -> *9 = font offset
        asl
        asl
        asl
        sta     uitmp
        lda     bigstr,y
        clc
        adc     uitmp
        sta     uitmp
        lda     uitmp2          ; column = letter*4
        asl
        asl
        sta     uitmp3
        ldx     #0              ; row 0-2
bt2:    lda     rowscr_lo,x
        clc
        adc     uitmp3
        sta     PTR
        lda     rowscr_hi,x
        adc     #0
        sta     PTR+1
        txa
        pha
        asl                     ; row*3 + glyph offset
        sta     uidig
        pla
        pha
        clc
        adc     uidig
        clc
        adc     uitmp
        tax
        ldy     #0
bt3:    lda     bigfont,x
        sta     (PTR),y
        inx
        iny
        cpy     #3
        bne     bt3
        pla
        tax
        inx
        cpx     #3
        bne     bt2
        inc     uitmp2
        jmp     bt1
bt_done:rts

; puts: copy 0-terminated screen codes from (PTR2) to (PTR)
puts:   ldy     #0
pu_1:   lda     (PTR2),y
        beq     pu_2
        sta     (PTR),y
        iny
        bne     pu_1
pu_2:   rts

; hs_show: the top-5 table under the marquee
hs_show:
        ldx     #0              ; entry index 0-4
hh1:    txa
        asl
        clc
        adc     hsx3,x          ; *3
        tay
        sty     uitmp2
        txa
        pha
        lda     hsrow_lo,x
        sta     PTR
        lda     hsrow_hi,x
        sta     PTR+1
        lda     #5
        sta     uidig
        ldy     uitmp2
        ldx     #0
hh2:    lda     hs_nm,y         ; initials
        sta     uitmp
        tya
        pha
        lda     uitmp
        ldy     hscol,x
        sta     (PTR),y
        pla
        tay
        iny
        inx
        cpx     #3
        bne     hh2
        ; score: 6 digits from the 3 BCD bytes (high byte first;
        ; hs2dig clobbers Y, so reload the entry offset each time)
        ldy     uitmp2
        lda     hs_sc+2,y
        jsr     hs2dig
        ldy     uitmp2
        lda     hs_sc+1,y
        jsr     hs2dig
        ldy     uitmp2
        lda     hs_sc,y
        jsr     hs2dig
        pla
        tax
        inx
        cpx     #5
        bne     hh1
        rts
hs2dig: pha
        lsr
        lsr
        lsr
        lsr
        clc
        adc     #48
        ldy     uidig
        sta     (PTR),y
        iny
        pla
        and     #$0F
        clc
        adc     #48
        sta     (PTR),y
        iny
        sty     uidig
        rts

; ---- title_tick: marquee animation, roster parade, key handling ----
title_tick:
        inc     title_t
        bne     tt0
        inc     title_t+1
tt0:    lda     title_t
        and     #7
        bne     tt1
        jsr     marquee         ; chase the lights every 8 jiffies
tt1:    ; roster parade: one ghost (with name) appears per ~1.5 s
        lda     title_t+1
        bne     tt2
        lda     title_t
        ldx     #0
tt11:   cmp     par_when,x
        bne     tt12
        txa
        pha
        jsr     par_show
        pla
        tax
tt12:   inx
        cpx     #6
        bne     tt11
tt2:    ; keys: SPACE starts; 1/2/3 request the acts (T13)
        lda     keybuf
        cmp     #K_SP
        bne     tt3
        jmp     newgame
tt3:    cmp     #K_1
        bcc     tt4
        cmp     #K_3+1
        bcs     tt4
        sec
        sbc     #K_1-1          ; act number 1-3: play it right now
        ldx     #0
        stx     act_from
        jmp     act_enter
tt4:    ; after ~15 s of title, roll the attract demo
        lda     title_t+1
        cmp     #>900
        bne     tt5
        lda     title_t
        cmp     #<900
        bne     tt5
        jmp     demo_enter
tt5:    rts

; marquee: dotted border with a rotating "lights" phase
marquee:
        inc     mq_ph
        lda     #MARQ_L         ; top and bottom edges
        sta     uicol
mqt:    lda     uicol
        ldx     #MARQ_T
        jsr     mq_cell
        lda     uicol
        ldx     #MARQ_B
        jsr     mq_cell
        inc     uicol
        lda     uicol
        cmp     #MARQ_R+1
        bne     mqt
        lda     #MARQ_T+1       ; side edges
        sta     uirow
mqs:    lda     #MARQ_L
        ldx     uirow
        jsr     mq_cell
        lda     #MARQ_R
        ldx     uirow
        jsr     mq_cell
        inc     uirow
        lda     uirow
        cmp     #MARQ_B
        bne     mqs
        rts

; mq_cell: A = col, X = row. Light on when (col+row+phase) mod 4 == 0.
mq_cell:
        sta     uitmp
        clc
        adc     mq_ph
        sta     uitmp3
        txa
        clc
        adc     uitmp3
        and     #3
        cmp     #1
        lda     #G_DOT
        bcs     mqc1
        lda     #G_BALL
mqc1:   pha
        lda     rowscr_lo,x
        sta     PTR
        lda     rowscr_hi,x
        sta     PTR+1
        ldy     uitmp
        pla
        sta     (PTR),y
        rts

; par_show: X = parade step: 0-3 ghosts, 4 STARRING, 5 her
par_show:
        cpx     #4
        bcs     ps2
        txa
        pha
        lda     parrow,x
        tay
        lda     rowscr_lo,y
        sta     PTR
        lda     rowscr_hi,y
        sta     PTR+1
        lda     parglyph,x
        ldy     #12
        sta     (PTR),y
        pla
        tax
        lda     parstr,x
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        lda     PTR
        clc
        adc     #14
        sta     PTR
        bcc     ps1
        inc     PTR+1
ps1:    jmp     puts
ps2:    bne     ps3
        lda     #<(SCREEN+12*40+13) ; "STARRING"
        sta     PTR
        lda     #>(SCREEN+12*40+13)
        sta     PTR+1
        lda     #S_STARRING
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        jmp     puts
ps3:    lda     #<(SCREEN+13*40+13) ; her name + ball
        sta     PTR
        lda     #>(SCREEN+13*40+13)
        sta     PTR+1
        lda     #S_MSMUNCH
        tay
        lda     strs_lo,y
        sta     PTR2
        lda     strs_hi,y
        sta     PTR2+1
        jsr     puts
        lda     #G_BALL
        sta     SCREEN+13*40+11
        rts

; ---- demo_enter / demo flow: a scripted game with a fixed seed ----
demo_enter:
        jsr     newgame
        lda     #$77            ; fixed seed: the demo replays identically
        sta     rng
        lda     #$31
        sta     rng+1
        lda     #1
        sta     demo_mode
        lda     #0
        sta     demo_i
        sta     demo_t
        sta     demo_t+1
        lda     #6
        sta     game_state
        ldx     #0              ; "DEMO" over the 1UP label
dm0:    lda     s_demo,x
        beq     dm01
        sta     SCREEN+2*40+29,x
        inx
        bne     dm0
dm01:   rts

demo_tick:
        inc     demo_t
        bne     dm1
        inc     demo_t+1
dm1:    lda     keybuf          ; a human takes over any time
        cmp     #K_SP
        bne     dm2
        jmp     newgame
dm2:    ldy     demo_i          ; scripted steering (bounded: reading past
        cpy     #7              ; the table once fed garbage into pwant and
        bcs     dm3             ; teleported her into code — see AUDIT.md)
        lda     demo_when,y
        cmp     demo_t
        bne     dm3
        lda     demo_dir,y
        sta     pwant
        inc     demo_i
dm3:    jsr     player_tick
        jsr     ghosts_tick
        jsr     fruit_tick
        jsr     popup_tick
        lda     game_state      ; collision flipped us into dying?
        cmp     #1
        bne     dm4
        jmp     title_enter     ; demo over
dm4:    lda     demo_t+1
        cmp     #4              ; ~17 s cap
        bne     dm5
        jmp     title_enter
dm5:    lda     #6
        sta     game_state      ; stay in demo state
        rts

        .segment "RODATA"
; title strings (screen codes, 0-terminated)
s_title:  .byte 141,147,174,160,141,149,142,131,136,133,146,0 ; reverse "MS. MUNCHER"
s_with:   .byte 23,9,20,8,0                                   ; WITH
s_bruiser:.byte 2,18,21,9,19,5,18,0
s_pixie:  .byte 16,9,24,9,5,0
s_ivy:    .byte 9,22,25,0
s_sable:  .byte 19,1,2,12,5,0
s_starring:.byte 19,20,1,18,18,9,14,7,0
s_msmunch:.byte 13,19,46,32,13,21,14,3,8,5,18,0
s_ctrl:   .byte 23,47,1,47,19,47,4,61,13,15,22,5,32,32,19,16,1,3,5,61,19,20,1,18,20,0
s_hstitle:.byte 8,9,7,8,32,19,3,15,18,5,19,0
s_demo:   .byte 4,5,13,15,32,32,0                             ; "DEMO  "
S_TITLE   = 0
S_WITH    = 1
S_BRUISER = 2
S_PIXIE   = 3
S_IVY     = 4
S_SABLE   = 5
S_STARRING= 6
S_MSMUNCH = 7
S_CTRL    = 8
S_HSTITLE = 9
strs_lo: .byte <s_title,<s_with,<s_bruiser,<s_pixie,<s_ivy,<s_sable
         .byte <s_starring,<s_msmunch,<s_ctrl,<s_hstitle
         .byte <s_act1,<s_act2,<s_act3
strs_hi: .byte >s_title,>s_with,>s_bruiser,>s_pixie,>s_ivy,>s_sable
         .byte >s_starring,>s_msmunch,>s_ctrl,>s_hstitle
         .byte >s_act1,>s_act2,>s_act3
; static layout records: screen addr lo/hi + string id, $FF end
ttl_recs:
        .byte <(SCREEN+6*40+18), >(SCREEN+6*40+18), S_WITH
        .byte <(SCREEN+17*40+7), >(SCREEN+17*40+7), S_CTRL
        .byte <(SCREEN+19*40+14), >(SCREEN+19*40+14), S_HSTITLE
        .byte $FF
; parade: appearance times (title_t low byte), rows, glyphs, names
par_when: .byte 60, 100, 140, 180, 220, 240
parrow:   .byte 7, 8, 9, 10
parglyph: .byte G_BRUISER, G_PIXIE, G_IVY, G_SABLE
parstr:   .byte S_BRUISER, S_PIXIE, S_IVY, S_SABLE
; high-score table rows 20-24 col 12: name at 0-2, score digits at 5-10
hsrow_lo: .byte <(SCREEN+20*40+12), <(SCREEN+21*40+12), <(SCREEN+22*40+12)
          .byte <(SCREEN+23*40+12), <(SCREEN+24*40+12)
hsrow_hi: .byte >(SCREEN+20*40+12), >(SCREEN+21*40+12), >(SCREEN+22*40+12)
          .byte >(SCREEN+23*40+12), >(SCREEN+24*40+12)
hscol:    .byte 0, 1, 2
; big title: glyph ids for "MS.MUNCHER" into the 3x3 font below
bigstr: .byte 0,1,2,0,3,4,5,6,7,8
; 3x3 rounded letterforms (quarter-arcs + lines), 9 bytes each:
; M S . U N C H E R
bigfont:
        .byte 85,114,73, 93,93,93, 93,32,93      ; M
        .byte 85,64,64, 74,64,73, 64,64,75       ; S
        .byte 32,32,32, 32,32,32, 32,81,32       ; .
        .byte 93,32,93, 93,32,93, 74,64,75       ; U
        .byte 93,77,93, 93,77,93, 93,77,93       ; N
        .byte 85,64,64, 93,32,32, 74,64,64       ; C
        .byte 93,32,93, 107,64,115, 93,32,93     ; H
        .byte 85,64,64, 107,64,32, 74,64,64      ; E
        .byte 85,64,73, 107,64,75, 93,32,77      ; R
; demo steering script (demo_t low byte, direction)
demo_when: .byte 1,  40,  90, 140, 190, 240, 255
demo_dir:  .byte 1,   0,   3,   0,   1,   2,   1

        .segment "BSS"
title_t:.res 2
mq_ph:  .res 1
demo_mode:.res 1
demo_i: .res 1
demo_t: .res 2
act_req:.res 1
uitmp:  .res 1
uitmp2: .res 1
uitmp3: .res 1
uidig:  .res 1
uicol:  .res 1
uirow:  .res 1
