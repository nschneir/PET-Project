; engine.s — the half-cell actor engine (spec §4). HOT PATH.
;
; Actors live on a 56x50 grid (2x the 28x25 cell grid). Even coordinate =
; centred in a cell (drawn as aglyph); odd = straddling two cells (drawn as
; a fused half-block pair; arev swaps the pair for reverse-video actors).
; Only one coordinate can be odd (4-way movement, turns at centres only).
;
; Per jiffy, step_actor adds the actor's speed fraction to its accumulator;
; a carry advances one half-cell. Speeds are 8-bit fractions of a half-cell
; per jiffy: arcade 100% = $50 (18.75 half-cells/s; 28 cells in ~3.0 s,
; matching the arcade's tile rate on our identical 28-cell width).
;
; Actor indices: 0 Ms. Muncher, 1 Bruiser, 2 Pixie, 3 Ivy, 4 Sable,
; 5 fruit, 6 Mr. Muncher (cutscenes).

NACT    = 8                     ; array stride (7 used)
DIR_UP    = 0
DIR_LEFT  = 1
DIR_DOWN  = 2
DIR_RIGHT = 3
DIR_NONE  = 4                   ; parked: step_actor still ticks, never moves

        .segment "CODE"         ; (the previous include ends inside BSS)

; ---- init_actors: zero the actor arrays (BSS is not auto-cleared) ----
init_actors:
        ldx     #NACT-1
        lda     #0
ia1:    sta     aacc,x
        sta     apause,x
        sta     ahid,x
        sta     asvn,x
        sta     arev,x
        sta     aspd,x
        lda     #DIR_NONE
        sta     adir,x
        lda     #0
        dex
        bpl     ia1
        rts

; ---- step_actor: X = actor. One accumulator tick; move on overflow ----
step_actor:
        lda     apause,x        ; stall (dot/energizer chew, freeze effects)
        beq     sp0
        dec     apause,x
        rts
sp0:    lda     aacc,x
        clc
        adc     aspd,x
        sta     aacc,x
        bcs     sa1
        rts                     ; no half-cell earned this jiffy
sa1:    lda     adir,x
        cmp     #DIR_NONE
        bne     sa2
        rts                     ; parked
sa2:    lda     ahid,x          ; hidden in the tunnel void?
        beq     sa3
        dec     ahid,x
        bne     sa_done
        jmp     draw_blob       ; emerge at the pre-set far side
sa3:    lda     ax,x
        ora     ay,x
        and     #1
        bne     sa_move         ; mid-step: completion was pre-validated
        jsr     canmove         ; C set = blocked by wall/door
        bcc     sa_entry
        rts                     ; blocked at centre; steering decides later
sa_entry:                       ; tunnel mouth exit? (centre col 0/27)
        lda     ax,x
        bne     sa4
        lda     adir,x
        cmp     #DIR_LEFT
        bne     sa_move
        jsr     erase_blob      ; vanish into the left void
        lda     #54             ; re-appear at col 27 centre, 4 steps later
        sta     ax,x
        lda     #4
        sta     ahid,x
        rts
sa4:    cmp     #54
        bne     sa_move
        lda     adir,x
        cmp     #DIR_RIGHT
        bne     sa_move
        jsr     erase_blob
        lda     #0
        sta     ax,x
        lda     #4
        sta     ahid,x
        rts
sa_move:jmp     force_step
sa_done:rts

; ---- force_step: X = actor. Unconditionally advance one half-cell in
; adir and redraw. Callers must have validated the move. ----
force_step:
        jsr     erase_blob
        ldy     adir,x
        lda     ax,x
        clc
        adc     dxtbl,y
        sta     ax,x
        lda     ay,x
        clc
        adc     dytbl,y
        sta     ay,x
        jmp     draw_blob

; ---- canmove: X = actor. C clear if the cell ahead of adir is enterable.
; From a centre only. Tunnel exits are always enterable. The player (actor
; 0) is additionally blocked by the ghost-house door (spec §5).
canmove:
        ldy     adir,x
; canmove_dir: like canmove but tests the direction in Y (steering probes)
canmove_dir:
        lda     ax,x
        lsr
        sta     etx             ; cell x
        lda     ay,x
        lsr
        sta     ety             ; cell y
        lda     etx
        clc
        adc     dxtbl2,y        ; whole-cell delta
        sta     etx
        cmp     #MAZE_W         ; wrapped past either edge? ($FF or 28)
        bcc     cm1
        clc                     ; off-screen: tunnel — enterable
        rts
cm1:    lda     ety
        clc
        adc     dytbl2,y
        sta     ety
        cpx     #0              ; the player may not use the door
        bne     cm2
        cmp     #10
        bne     cm2
        lda     etx
        cmp     #13
        beq     cmblk
        cmp     #14
        beq     cmblk
cm2:    ldy     ety             ; cell lookup: dots[ety*28 + etx]
        lda     m28_lo,y
        clc
        adc     #<dots
        sta     PTR
        lda     m28_hi,y
        adc     #>dots
        sta     PTR+1
        ldy     etx
        lda     (PTR),y
        cmp     #3
        beq     cmblk
        clc
        rts
cmblk:  sec
        rts

; ---- draw_blob: X = actor. Save-under then draw at (ax,ay) ----
draw_blob:
        lda     ax,x
        sta     asvx,x          ; remember where we drew, for erase
        lda     ay,x
        sta     asvy,x
        and     #1
        bne     db_v
        lda     ax,x
        and     #1
        bne     db_h
        ; centre: one cell
        jsr     blob_addr       ; PTR2 = screen cell, Y = col
        lda     (PTR2),y
        sta     asave0,x
        lda     aglyph,x
        sta     (PTR2),y
        lda     #1
        sta     asvn,x
        rts
db_h:   jsr     blob_addr       ; PTR2/Y = left cell of the straddle
        lda     (PTR2),y
        sta     asave0,x
        iny
        lda     (PTR2),y
        sta     asave1,x
        dey
        lda     #2
        sta     asvn,x
        lda     arev,x
        bne     dbhr
        lda     #G_HALF_R       ; body centred on the cell boundary
        sta     (PTR2),y
        iny
        lda     #G_HALF_L
        sta     (PTR2),y
        rts
dbhr:   lda     #G_HALF_L       ; reverse-video pair (frightened style)
        sta     (PTR2),y
        iny
        lda     #G_HALF_R
        sta     (PTR2),y
        rts
db_v:   jsr     blob_addr       ; PTR2/Y = top cell of the straddle
        lda     (PTR2),y
        sta     asave0,x
        lda     arev,x
        beq     dbv1
        lda     #G_HALF_T       ; reverse-video pair
        bne     dbv2
dbv1:   lda     #G_HALF_B       ; top cell shows the bottom half
dbv2:   sta     (PTR2),y
        lda     PTR2            ; advance one row
        clc
        adc     #40
        sta     PTR2
        bcc     dbv3
        inc     PTR2+1
dbv3:   lda     (PTR2),y
        sta     asave1,x
        lda     arev,x
        beq     dbv4
        lda     #G_HALF_B
        bne     dbv5
dbv4:   lda     #G_HALF_T       ; bottom cell shows the top half
dbv5:   sta     (PTR2),y
        lda     #2
        sta     asvn,x
        rts

; ---- erase_blob: X = actor. Vacated cells are redrawn from the GAME
; STATE (dots[]), never from saved screen bytes: overlapping actors used
; to capture each other's glyphs in the save-under buffers and leave
; orphaned half-blocks behind ("rectangles in the maze"). ----
erase_blob:
        lda     asvn,x
        bne     eb1
        rts                     ; nothing drawn yet
eb1:    lda     ax,x            ; address the SAVED position
        pha
        lda     ay,x
        pha
        lda     asvx,x
        sta     ax,x
        lda     asvy,x
        sta     ay,x
        jsr     blob_addr       ; PTR2/Y = anchor cell
        pla
        sta     ay,x
        pla
        sta     ax,x
        lda     asvx,x
        lsr
        sta     ebcol
        lda     asvy,x
        lsr
        sta     ebrow
        jsr     cell_glyph
        sta     (PTR2),y
        lda     asvn,x
        cmp     #2
        bne     eb_done
        lda     asvy,x
        and     #1
        bne     eb_v
        iny                     ; horizontal partner: next column
        inc     ebcol
        jsr     cell_glyph
        sta     (PTR2),y
        jmp     eb_done
eb_v:   lda     PTR2            ; vertical partner: next row
        clc
        adc     #40
        sta     PTR2
        bcc     eb2
        inc     PTR2+1
eb2:    inc     ebrow
        jsr     cell_glyph
        sta     (PTR2),y
eb_done:lda     #0
        sta     asvn,x
        rts

; ---- cell_glyph: (ebcol, ebrow) -> A = the cell's true glyph. Preserves
; X and Y. Corridor cells only (that is all an actor can vacate). ----
cell_glyph:
        tya
        pha
        lda     ebrow
        tay
        lda     m28_lo,y
        clc
        adc     #<dots
        sta     PTR
        lda     m28_hi,y
        adc     #>dots
        sta     PTR+1
        ldy     ebcol
        lda     (PTR),y
        beq     cg_open
        cmp     #1
        bne     cg_e
        lda     #G_DOT
        bne     cg_out
cg_e:   cmp     #2
        bne     cg_open         ; (3=wall never underlies an actor; treat
        lda     #G_BALL         ;  defensively as open)
        bne     cg_out
cg_open:lda     ebrow           ; the door lintel is state OPEN but drawn
        cmp     #10
        bne     cg_sp
        lda     ebcol
        cmp     #13
        beq     cg_door
        cmp     #14
        beq     cg_door
cg_sp:  lda     #G_SPACE
        bne     cg_out
cg_door:lda     #G_HLINE
cg_out: sta     ebtmp
        pla
        tay
        lda     ebtmp
        rts

; ---- blob_addr: X = actor. PTR2 = screen addr of the anchor cell of the
; CURRENT (ax,ay); Y = column. Anchor = the cell itself at a centre, the
; left/top cell of the pair at a straddle (odd>>1 floors correctly).
blob_addr:
        lda     ay,x
        lsr
        tay
        lda     rowscr_lo,y
        sta     PTR2
        lda     rowscr_hi,y
        sta     PTR2+1
        lda     ax,x
        lsr
        tay
        rts

        .segment "RODATA"
dxtbl:  .byte   0, $FF, 0, 1, 0 ; half-cell deltas by dir (up,left,down,right,none)
dytbl:  .byte   $FF, 0, 1, 0, 0
dxtbl2: .byte   0, $FF, 0, 1, 0 ; whole-cell deltas for canmove
dytbl2: .byte   $FF, 0, 1, 0, 0

        .segment "BSS"
ax:     .res NACT               ; half-cell x (0-55)
ay:     .res NACT               ; half-cell y (0-49)
adir:   .res NACT
aspd:   .res NACT               ; fraction of a half-cell per jiffy
aacc:   .res NACT
aglyph: .res NACT               ; centre glyph
arev:   .res NACT               ; nonzero = reverse-video blob pair
ahid:   .res NACT               ; hidden tunnel steps remaining
apause: .res NACT               ; jiffies to stall before moving again
asvx:   .res NACT               ; where the last draw happened
asvy:   .res NACT
asvn:   .res NACT               ; 0 = nothing to erase, else 1 or 2 cells
asave0: .res NACT               ; (legacy; kept for test pokes)
asave1: .res NACT
etx:    .res 1
ety:    .res 1
ebcol:  .res 1
ebrow:  .res 1
ebtmp:  .res 1
