; sound.s — one CB2 square-wave voice (spec §13). Sequencer ticked once
; per jiffy from the main loop; effects are (period,duration) pair tables
; with a priority scheme. All melodies are ORIGINAL compositions.
;
; Priorities (high wins): death > acts/jingle > ghost > extra > fruit >
; energizer > munch > eyes-hum > fright-warble > siren. The siren tiers
; are the idle layer and restart themselves whenever nothing else plays.

FX_SIREN  = 0                   ; looping idle (tier picked at start)
FX_WARBLE = 1                   ; looping while frightened
FX_HUM    = 2                   ; looping while eyes travel
FX_MUNCH  = 3                   ; per-dot blip, two alternating pitches
FX_ENER   = 4
FX_FRUIT  = 5
FX_GHOST  = 6
FX_EXTRA  = 7
FX_JINGLE = 8
FX_DEATH  = 9
FX_NONE   = $FF

        .segment "CODE"

; ---- snd_init / snd_off ----
snd_init:
        lda     #FX_NONE
        sta     snd_cur
        lda     #0
        sta     munch_alt
snd_off:lda     #0
        sta     SND_T2
        sta     SND_ACR
        rts

; ---- snd_play: A = effect id; starts it if it outranks the current.
; Preserves X (callers are often mid actor loop). ----
snd_play:
        sta     sndtmp
        txa
        pha
        ldy     sndtmp
        lda     snd_cur
        cmp     #FX_NONE
        beq     sp_go
        tax
        lda     prio,y
        cmp     prio,x
        bcc     sp_no           ; lower priority: rejected
sp_go:  sty     snd_cur
        lda     fxoff,y
        sta     snd_ptr         ; byte offset into the shared fxdata blob
        lda     #1              ; fetch the first note on the next tick
        sta     snd_dur
sp_no:  pla
        tax
        rts

; ---- snd_tick: per jiffy — sequence notes, then keep the idle layer on --
snd_tick:
        lda     snd_cur
        cmp     #FX_NONE
        beq     st_idle
        dec     snd_dur
        bne     st_done
        ldy     snd_ptr         ; next (period,duration) pair
        lda     fxdata,y
        bne     st_note
        ; terminator: loops restart, one-shots go quiet
        ldx     snd_cur
        lda     prio,x
        cmp     #4              ; the idle layer (prio 1-3) loops
        bcs     st_end
        lda     fxoff,x
        sta     snd_ptr
        tay
        lda     fxdata,y
st_note:sta     SND_T2
        lda     #$10
        sta     SND_ACR
        lda     #$0F            ; square-ish timbre
        sta     SND_SR
        iny
        lda     fxdata,y
        sta     snd_dur
        inc     snd_ptr
        inc     snd_ptr
st_done:rts
st_end: lda     #FX_NONE
        sta     snd_cur
        lda     #0
        sta     SND_T2
        sta     SND_ACR
st_idle:lda     gon             ; idle layer only during live play
        beq     st_done
        lda     game_state
        bne     st_done
        ; desired idle: eyes-hum > fright-warble > siren tier by dots left
        ldx     #FX_HUM
        lda     gstate+1
        cmp     #GST_EYES
        beq     st_want
        lda     gstate+2
        cmp     #GST_EYES
        beq     st_want
        lda     gstate+3
        cmp     #GST_EYES
        beq     st_want
        lda     gstate+4
        cmp     #GST_EYES
        beq     st_want
        ldx     #FX_WARBLE
        lda     frite_t
        ora     frite_t+1
        bne     st_want
        ldx     #FX_SIREN
st_want:cpx     snd_cur
        beq     st_done
        lda     snd_cur         ; only replace silence or another idle
        cmp     #FX_NONE
        beq     st_sw
        tay
        lda     prio,y
        cmp     #4              ; only silence or another idle layer yields
        bcs     st_done
st_sw:  cpx     #FX_SIREN
        bne     st_sw2
        jsr     siren_pick      ; tier offset by dots remaining
        jmp     st_sw3
st_sw2: lda     fxoff,x
        sta     snd_ptr
st_sw3: stx     snd_cur
        lda     #1
        sta     snd_dur
        rts

; siren_pick: snd_ptr = siren1/2/3 offset by thirds of the board's dots
siren_pick:
        lda     dots_left+1
        bne     sk1             ; plenty left
        lda     dots_left
        cmp     #60
        bcc     sk3
        cmp     #120
        bcc     sk2
sk1:    lda     #t_siren1 - fxdata
        sta     snd_ptr
        rts
sk2:    lda     #t_siren2 - fxdata
        sta     snd_ptr
        rts
sk3:    lda     #t_siren3 - fxdata
        sta     snd_ptr
        rts

; snd_munch: the waka blip, alternating between two pitches
snd_munch:
        lda     munch_alt
        eor     #1
        sta     munch_alt
        bne     sm1
        lda     #FX_MUNCH
        jmp     snd_play
sm1:    ldy     #FX_MUNCH       ; same id, other table: bypass snd_play's
        lda     snd_cur         ; table lookup with a manual start
        cmp     #FX_NONE
        beq     sm2
        tax
        lda     prio,y
        cmp     prio,x
        bcc     sm3
sm2:    sty     snd_cur
        lda     #t_munch2 - fxdata
        sta     snd_ptr
        lda     #1
        sta     snd_dur
sm3:    rts

        .segment "RODATA"
prio:   .byte 1, 2, 3, 5, 9, 10, 12, 11, 14, 15
fxoff:  .byte t_siren1-fxdata, t_warble-fxdata, t_hum-fxdata
        .byte t_munch1-fxdata, t_ener-fxdata, t_fruit-fxdata
        .byte t_ghost-fxdata, t_extra-fxdata, t_jingle-fxdata
        .byte t_death-fxdata
; (period, jiffies) pairs, 0-terminated. Original phrases. All tables
; live inside one <256-byte blob so the sequencer indexes with a byte.
fxdata:
t_siren1: .byte 140,6, 120,6, 0
t_siren2: .byte 118,5, 100,5, 0
t_siren3: .byte  98,4,  84,4, 0
t_warble: .byte  88,3,  68,3, 0
t_hum:    .byte 210,8, 196,8, 0
t_munch1: .byte  72,3, 0
t_munch2: .byte  94,3, 0
t_ener:   .byte  62,4,  78,4,  62,4, 0
t_fruit:  .byte  66,3,  54,5, 0
t_ghost:  .byte 112,4,  86,4,  64,6, 0
t_extra:  .byte  92,4,  72,4,  56,4,  44,10, 0
t_jingle: .byte 150,8, 112,8, 94,8, 74,12, 94,6, 74,6, 62,20, 0
t_death:  .byte  78,6,  92,6, 108,6, 128,8, 156,10, 200,16, 0

        .segment "BSS"
snd_cur:.res 1
snd_dur:.res 1
snd_ptr:.res 1                  ; byte offset into fxdata
munch_alt:.res 1
sndtmp: .res 1
