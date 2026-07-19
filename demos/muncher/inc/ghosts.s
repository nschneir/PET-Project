; ghosts.s — Bruiser, Pixie, Ivy, Sable (actors 1-4). HOT PATH.
;
; Spec §7: Ms.-style scatter/chase schedule (random-scatter for Bruiser and
; Pixie, corner targets for Ivy and Sable, reversals at ~7 s and ~25 s, then
; chase effectively forever), arcade targeting rules including Pixie's
; up-quirk, dot-counter/timeout house releases, tunnel slowdown.
;
; Ghost states (gstate): 0 housed, 1 normal, 4 exiting the house.
; (2 frightened and 3 eyes arrive with T7.)

GST_HOUSED = 0
GST_NORM   = 1
GST_FRIGHT = 2
GST_EYES   = 3
GST_EXIT   = 4

GSPD_NORM  = $3C                ; board-1 class: ghosts 75% (T11 tables)
GSPD_TUN   = $20                ; tunnel zone 40%

        .segment "CODE"

; ---- ghost_init: board-start placement (spec §5) ----
ghost_init:
        ldx     #1              ; Bruiser: above the door, heading left
        lda     #27
        sta     ax,x
        lda     #18             ; row 9
        sta     ay,x
        lda     #DIR_LEFT
        sta     adir,x
        lda     #GST_NORM
        sta     gstate,x
        lda     #G_BRUISER
        sta     aglyph,x
        jsr     gh_common
        ldx     #2              ; Pixie: house centre
        lda     #27
        sta     ax,x
        lda     #G_PIXIE
        jsr     gh_house
        ldx     #3              ; Ivy: house left
        lda     #24
        sta     ax,x
        lda     #G_IVY
        jsr     gh_house
        ldx     #4              ; Sable: house right
        lda     #30
        sta     ax,x
        lda     #G_SABLE
        jsr     gh_house
        lda     #0              ; release bookkeeping (board 1 limits; T11)
        sta     gdcnt
        sta     sched_state
        lda     #<420           ; scatter #1: ~7 s to the first reversal
        sta     sched_t
        lda     #>420
        sta     sched_t+1
        lda     #<240           ; 4 s no-dot timeout forces a release
        sta     gtimeout
        lda     #>240
        sta     gtimeout+1
        lda     #1
        sta     gon
        rts

gh_house:
        sta     aglyph,x
        lda     #22             ; house interior row 11
        sta     ay,x
        lda     #GST_HOUSED
        sta     gstate,x
        lda     #DIR_NONE
        sta     adir,x
gh_common:
        lda     #1
        sta     arev,x          ; ghosts render reverse-video
        lda     #GSPD_NORM
        sta     aspd,x
        lda     #0
        sta     aacc,x
        sta     apause,x
        jmp     draw_blob

; ---- ghosts_tick: once per jiffy, after player_tick ----
ghosts_tick:
        lda     gon             ; test hook: 0 freezes the ghost world
        bne     gt0
        lda     #0
        sta     eat_ev
        rts
gt0:    jsr     gh_release
        ldx     #1
gt1:    jsr     ghost_tick
        inx
        cpx     #5
        bne     gt1
        jsr     sched_tick
        lda     #0              ; the eat event is consumed by now
        sta     eat_ev
        rts

; ---- gh_release: house dot counters and the no-dot timeout ----
gh_release:
        ldx     #2              ; preferred = first housed of Pixie,Ivy,Sable
gr1:    lda     gstate,x
        cmp     #GST_HOUSED
        beq     gr2
        inx
        cpx     #5
        bne     gr1
        rts                     ; house is empty
gr2:    lda     eat_ev
        cmp     #1
        bne     gr3
        inc     gdcnt           ; a dot: bump the counter, pet the watchdog
        lda     #<240
        sta     gtimeout
        lda     #>240
        sta     gtimeout+1
gr3:    lda     gdcnt
        cmp     glimit,x        ; enough dots for the preferred ghost?
        bcs     gr_go
        lda     gtimeout        ; or has the no-dot timeout expired?
        bne     gr4
        lda     gtimeout+1
        beq     gr_go
        dec     gtimeout+1
gr4:    dec     gtimeout
        rts
