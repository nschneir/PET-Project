; fruit.s — the wandering bonus fruit (actor 5, spec §11).
;
; Spawns twice per board (scaled 64-eaten / 66-left thresholds from
; mapdata.inc), enters through a random tunnel mouth, follows its validated
; waypoint path to the house ring, laps it clockwise, walks on to a random
; exit mouth's corner, and leaves along that path reversed. The whole route
; is compiled into a run queue at spawn time; the per-tick work is trivial.

FSPD    = $28                   ; fruit ambles at 50%

; fruit path record fields (see mazecheck.py emit_fruit)
FP_SX   = 0
FP_SY   = 1
FP_CN   = 2
FP_NR   = 3
FP_RUNS = 4
FP_SIZE = 12

        .segment "CODE"

; ---- fruit_init: per-board reset ----
fruit_init:
        lda     #0
        sta     factive
        sta     f1done
        sta     f2done
        sta     fq_n
        rts

; ---- fruit_tick: once per jiffy while playing ----
fruit_tick:
        lda     factive
        bne     :+
        jmp     fspawn_chk
:       ldx     #5
        lda     ax,x            ; need a new run at each exhausted centre
        ora     ay,x
        and     #1
        bne     ft_go
        lda     fsteps
        bne     ft_go
        ldy     fq_i
        cpy     fq_n
        bcc     ft_load
        jsr     erase_blob      ; route done: the fruit escapes
        lda     #0
        sta     factive
        rts
ft_load:lda     fq_dir,y
        sta     adir,x
        lda     fq_cnt,y
        asl                     ; cells -> half-steps
        sta     fsteps
        inc     fq_i
ft_go:  lda     ax,x
        sta     fprex
        lda     ay,x
        sta     fprey
        jsr     step_actor
        lda     ax,x
        cmp     fprex
        bne     ft_moved
        lda     ay,x
        cmp     fprey
        beq     ft_coll
ft_moved:
        dec     fsteps
        lda     ax,x            ; bounce: reverse-video pulse at each centre
        ora     ay,x
        and     #1
        bne     ft_coll
        lda     arev,x
        eor     #1
        sta     arev,x
ft_coll:; eaten? same half-cell as the player, or swapped past her
        lda     ax+5
        cmp     ax
        bne     fc1
        lda     ay+5
        cmp     ay
        beq     ft_eat
fc1:    lda     ax+5
        cmp     ppx
        bne     ftk_out
        lda     ay+5
        cmp     ppy
        bne     ftk_out
        lda     fprex
        cmp     ax
        bne     ftk_out
        lda     fprey
        cmp     ay
        beq     ft_eat
ftk_out: rts
ft_eat: ldx     #5
        lda     fkind
        clc
        adc     #SC_FRUIT
        pha
        jsr     popup_at        ; value at the fruit's cell (before erase)
        pla
        jsr     addscore
        lda     #FX_FRUIT
        jsr     snd_play
        ldx     #5
        jsr     erase_blob
        lda     #0
        sta     factive
        lda     #1
        sta     fruit_ev
        rts

fspawn_chk:                     ; no fruit afield: is one due?
        lda     dots_left+1
        bne     fs_no           ; (>255 left cannot pass either threshold)
        ldx     cur_maze
        lda     f1done
        bne     fs2
        lda     mf1left_tbl-1,x
        cmp     dots_left       ; eaten >= threshold  <=>  left <= dots-thr
        bcc     fs_no
        lda     #1
        sta     f1done
        bne     fspawn
fs2:    lda     f2done
        bne     fs_no
        lda     mf2_tbl-1,x
        cmp     dots_left
        bcc     fs_no
        lda     #1
        sta     f2done
        bne     fspawn
fs_no:  rts

; ---- fspawn: build the run queue and place the fruit ----
fspawn: jsr     lfsr
        and     #3
        ldx     cur_maze
        cmp     fnmouth-1,x
        bcc     fsp1
        sec
        sbc     fnmouth-1,x
fsp1:   sta     fmin            ; entry mouth
        jsr     lfsr
        and     #3
        cmp     fnmouth-1,x
        bcc     fsp2
        sec
        sbc     fnmouth-1,x
fsp2:   sta     fmout           ; exit mouth
        lda     #0
        sta     fq_n
        sta     fq_i
        ; 1) entry path, forward
        lda     fmin
        jsr     fp_rec          ; Y = record offset
        ldy     #0
        lda     (PTR),y
        asl
        sta     ax+5            ; start position (half-cells)
        iny
        lda     (PTR),y
        asl
        sta     ay+5
        jsr     fq_addpath
        ; 2) full lap: 4 cycle segments from the entry corner
        ; (memory loop counter: fq_addcyc uses X for the queue index)
        lda     fmin
        jsr     fp_corner
        sta     fcyc
        lda     #4
        sta     ftmp2
