; mazes.s — unpack packed 2-bit maps into the working dot array and draw
; the maze with per-style wall glyphs. Not hot-path: runs at board start.
;
; Cell codes in dots[]: 0 open, 1 dot, 2 energizer, 3 wall (mazecheck.py).
; House door cells (13,10)/(14,10) pack as open; drawn as G_HLINE.

; ---- unpack_maze: current maze's packed map -> dots[], counts dots_left ----
; (maze selection lands in T11; maze 1 hardwired until then)
unpack_maze:
        lda     #<maze1_map
        sta     PTR
        lda     #>maze1_map
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
        lda     wglyphs,x
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
mtmp:      .res 1
mstyle:    .res 1
rowbuf_p:  .res 28
rowbuf_c:  .res 28
rowbuf_n:  .res 28