gr_go:  lda     #GST_EXIT       ; release: walk to the door column, then up
        sta     gstate,x
        lda     #0
        sta     gdcnt           ; next ghost counts afresh (close enough to
        lda     #<240           ; the arcade's per-ghost counters)
        sta     gtimeout
        lda     #>240
        sta     gtimeout+1
        rts

; ---- ghost_tick: X = ghost actor ----
ghost_tick:
        lda     gstate,x
        cmp     #GST_HOUSED
        bne     gk1
        rts                     ; sits tight (arcade pacing is cosmetic)
gk1:    cmp     #GST_EXIT
        bne     gk2
        jmp     gh_exit
gk2:    lda     ax,x            ; at a cell centre? decide a direction
        ora     ay,x
        and     #1
        bne     gk3
        jsr     ghost_decide
gk3:    jsr     gh_speed
        jmp     step_actor

; ---- gh_exit: scripted walk out of the house ----
gh_exit:
        lda     #GSPD_NORM
        sta     aspd,x
        lda     ay,x
        cmp     #18             ; reached row 9: outside
        bne     ge1
        lda     ax,x
        and     #1
        bne     ge1
        lda     #GST_NORM       ; free — join the fray heading left
        sta     gstate,x
        lda     #DIR_LEFT
        sta     adir,x
        rts
ge1:    lda     ax,x
        cmp     #26             ; align to door col 13 (or 14 if right of it)
        beq     ge_up
        bcs     ge2
        lda     #DIR_RIGHT      ; left of the door: head right
        sta     adir,x
        jmp     step_actor
ge2:    cmp     #28
        beq     ge_up
        lda     #DIR_LEFT
        sta     adir,x
        jmp     step_actor
ge_up:  lda     #DIR_UP
        sta     adir,x
        jmp     step_actor

; ---- gh_speed: normal vs tunnel-zone speed (fright/eyes come in T7) ----
gh_speed:
        lda     ahid,x          ; hidden in the void: tunnel speed
        bne     gs_tun
        lda     ay,x
        lsr
        cmp     #6              ; maze 1 tunnel rows (T11 generalises)
        beq     gs_row
        cmp     #14
        beq     gs_row
gs_norm:lda     #GSPD_NORM
        sta     aspd,x
        rts
gs_row: lda     ax,x
        lsr
        cmp     #6              ; zone: cols 0-5 and 22-27
        bcc     gs_tun
        cmp     #22
        bcc     gs_norm
gs_tun: lda     #GSPD_TUN
        sta     aspd,x
        rts

; ---- ghost_decide: X = ghost at a centre. Choose adir. ----
ghost_decide:
        lda     #0
        sta     gcn
        ldy     #DIR_UP         ; build candidates in arcade priority order
gd1:    sty     gdir
        lda     adir,x
        tay
        lda     opptbl,y
        cmp     gdir
        beq     gd_next         ; never reverse by choice
        ; door guard: normal/frightened ghosts may not step DOWN into it
        lda     gdir
        cmp     #DIR_DOWN
        bne     gdd
        lda     gstate,x
        cmp     #GST_EYES
        beq     gdd
        lda     ay,x
        lsr
        cmp     #9              ; from row 9...
        bne     gdd
        lda     ax,x
        lsr
        cmp     #13             ; ...into door cols 13/14
        beq     gd_next
        cmp     #14
        beq     gd_next
gdd:    ldy     gdir
        jsr     canmove_dir
        bcs     gd_next
        ldy     gcn             ; open: append
        lda     gdir
        sta     gcand,y
        inc     gcn
gd_next:ldy     gdir
        iny
        cpy     #4
        bne     gd1
        lda     gcn
        bne     gd3
        lda     adir,x          ; boxed in: forced reverse
        tay
        lda     opptbl,y
        sta     adir,x
        rts
gd3:    cmp     #1
        bne     gd4
        lda     gcand           ; corridor: the only way on
        sta     adir,x
        rts
gd4:    ; a junction: random for frightened, and for Bruiser/Pixie during
        ; the scatter windows (the Ms. anti-pattern randomiser)
        lda     gstate,x
        cmp     #GST_FRIGHT
        beq     gd_rand
        lda     sched_state
        and     #1              ; states 0/2 = scatter windows
        bne     gd_tgt
        cpx     #3
        bcs     gd_tgt          ; Ivy/Sable still corner-target in scatter
gd_rand:jsr     lfsr
        and     #3
gdr1:   cmp     gcn
        bcc     gdr2
        sec
        sbc     gcn
        jmp     gdr1
gdr2:   tay
        lda     gcand,y
        sta     adir,x
        rts
gd_tgt: jsr     calc_target     ; -> ttx/tty
        lda     #$FF
        sta     gbest
        sta     gbest+1
        ldy     #0
gt2:    sty     gci
        lda     gcand,y         ; candidate: distance^2 from the next cell
        tay
        lda     ax,x
        lsr
        clc
        adc     dxtbl2,y
        sta     etx
        lda     ay,x
        lsr
        clc
        adc     dytbl2,y
        sta     ety
        ; dx = |ttx - etx| (etx can be $FF/28 through a tunnel mouth: fine,
        ; the wrap candidate scores as far away, which the arcade also
        ; effectively does at mouths)
        lda     ttx
        sec
        sbc     etx
        bpl     gt3
        eor     #$FF
        adc     #1
gt3:    and     #$1F
        tay
        lda     sqtbl_lo,y
        sta     gd2
        lda     sqtbl_hi,y
        sta     gd2+1
        lda     tty
        sec
        sbc     ety
        bpl     gt4
        eor     #$FF
        adc     #1
gt4:    and     #$1F
        tay
        lda     gd2
        clc
        adc     sqtbl_lo,y
        sta     gd2
        lda     gd2+1
        adc     sqtbl_hi,y
        sta     gd2+1
        ; strict less-than keeps the first (highest-priority) on ties
        lda     gd2+1
        cmp     gbest+1
        bcc     gt_new
        bne     gt_old
        lda     gd2
        cmp     gbest
        bcs     gt_old
gt_new: lda     gd2
        sta     gbest
        lda     gd2+1
        sta     gbest+1
        ldy     gci
        lda     gcand,y
        sta     gpick
gt_old: ldy     gci
        iny
        cpy     gcn
        beq     :+
        jmp     gt2
:       lda     gpick
        sta     adir,x
        rts

; ---- calc_target: X = ghost. Chase/scatter target -> ttx/tty ----
calc_target:
        lda     sched_state
        and     #1
        bne     ct_chase
        cpx     #3              ; scatter: Ivy/Sable head for their corners
        bne     ct_sable_sc
        lda     #26
        sta     ttx
        lda     #23
        sta     tty
        rts
ct_sable_sc:
        cpx     #4
        bne     ct_chase        ; (Bruiser/Pixie never get here: randomised)
        lda     #1
        sta     ttx
        lda     #23
        sta     tty
        rts
ct_chase:
        lda     ax              ; player cell
        lsr
        sta     ttx
        lda     ay
        lsr
        sta     tty
        lda     ax+1            ; Bruiser's cell (Ivy's vector base)
        lsr
        sta     gbx
        lda     ay+1
        lsr
        sta     gby
        cpx     #1
        bne     ct2
        rts                     ; Bruiser: her cell, done