fl1:    lda     fcyc
        jsr     fq_addcyc
        inc     fcyc
        lda     fcyc
        and     #3
        sta     fcyc
        dec     ftmp2
        bne     fl1
        ; 3) walk on around to the exit corner
        lda     fmout
        jsr     fp_corner
        sta     ftmp
fl2:    lda     fcyc
        cmp     ftmp
        beq     fl3
        jsr     fq_addcyc
        inc     fcyc
        lda     fcyc
        and     #3
        sta     fcyc
        jmp     fl2
        ; 4) exit path, reversed
fl3:    lda     fmout
        jsr     fp_rec
        ldy     #FP_NR
        lda     (PTR),y
        sta     ftmp            ; run count
fl4:    lda     ftmp
        beq     fl5
        dec     ftmp
        lda     ftmp            ; runs in reverse order, dirs flipped
        asl
        clc
        adc     #FP_RUNS
        tay
        lda     (PTR),y
        tax
        lda     opptbl,x
        ldx     fq_n
        sta     fq_dir,x
        iny
        lda     (PTR),y
        sta     fq_cnt,x
        inc     fq_n
        jmp     fl4
fl5:    ; pick the board's fruit and go
        jsr     fruit_pick
        ldx     #5
        sta     aglyph,x
        lda     #0
        sta     arev,x
        sta     aacc,x
        sta     apause,x
        sta     fsteps
        lda     #FSPD
        sta     aspd,x
        lda     #DIR_NONE       ; first run loads at the first centre check
        sta     adir,x
        lda     #1
        sta     factive
        jmp     draw_blob

; fp_rec: A = mouth 0-3 -> PTR = its 16-byte record for cur_maze
fp_rec: asl
        asl
        asl
        asl                     ; *16 (<= 48: no carry out)
        ldx     cur_maze
        clc
        adc     fpaths_lo-1,x
        sta     PTR
        lda     fpaths_hi-1,x
        adc     #0
        sta     PTR+1
        rts

; fp_corner: A = mouth -> A = its ring corner index
fp_corner:
        jsr     fp_rec
        ldy     #FP_CN
        lda     (PTR),y
        rts

; fq_addpath: append PTR record's runs (forward) to the queue
fq_addpath:
        ldy     #FP_NR
        lda     (PTR),y
        sta     ftmp2
        lda     #0
        sta     ftmp
fqa1:   lda     ftmp
        cmp     ftmp2
        beq     fqa2
        asl
        clc
        adc     #FP_RUNS
        tay
        lda     (PTR),y
        ldx     fq_n
        sta     fq_dir,x
        iny
        lda     (PTR),y
        sta     fq_cnt,x
        inc     fq_n
        inc     ftmp
        bne     fqa1
fqa2:   rts

; fq_addcyc: A = cycle segment index -> append it
fq_addcyc:
        asl
        tay
        ldx     fq_n
        lda     fruit1_cycle,y
        sta     fq_dir,x
        lda     fruit1_cycle+1,y
        sta     fq_cnt,x
        inc     fq_n
        rts

; fruit_pick: A = glyph for this board's fruit; fkind records which
fruit_pick:
        ldy     board
        cpy     #8
        bcs     fp_rand
        dey
        sty     fkind
        lda     fruitgly,y
        rts
fp_rand:jsr     lfsr            ; boards 8+: any of the seven
        and     #7
        cmp     #7
        bne     fp_ok
        lda     #3              ; (8th value folds onto the pretzel)
fp_ok:  sta     fkind
        tay
        lda     fruitgly,y
        rts

        .segment "RODATA"
; cherry, strawberry, peach, pretzel, apple, pear, banana
fruitgly: .byte 37, 90, 87, 38, 65, 88, 40

        .segment "BSS"
factive:.res 1
f1done: .res 1
f2done: .res 1
fq_dir: .res 20                 ; worst route: 6 entry + 4 lap + 3 + 6 exit
fq_cnt: .res 20
fq_n:   .res 1
fq_i:   .res 1
fsteps: .res 1
fmin:   .res 1
fmout:  .res 1
fcyc:   .res 1
ftmp:   .res 1
ftmp2:  .res 1
fprex:  .res 1
fprey:  .res 1
fkind:  .res 1
fruit_ev:.res 1
