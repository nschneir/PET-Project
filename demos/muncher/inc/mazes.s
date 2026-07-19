; mazes.s — unpack packed 2-bit maps into the working dot array and draw
; the maze with per-style wall glyphs. Not hot-path: runs at board start.
;
; Cell codes in dots[]: 0 open, 1 dot, 2 energizer, 3 wall (mazecheck.py).
; House door cells (13,10)/(14,10) pack as open; drawn as G_HLINE.

; ---- maze_select: board -> cur_maze + wall style (spec §5/§10) ----
; Boards 1-21 use the table; later boards alternate mazes 3/4 every 4.
; From board 14 the recycled 3/4 shapes SWAP styles (the arcade recolor).
maze_select:
        lda     board
        cmp     #22
        bcc     ms_tbl
        sec                     ; (board-14)/4 parity -> maze 3 or 4
        sbc     #14
        lsr
        lsr
        and     #1
        clc
        adc     #3
        jmp     ms_set
ms_tbl: tay
        lda     bmaze_tbl-1,y
ms_set: sta     cur_maze
        tay
        lda     mstyletbl-1,y
        ldx     board
        cpx     #14
        bcc     ms_ok
        cpy     #3              ; recolor: maze 3 wears maze 4's style
        bne     ms_n3
        lda     mstyletbl-1+4
        jmp     ms_ok
ms_n3:  cpy     #4              ; and maze 4 wears maze 3's
        bne     ms_ok
        lda     mstyletbl-1+3
ms_ok:  sta     mstyle
        rts

; ---- unpack_maze: cur_maze's packed map -> dots[], counts dots_left ----
unpack_maze:
        ldx     cur_maze
        lda     mazemap_lo-1,x
        sta     PTR
        lda     mazemap_hi-1,x
        sta     PTR+1
        lda     #<dots
        sta     PTR2
        lda     #>dots
        sta     PTR2+1
        lda     #0
        sta     dots_left
        sta     dots_left+1
        ldx     #175            ; 700 cells / 4 per byte
up1:    ldy     #0
        lda     (PTR),y
        sta     mtmp
up2:    lda     mtmp
        and     #3
        sta     (PTR2),y
        cmp     #1              ; a dot?
        bne     up3
        inc     dots_left
        bne     up3
        inc     dots_left+1
up3:    lsr     mtmp
        lsr     mtmp
        iny
        cpy     #4
        bne     up2
        inc     PTR
        bne     up4
        inc     PTR+1
up4:    lda     PTR2
        clc
        adc     #4
        sta     PTR2
        bcc     up5
        inc     PTR2+1
up5:    dex
        bne     up1
        rts

; ---- draw_maze: render dots[] to the screen in the style in mstyle ----
; mstyle: 0 = line-and-arc walls, 1 = checkerboard fill, 2 = solid fill.
; Neighbour reads use a 3-row window (prev/cur/next) copied to BSS so only
; the two verified-free zp pointers are needed. Off-screen counts as open,
; which turns the outer border into clean lines and rounded corners.
draw_maze:
        lda     #0
        sta     mrow
dmrow:  lda     mrow            ; window: prev / cur / next rows
        sec
        sbc     #1
        ldx     #<rowbuf_p
        ldy     #>rowbuf_p
        jsr     copy_cells
        lda     mrow
        ldx     #<rowbuf_c
        ldy     #>rowbuf_c
        jsr     copy_cells
        lda     mrow
        clc
        adc     #1
        ldx     #<rowbuf_n
        ldy     #>rowbuf_n
        jsr     copy_cells
        ldx     mrow            ; PTR2 = screen row base
        lda     rowscr_lo,x
        sta     PTR2
        lda     rowscr_hi,x
        sta     PTR2+1
        ldy     #0
dmcol:  lda     rowbuf_c,y
        cmp     #3
        beq     dmwall
        cmp     #1
        beq     dmdot
        cmp     #2
        beq     dmener
        lda     mrow            ; open: the door cells draw as a lintel
        cmp     #10
        bne     dmspace
        cpy     #13
        beq     dmdoor
        cpy     #14
        beq     dmdoor