ct2:    cpx     #4
        bne     ct3
        ; Sable: her cell if further than 8 cells (d^2 > 64), else corner
        lda     ax,x
        lsr
        sec
        sbc     ttx
        bpl     ct41
        eor     #$FF
        adc     #1
ct41:   and     #$1F
        tay
        lda     sqtbl_lo,y
        sta     gd2
        lda     sqtbl_hi,y
        sta     gd2+1
        lda     ay,x
        lsr
        sec
        sbc     tty
        bpl     ct42
        eor     #$FF
        adc     #1
ct42:   and     #$1F
        tay
        lda     gd2
        clc
        adc     sqtbl_lo,y
        sta     gd2
        lda     gd2+1
        adc     sqtbl_hi,y
        bne     ct_far          ; high byte set: > 255 >> 64
        lda     gd2
        cmp     #65
        bcs     ct_far
        lda     #1              ; near: retreat target = home corner
        sta     ttx
        lda     #23
        sta     tty
ct_far: rts
ct3:    ; Pixie (n=4) / Ivy (n=2): n cells ahead, with the arcade up-quirk
        ; (facing up also shifts n left)
        lda     #4
        cpx     #2
        beq     ct5
        lda     #2
ct5:    sta     gnn
        ldy     adir            ; player's facing
        cpy     #DIR_UP
        bne     ct6
        lda     ttx             ; quirk: up also pulls the target left
        sec
        sbc     gnn
        sta     ttx
        lda     tty
        sec
        sbc     gnn
        sta     tty
        jmp     ct7
ct6:    lda     dxtbl2,y        ; +/-1 or 0
        beq     ct61
        bmi     ct62
        lda     ttx
        clc
        adc     gnn
        sta     ttx
        jmp     ct61
ct62:   lda     ttx
        sec
        sbc     gnn
        sta     ttx
ct61:   lda     dytbl2,y
        beq     ct7
        bmi     ct63
        lda     tty
        clc
        adc     gnn
        sta     tty
        jmp     ct7
ct63:   lda     tty
        sec
        sbc     gnn
        sta     tty
ct7:    cpx     #3
        beq     ct8
        jmp     ct_clamp        ; Pixie: done (clamped below)
ct8:    ; Ivy: double the vector from Bruiser to the intermediate point
        lda     ttx
        asl
        sec
        sbc     gbx             ; caller pre-loads Bruiser's cell? no —
        sta     ttx             ; compute here:
        lda     tty
        asl
        sec
        sbc     gby
        sta     tty
ct_clamp:                       ; clamp signed results into the maze
        lda     ttx
        bpl     cl1
        lda     #0
        sta     ttx
cl1:    lda     ttx
        cmp     #MAZE_W
        bcc     cl2
        lda     #MAZE_W-1
        sta     ttx
cl2:    lda     tty
        bpl     cl3
        lda     #0
        sta     tty
cl3:    lda     tty
        cmp     #MAZE_H
        bcc     cl4
        lda     #MAZE_H-1
        sta     tty
cl4:    rts

; ---- sched_tick: the scatter/chase clock (paused while frightened, T7) --
sched_tick:
        lda     sched_state
        cmp     #3
        beq     sc_slow         ; permanent chase: a ~17-minute idle timer
        lda     sched_t
        bne     sc1
        lda     sched_t+1
        beq     sc_adv
        dec     sched_t+1
sc1:    dec     sched_t
        rts
sc_slow:lda     sched_t         ; state 3 just reloads itself on expiry
        bne     sc1
        lda     sched_t+1
        bne     sc1
sc_adv: inc     sched_state
        lda     sched_state
        cmp     #4
        bcc     sc2
        lda     #3
        sta     sched_state
sc2:    tay                     ; note: Y = new state (1..3)
        lda     schedlo-1,y
        sta     sched_t
        lda     schedhi-1,y
        sta     sched_t+1
        jmp     rev_all

; ---- rev_all: every active ghost reverses (schedule edges, energizers) --
rev_all:
        txa
        pha
        ldx     #1
rv1:    lda     gstate,x
        cmp     #GST_NORM
        beq     rv2
        cmp     #GST_FRIGHT
        bne     rv3
rv2:    lda     adir,x
        tay
        lda     opptbl,y
        sta     adir,x
rv3:    inx
        cpx     #5
        bne     rv1
        pla
        tax
        rts

; ---- lfsr: 16-bit xorshift step; returns A (never all-zero) ----
lfsr:   lda     rng
        asl
        rol     rng+1
        bcc     lf1
        eor     #$2D            ; x^16 + x^14 + x^13 + x^11 taps
lf1:    sta     rng
        eor     rng+1
        rts

        .segment "RODATA"
; ghost glyphs: reverse-video initials
G_BRUISER = 2+128
G_PIXIE   = 16+128
G_IVY     = 9+128
G_SABLE   = 19+128
glimit:  .byte 0, 0, 0, 30, 60  ; house dot limits (board 1; index=actor)
schedlo: .byte <1200, <300, <61200  ; chase1 20s, scatter2 5s, "forever"
schedhi: .byte >1200, >300, >61200
sqtbl_lo: .repeat 32, n
          .byte <(n*n)
          .endrepeat
sqtbl_hi: .repeat 32, n
          .byte >(n*n)
          .endrepeat

        .segment "BSS"
gstate: .res NACT
gon:    .res 1                  ; ghost world enable (tests park it)
gdcnt:  .res 1                  ; dots counted for the preferred captive
gtimeout:.res 2
sched_state:.res 1              ; 0 scat1, 1 chase1, 2 scat2, 3 chase-ever
sched_t:.res 2
rng:    .res 2
gcand:  .res 4
gcn:    .res 1
gdir:   .res 1
gci:    .res 1
gd2:    .res 2
gbest:  .res 2
gpick:  .res 1
ttx:    .res 1
tty:    .res 1
gnn:    .res 1
gbx:    .res 1                  ; Bruiser's cell (for Ivy), set per decide
gby:    .res 1