dmspace:lda     #G_SPACE
        jmp     dmput
dmdoor: lda     #G_HLINE
        jmp     dmput
dmdot:  lda     #G_DOT
        jmp     dmput
dmener: lda     #G_BALL
        jmp     dmput
dmwall: lda     mstyle
        beq     dmline
        cmp     #3
        beq     dmline
        cmp     #1
        beq     dmchk
        lda     #G_SOLID
        jmp     dmput
dmchk:  lda     #G_CHECK
        jmp     dmput
; Line style draws wall PERIMETERS: a link toward a neighbouring wall cell
; is drawn only when the shared edge borders something open (corridor or
; off-screen), so slab interiors stay hollow instead of rendering as grids.
; mask: N=1 W=2 S=4 E=8. Buffers hold OPEN for off-screen rows already.
dmline: lda     #0
        sta     mtmp
        ; --- N link: neighbour rowbuf_p[y]; sides p/c at y-1 and y+1 ---
        lda     rowbuf_p,y
        cmp     #3
        bne     dmn0
        cpy     #0
        beq     dmn1
        cpy     #27
        beq     dmn1
        lda     rowbuf_p-1,y
        cmp     #3
        bne     dmn1
        lda     rowbuf_c-1,y
        cmp     #3
        bne     dmn1
        lda     rowbuf_p+1,y
        cmp     #3
        bne     dmn1
        lda     rowbuf_c+1,y
        cmp     #3
        beq     dmn0            ; fully interior: skip
dmn1:   inc     mtmp            ; N bit
dmn0:   ; --- S link: neighbour rowbuf_n[y]; sides n/c at y-1 and y+1 ---
        lda     rowbuf_n,y
        cmp     #3
        bne     dms0
        cpy     #0
        beq     dms1
        cpy     #27
        beq     dms1
        lda     rowbuf_n-1,y
        cmp     #3
        bne     dms1
        lda     rowbuf_c-1,y
        cmp     #3
        bne     dms1
        lda     rowbuf_n+1,y
        cmp     #3
        bne     dms1
        lda     rowbuf_c+1,y
        cmp     #3
        beq     dms0
dms1:   lda     mtmp
        ora     #4              ; S bit
        sta     mtmp
dms0:   ; --- W link: neighbour c[y-1]; sides p and n at y-1 and y ---
        cpy     #0
        beq     dmw0
        lda     rowbuf_c-1,y
        cmp     #3
        bne     dmw0
        lda     rowbuf_p-1,y
        cmp     #3
        bne     dmw1
        lda     rowbuf_p,y
        cmp     #3
        bne     dmw1
        lda     rowbuf_n-1,y
        cmp     #3
        bne     dmw1
        lda     rowbuf_n,y
        cmp     #3
        beq     dmw0
dmw1:   lda     mtmp
        ora     #2              ; W bit
        sta     mtmp
dmw0:   ; --- E link: neighbour c[y+1]; sides p and n at y and y+1 ---
        cpy     #27
        beq     dme0
        lda     rowbuf_c+1,y
        cmp     #3
        bne     dme0
        lda     rowbuf_p,y
        cmp     #3
        bne     dme1
        lda     rowbuf_p+1,y
        cmp     #3
        bne     dme1
        lda     rowbuf_n,y
        cmp     #3
        bne     dme1
        lda     rowbuf_n+1,y
        cmp     #3
        beq     dme0
dme1:   lda     mtmp
        ora     #8              ; E bit
        sta     mtmp
dme0:   ldx     mtmp
        lda     mstyle
        cmp     #3
        beq     dmsh
        lda     wglyphs,x
        jmp     dmput
dmsh:   lda     wglyphs2,x
dmput:  sta     (PTR2),y
        iny
        cpy     #MAZE_W
        beq     :+
        jmp     dmcol
:       inc     mrow
        lda     mrow
        cmp     #MAZE_H
        beq     :+
        jmp     dmrow
:       rts

; copy_cells: A = maze row (may be -1/25: fills OPEN), X/Y = dest lo/hi
copy_cells:
        sta     mtmp
        stx     PTR
        sty     PTR+1
        lda     mtmp
        bmi     ccfill
        cmp     #MAZE_H
        bcs     ccfill
        tax                     ; PTR2 = dots + row*28
        lda     m28_lo,x
        clc
        adc     #<dots
        sta     PTR2
        lda     m28_hi,x
        adc     #>dots
        sta     PTR2+1
        ldy     #MAZE_W-1
cc1:    lda     (PTR2),y
        sta     (PTR),y
        dey
        bpl     cc1
        rts
ccfill: lda     #0
        ldy     #MAZE_W-1
cc2:    sta     (PTR),y
        dey
        bpl     cc2
        rts

        .segment "RODATA"
; wall glyph by adjacency mask (N=1 W=2 S=4 E=8), line-and-arc style
wglyphs: .byte  G_SPACE, G_VLINE, G_HLINE, G_ARC_LR
         .byte  G_VLINE, G_VLINE, G_ARC_UR, G_TEE_L
         .byte  G_HLINE, G_ARC_LL, G_HLINE, G_TEE_U
         .byte  G_ARC_UL, G_TEE_R, G_TEE_D, G_CROSS

bmaze_tbl: .byte 1,1, 2,2,2, 3,3,3,3, 4,4,4,4, 3,3,3,3, 4,4,4,4
mazemap_lo: .byte <maze1_map, <maze2_map, <maze3_map, <maze4_map
mazemap_hi: .byte >maze1_map, >maze2_map, >maze3_map, >maze4_map
mstyletbl:  .byte 0, 2, 1, 3    ; line / solid / checker / sharp-line
tun_a:      .byte 6, 1, 7, 10   ; tunnel rows per maze ($FF = none)
tun_b:      .byte 14, 19, $FF, 13
mdots_tbl:  .byte MAZE1_DOTS, MAZE2_DOTS, MAZE3_DOTS, MAZE4_DOTS
mf1left_tbl:.byte MAZE1_DOTS-MAZE1_FRUIT1_EATEN, MAZE2_DOTS-MAZE2_FRUIT1_EATEN
            .byte MAZE3_DOTS-MAZE3_FRUIT1_EATEN, MAZE4_DOTS-MAZE4_FRUIT1_EATEN
mf2_tbl:    .byte MAZE1_FRUIT2_LEFT, MAZE2_FRUIT2_LEFT
            .byte MAZE3_FRUIT2_LEFT, MAZE4_FRUIT2_LEFT
fpaths_lo:  .byte <fruit1_paths, <fruit2_paths, <fruit3_paths, <fruit4_paths
fpaths_hi:  .byte >fruit1_paths, >fruit2_paths, >fruit3_paths, >fruit4_paths
fnmouth:    .byte FRUIT1_NMOUTH, FRUIT2_NMOUTH, FRUIT3_NMOUTH, FRUIT4_NMOUTH
; sharp-cornered variant of the wall glyphs (style 3)
wglyphs2: .byte G_SPACE, G_VLINE, G_HLINE, G_CORN_LR
          .byte G_VLINE, G_VLINE, G_CORN_UR, G_TEE_L
          .byte G_HLINE, G_CORN_LL, G_HLINE, G_TEE_U
          .byte G_CORN_UL, G_TEE_R, G_TEE_D, G_CROSS

; row*28 into dots[] and row*40 into screen RAM
m28_lo:  .repeat MAZE_H, r
         .byte  <(r*28)
         .endrepeat
m28_hi:  .repeat MAZE_H, r
         .byte  >(r*28)
         .endrepeat
rowscr_lo: .repeat MAZE_H, r
         .byte  <(SCREEN + r*40)
         .endrepeat
rowscr_hi: .repeat MAZE_H, r
         .byte  >(SCREEN + r*40)
         .endrepeat

        .include "mapdata.inc"

        .segment "BSS"
dots:      .res 700             ; working cell array, row-major 28x25
dots_left: .res 2
mrow:      .res 1
cur_maze:  .res 1
mtmp:      .res 1
mstyle:    .res 1
rowbuf_p:  .res 28
rowbuf_c:  .res 28
rowbuf_n:  .res 28
