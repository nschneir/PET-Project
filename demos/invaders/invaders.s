; invaders.s — Invaders (a Space Invaders recreation) for the Commodore PET 4032 (40x25).
; Pure 6502 with a BASIC SYS stub. Screen at $8000, jiffy-paced (60 Hz),
; one-alien-per-tick march engine, CB2 sound. See AUDIT.md for fidelity log.

CHROUT  = $FFD2
GETIN   = $FFE4
JIFFLO  = $8F                   ; jiffy clock low byte (60 Hz)
KEYDOWN = $97                   ; PETSCII of the key held right now ($FF none)

PTR     = $FB                   ; zero-page pointer (plot target)
PTR2    = $FD                   ; zero-page pointer (text source)

; --- screen layout ---
HUDROW    = 0
UFOROW    = 1
SHIELDROW = 19                  ; shields occupy rows 19-20
BASEROW   = 23
LIVESROW  = 24

; --- glyphs (screen codes) ---
CH_SPACE  = 32
CH_BASE_L = 108                 ; lower-right quadrant
CH_BASE_M = 98                  ; lower half block
CH_BASE_R = 123                 ; lower-left quadrant
CH_SHIELD1= 160                 ; solid block (reverse space)
CH_SHIELD2= 102                 ; checkerboard
CH_SHOT   = 30                  ; up arrow
CH_BOMB0  = 33                  ; slow straight bomb '!'
CH_BOMB1  = 93                  ; fast straight bomb (thin vertical bar)
CH_WIG1   = 77                  ; wiggly bomb ╲
CH_WIG2   = 78                  ; wiggly bomb ╱
CH_UFO_L  = 60                  ; the mystery saucer wears <=>
CH_UFO_M  = 61
CH_UFO_R  = 62
UFOPERIOD = 1500                ; ticks between saucer visits (~25 s)

; VIA CB2 sound — the PET's one voice
SND_ACR = $E84B                 ; $10 = shift register free-runs under T2
SND_SR  = $E84A                 ; the shifted bit pattern (timbre)
SND_T2  = $E848                 ; shift period = pitch (0 = silent)

; effect ids, lowest priority first
FX_HB     = 0                   ; heartbeat note (per march sweep)
FX_UFO    = 1                   ; saucer warble (loops while it flies)
FX_SHOT   = 2                   ; player shot zap
FX_HIT    = 3                   ; invader crunch
FX_UFOHIT = 4                   ; saucer explosion
FX_EXPL   = 5                   ; player explosion outranks everything

; --------------------------------------------------------------------------
        .segment "LOADADDR"
        .word   $0401
        .segment "EXEHDR"
        .word   nextln
        .word   10
        .byte   $9E, "1037", $00
nextln: .word   $0000

        .segment "CODE"
start:  cld
        lda     #0
        sta     hiscore
        sta     hiscore+1
        sta     score           ; the title draws these before any game runs
        sta     score+1
        lda     #1
        sta     wave

; ------------------------- attract / title --------------------------------
title:  jsr     sndoff
        jsr     titlescreen
        lda     #0
        sta     $9E             ; flush type-ahead
tloop:  jsr     GETIN           ; buffered keys are fine outside play
        beq     tloop
        jsr     newgame

; ---------------------------- main loop -----------------------------------
; $97 holds the PETSCII of the key currently down ($FF = none) — the IRQ
; scanner decodes through the ROM table at $E73E. Read it FIRST each tick so
; the debugger's poke-$97-then-step protocol sees its value before the next
; IRQ rewrites it.
KEY_A  = $41
KEY_D  = $44
KEY_SP = $20

tick:                           ; ONE game tick per jiffy; frame-step anchor
        lda     deathT
        bne     dying           ; player explosion freezes the world
        jsr     input
        jsr     shotmove
        jsr     bombmove
        jsr     march
        jsr     bombdrop
        jsr     ufotick
        jsr     popuptick
        jsr     snddrv
        lda     invaded
        bne     gameover        ; an alien reached the baseline
        lda     aliveN
        beq     wavedone        ; rack cleared
        jsr     pace
        jmp     tick

wavedone:
        inc     wave
        jsr     setfield        ; fresh shields + rack one row lower (2-9)
        jmp     tick

; --- player death: ~1s freeze, then respawn at the left or game over ------
dying:  dec     deathT
        bne     dpace
        lda     lives           ; freeze over: pay the life
        beq     gameover
        dec     lives
        beq     gameover        ; that was the last one
        jsr     drawlives
        lda     #BASEROW        ; clear the wreck
        ldy     basex
        jsr     plotaddr
        lda     #CH_SPACE
        ldy     #2
:       sta     (PTR),y
        dey
        bpl     :-
        lda     #2              ; respawn at the left, like the arcade
        sta     basex
        jsr     drawbase
        jsr     clearfx
        lda     #60             ; a breath of grace after each death
        sta     bombTmr
dpace:  jsr     snddrv          ; the explosion rumble plays through the freeze
        jsr     pace
        jmp     tick

; playerhit: a bomb reached the base — start the explosion freeze
playerhit:
        ldx     #FX_EXPL        ; the player's own end outranks everything
        jsr     sndfx
        lda     #60
        sta     deathT
        lda     #BASEROW        ; wreck glyphs over the base
        ldy     basex
        jsr     plotaddr
        lda     #42
        ldy     #2
:       sta     (PTR),y
        dey
        bpl     :-
        rts

gameover:
        lda     score+1         ; hiscore = max(hiscore, score)
        cmp     hiscore+1
        bcc     gonohi
        bne     gohi
        lda     score
        cmp     hiscore
        bcc     gonohi
gohi:   lda     score
        sta     hiscore
        lda     score+1
        sta     hiscore+1
        jsr     drawhi
gonohi: jsr     sndoff          ; leave the voice clean
        lda     #<gotxt
        ldx     #>gotxt
        jsr     settext
        lda     #12
        ldy     #15
        jsr     drawtext
        ldx     #180            ; let it sink in (~3 s), then attract again
gop:    jsr     pace
        dex
        bne     gop
        jmp     title

pace:   lda     JIFFLO
pw:     cmp     JIFFLO
        beq     pw              ; wait for the jiffy clock to advance
        rts

; kill all in-flight ordnance AND lift its pixels (the respawn path keeps
; the playfield, so flags alone would leave stale glyphs — a stray <=> could
; even be shot for ghost points)
clearfx:
        lda     shotA
        beq     cf1
        lda     shotY
        ldy     shotX
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     #CH_SHOT
        bne     cf1
        lda     #CH_SPACE
        sta     (PTR),y
cf1:    ldx     #2
cf2:    stx     tmp2
        lda     bombA,x
        beq     cf3
        lda     bombG,x
        beq     cf3
        sta     tmp3
        lda     bombY,x
        ldy     bombX,x
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     tmp3
        bne     cf3
        lda     #CH_SPACE
        sta     (PTR),y
cf3:    ldx     tmp2
        dex
        bpl     cf2
        lda     ufoA
        beq     cf4
        jsr     ufoerase
cf4:    lda     popT
        beq     cf5
        lda     #1
        sta     popT
        jsr     popuptick       ; expire the flash through its own eraser
cf5:    lda     #0
        sta     shotA
        sta     bombA
        sta     bombA+1
        sta     bombA+2
        sta     popT
        sta     ufoA
        rts

; ---------------------------- input ---------------------------------------
input:  lda     movetmr
        beq     :+
        dec     movetmr
:       lda     KEYDOWN
        cmp     #KEY_SP
        beq     fire
        cmp     #KEY_A
        beq     mleft
        cmp     #KEY_D
        beq     mright
        rts

fire:   lda     shotA
        bne     inret           ; only one player shot on screen
        inc     shotA
        inc     shotCnt         ; the UFO counts these (8-bit, wraps)
        ldx     #FX_SHOT
        jsr     sndfx
        lda     basex
        clc
        adc     #1              ; muzzle = base centre
        sta     shotX
        lda     #BASEROW-1
        sta     shotY
        ldy     shotX
        ldx     #CH_SHOT
        jmp     putchar

mleft:  lda     movetmr
        bne     inret
        lda     basex
        beq     inret           ; clamp at left wall
        dec     basex
        jsr     drawbase        ; draws 3 cells at the new position...
        lda     #BASEROW
        ldy     basex
        iny
        iny
        iny                     ; ...and blanks the cell vacated on the right
        ldx     #CH_SPACE
        jsr     putchar
        jmp     setmtmr

mright: lda     movetmr
        bne     inret
        lda     basex
        cmp     #37
        bcs     inret           ; clamp at right wall
        inc     basex
        jsr     drawbase
        lda     #BASEROW
        ldy     basex
        dey                     ; blank the cell vacated on the left
        ldx     #CH_SPACE
        jsr     putchar
setmtmr:
        lda     #3              ; base speed: one cell per 3 ticks
        sta     movetmr
inret:  rts

; ---------------------------- game setup ----------------------------------
newgame:
        lda     #3
        sta     lives
        ldx     #GZLEN-1        ; BSS is not in the .prg — zero all dynamic
        lda     #0              ; game state explicitly
gz1:    sta     gzs,x
        dex
        bpl     gz1
        sta     score
        sta     score+1
        lda     #1
        sta     wave
        lda     JIFFLO          ; seed the LFSR (zero is its lock-up point)
        bne     :+
        lda     #$2A
:       sta     seed
        lda     #<UFOPERIOD     ; first saucer visit is a full period out
        sta     ufoTmr
        lda     #>UFOPERIOD
        sta     ufoTmr+1
        lda     #120            ; two seconds of grace before bombs fall
        sta     bombTmr
        ; fall through: set up the wave's field
setfield:
        jsr     clearfx         ; in-flight objects don't cross waves
        lda     #$93
        jsr     CHROUT          ; clear screen (init only — never in the loop)
        jsr     drawhud
        jsr     drawshields
        lda     #18
        sta     basex
        jsr     drawbase
        jsr     initform
        rts

; initform: build and draw the wave's formation. Top row = 2 + (wave-1) mod 9.
initform:
        lda     wave
        sec
        sbc     #1
mod9:   cmp     #9
        bcc     :+
        sbc     #9
        bcs     mod9
:       clc
        adc     #2
        sta     formtop
        lda     #55
        sta     aliveN
        lda     #0
        sta     mcur
        sta     mdrop
        sta     edgeF
        sta     sweepF
        sta     invaded
        lda     #1
        sta     mdx             ; rack opens marching right
        ldx     #54
if1:    lda     #1
        sta     alienA,x
        lda     ROWOF,x
        clc
        adc     formtop
        sta     alienY,x
        lda     COLOF,x
        asl                     ; column pitch 2
        clc
        adc     #9              ; rack starts centred (cols 9-29)
        sta     alienX,x
        dex
        bpl     if1
        ; draw all 55 (setup only — in play the march touches 2 cells/tick)
        ldx     #54
if2:    stx     tmp2
        ldy     ROWOF,x
        lda     GLYA,y
        sta     tmp3
        lda     alienY,x
        ldy     alienX,x
        jsr     plotaddr
        lda     tmp3
        ldy     #0
        sta     (PTR),y
        ldx     tmp2
        dex
        bpl     if2
        rts

; ---------------------------- the march -----------------------------------
; The authentic engine: ONE live alien moves per tick; the cursor sweeps
; index order and skips dead aliens for free, so the rack speeds up
; emergently as it thins. Direction/drop changes latch at sweep wrap.
march:  ldx     mcur
mfind:  cpx     #55
        bcs     mwrap
        lda     alienA,x
        bne     mmove
        inx
        bne     mfind
mwrap:  ldx     hbIdx           ; heartbeat: next of the four descending
        lda     hbtab,x         ; bass notes, once per sweep — the tempo
        pha                     ; quickens exactly as the rack thins
        inx
        txa
        and     #3
        sta     hbIdx
        ldx     #FX_HB
        pla
        jsr     sndfxp
        lda     #0              ; sweep complete: latch pending state
        sta     mcur
        lda     sweepF
        eor     #1
        sta     sweepF          ; all aliens animate as the next sweep runs
        lda     edgeF
        beq     mnodrop
        lda     #0
        sta     edgeF
        lda     #1
        sta     mdrop           ; next sweep: everyone down one row...
        lda     #0
        sec
        sbc     mdx
        sta     mdx             ; ...and the step reverses
        rts
mnodrop:
        lda     #0
        sta     mdrop
        rts
mmove:  stx     tmp2
        lda     alienY,x        ; erase the cell it leaves
        ldy     alienX,x
        jsr     plotaddr
        lda     #CH_SPACE
        ldy     #0
        sta     (PTR),y
        ldx     tmp2
        lda     mdrop
        beq     mside
        inc     alienY,x        ; drop sweep: down one row
        lda     alienY,x
        cmp     #BASEROW
        bcc     mdraw
        lda     #1
        sta     invaded         ; reached the baseline — the wave has landed
        bne     mdraw
mside:  lda     alienX,x
        clc
        adc     mdx
        sta     alienX,x
        beq     medge           ; landed on column 0
        cmp     #39
        bne     mdraw
medge:  lda     #1
        sta     edgeF
mdraw:  ldx     tmp2
        ldy     ROWOF,x
        lda     sweepF
        bne     mfB
        lda     GLYA,y
        bne     mg              ; glyphs are never zero
mfB:    lda     GLYB,y
mg:     sta     tmp3
        lda     alienY,x
        ldy     alienX,x
        jsr     plotaddr
        lda     tmp3
        ldy     #0
        sta     (PTR),y
        ldx     tmp2
        inx
        stx     mcur
        rts

; ---------------------------- player shot ---------------------------------
; One shot on screen; moves up one row per tick. Collision is by reading the
; destination cell's screen code and classifying it.
shotmove:
        lda     shotA
        beq     smret
        lda     shotY           ; erase (unless something drew over us)
        ldy     shotX
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     #CH_SHOT
        bne     :+
        lda     #CH_SPACE
        sta     (PTR),y
:       dec     shotY
        lda     shotY
        bne     :+
        lda     #0              ; reached the HUD row — spend the shot
        sta     shotA
smret:  rts
:       ldy     shotX
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     #CH_SPACE
        beq     smdraw
        cmp     #CH_SHIELD1
        beq     smshield
        cmp     #CH_SHIELD2
        beq     smshield
        cmp     #CH_UFO_L       ; the mystery saucer!
        bcc     :+
        cmp     #CH_UFO_R+1
        bcc     smufo
:       cmp     #CH_BOMB0       ; bomb? the shot and it cancel out
        beq     smbomb
        cmp     #CH_BOMB1
        beq     smbomb
        cmp     #CH_WIG1
        beq     smbomb
        cmp     #CH_WIG2
        beq     smbomb
        ldx     #4              ; alien glyph? (either animation frame)
smg1:   cmp     GLYA,x
        beq     smalien
        cmp     GLYB,x
        beq     smalien
        dex
        bpl     smg1
smdraw: lda     #CH_SHOT        ; empty (or unowned debris): fly on
        sta     (PTR),y
        rts

smbomb: ldx     #2              ; find the bomb that owns this cell
smb1:   lda     bombA,x
        beq     smb2
        lda     bombX,x
        cmp     shotX
        bne     smb2
        lda     bombY,x
        cmp     shotY
        beq     smb3
smb2:   dex
        bpl     smb1
        bmi     smdraw          ; no owner: stale pixel, fly through
smb3:   lda     #0
        sta     bombA,x
        sta     shotA
        lda     #42             ; both die in a little flash
        ldy     shotX
        ldx     shotY
        jmp     popupset

smufo:  lda     ufoA            ; only a live saucer pays out
        beq     smdraw
        lda     #0              ; shot meets saucer
        sta     shotA
        jmp     ufokill

smshield:                       ; erode: solid → checkerboard → gone
        cmp     #CH_SHIELD1
        bne     :+
        lda     #CH_SHIELD2
        .byte   $2C             ; BIT abs — skip the next 2-byte load
:       lda     #CH_SPACE
        sta     (PTR),y
        lda     #0
        sta     shotA
        rts

smalien:                        ; find the alien whose coords match the cell
        ldx     #54
sma1:   lda     alienA,x
        beq     sma2
        lda     alienX,x
        cmp     shotX
        bne     sma2
        lda     alienY,x
        cmp     shotY
        beq     smakill
sma2:   dex
        bpl     sma1
        bmi     smdraw          ; no owner (mid-move artifact): fly through
smakill:
        lda     #0
        sta     alienA,x
        sta     shotA
        dec     aliveN
        lda     ROWOF,x
        tax
        lda     PTS,x
        jsr     addscore
        ldx     #FX_HIT
        jsr     sndfx
        lda     #42             ; '*' explosion flash where it died
        ldy     shotX
        ldx     shotY
        jmp     popupset

; addscore: A = points in units of 10; awards the 1500-point extra life
addscore:
        clc
        adc     score
        sta     score
        bcc     :+
        inc     score+1
:       lda     score+1         ; hold at 99990 — five digits is all the
        cmp     #>9999          ; HUD owns (the arcade rolls at 9999 too)
        bcc     asdraw
        bne     ascap
        lda     score
        cmp     #<9999
        bcc     asdraw
ascap:  lda     #<9999
        sta     score
        lda     #>9999
        sta     score+1
asdraw: jsr     drawscore
        lda     extraF
        bne     asret           ; one bonus base per game, like the arcade
        lda     score+1
        bne     asaward
        lda     score
        cmp     #150            ; 1500 points, in units of ten
        bcc     asret
asaward:
        inc     extraF
        inc     lives
        jsr     drawlives
asret:  rts

; popupset: flash char A at column Y, row X for a few ticks
popupset:
        sta     popB
        sty     popX
        stx     popY
        lda     #1
        sta     popN
        lda     #6
        sta     popT
        bne     popshow

; popshow: draw the popN chars in popB.. at (popX,popY); popT already set
popshow:
        lda     popY
        ldy     popX
        jsr     plotaddr
        ldy     #0
pps1:   lda     popB,y
        sta     (PTR),y
        iny
        cpy     popN
        bcc     pps1
        rts

popuptick:
        lda     popT
        beq     ppret
        dec     popT
        bne     ppret
        lda     popY            ; timer just expired: clear our chars (each
        ldy     popX            ; only if nothing has drawn over it since)
        jsr     plotaddr
        ldy     #0
pp1:    lda     (PTR),y
        cmp     popB,y
        bne     pp2
        lda     #CH_SPACE
        sta     (PTR),y
pp2:    iny
        cpy     popN
        bcc     pp1
ppret:  rts

; ---------------------------- the mystery UFO -----------------------------
; Crosses row 1 left to right every UFOPERIOD ticks. Worth 50-300; the real
; arcade secret: 300 on the player's 23rd shot, then on every 15th after.
ufotick:
        lda     ufoA
        beq     ufidle
        dec     ufoP
        beq     :+
        rts
:       lda     #2
        sta     ufoP            ; one column per two ticks
        jsr     ufoerase
        inc     ufoX
        lda     ufoX
        cmp     #38
        bcc     ufodraw
        lda     #0              ; slipped off the right edge, unpaid
        sta     ufoA
        rts
ufodraw:
        lda     #UFOROW
        ldy     ufoX
        jsr     plotaddr
        ldy     #2
:       lda     (PTR),y
        cmp     #CH_SHOT        ; swept into the player's shot: that's a hit
        beq     ufoshot
        dey
        bpl     :-
        ldy     #0
        lda     #CH_UFO_L
        sta     (PTR),y
        iny
        lda     #CH_UFO_M
        sta     (PTR),y
        iny
        lda     #CH_UFO_R
        sta     (PTR),y
        rts
ufoshot:
        lda     #0
        sta     shotA
        beq     ufokill
ufidle: lda     ufoTmr
        ora     ufoTmr+1
        beq     ufospawn
        lda     ufoTmr
        bne     :+
        dec     ufoTmr+1
:       dec     ufoTmr
        rts
ufospawn:
        lda     #1
        sta     ufoA
        lda     #0
        sta     ufoX
        lda     #2
        sta     ufoP
        lda     #<UFOPERIOD     ; rearm for the next visit
        sta     ufoTmr
        lda     #>UFOPERIOD
        sta     ufoTmr+1
        rts

ufoerase:                       ; lift our three chars off the lane
        lda     #UFOROW
        ldy     ufoX
        jsr     plotaddr
        ldy     #2
ue1:    lda     (PTR),y
        cmp     #CH_UFO_L
        bcc     ue2
        cmp     #CH_UFO_R+1
        bcs     ue2
        lda     #CH_SPACE
        sta     (PTR),y
ue2:    dey
        bpl     ue1
        rts

; ufokill: the saucer is hit. Value by the shot-count secret.
ufokill:
        jsr     ufoerase
        lda     #0
        sta     ufoA
        ldx     #FX_UFOHIT
        jsr     sndfx
        lda     shotCnt
        cmp     #23
        beq     uf300
        bcc     ufsmall
        sec                     ; shot > 23: 300 on every 15th after the 23rd
        sbc     #23
uf15:   cmp     #15
        bcc     :+
        sbc     #15
        jmp     uf15
:       cmp     #0
        beq     uf300
ufsmall:
        lda     shotCnt
        and     #3
        tax
        lda     UFOVAL,x        ; 50 / 100 / 150 / 100
        bne     ufsc
uf300:  lda     #30             ; 300 points, in units of ten
ufsc:   pha
        jsr     addscore
        pla                     ; flash the value where the saucer died:
        ldx     #0              ; units → "50" / "100" / "150" / "300"
        cmp     #10
        bcc     uftens
uf10:   sbc     #10             ; carry is set
        inx
        cmp     #10
        bcs     uf10
uftens: pha
        txa
        beq     :+
        ora     #48
        sta     popB
        pla
        ora     #48
        sta     popB+1
        lda     #48
        sta     popB+2
        lda     #3
        bne     ufpn
:       pla
        ora     #48
        sta     popB
        lda     #48
        sta     popB+1
        lda     #2
ufpn:   sta     popN
        lda     ufoX
        sta     popX
        lda     #UFOROW
        sta     popY
        lda     #20
        sta     popT
        jmp     popshow

; ---------------------------- sound ---------------------------------------
; One CB2 voice, priority-owned. sndfx starts effect X if nothing more
; important is playing; snddrv steps the current effect once per tick and
; releases the voice when it ends. The heartbeat is triggered by the march's
; sweep wrap, so its tempo IS the march tempo.
sndfx:  lda     FXPER,x         ; entry 1: period from the table
sndfxp: sta     tmp3            ; entry 2: caller supplies the period in A
        lda     FXPRI,x
        cmp     sndPri
        bcc     sfret           ; something more important is playing
        sta     sndPri
        stx     sndFX
        lda     FXDUR,x
        sta     sndTmr
        lda     #$10
        sta     SND_ACR
        lda     FXPAT,x
        sta     SND_SR
        lda     tmp3
        sta     SND_T2
        sta     curper
sfret:  rts

snddrv: lda     sndPri
        bne     sd1
        lda     ufoA            ; voice idle + saucer aloft → warble under
        beq     sdret
        lda     ufoWb
        eor     #1
        sta     ufoWb
        beq     :+
        lda     #90
        bne     :++
:       lda     #110
:       ldx     #FX_UFO
        jmp     sndfxp
sd1:    dec     sndTmr
        bne     sd2
sndoff: lda     #0              ; effect over: release the voice properly
        sta     SND_T2
        sta     SND_ACR
        sta     sndPri
        rts
sd2:    lda     sndFX           ; per-tick shaping
        cmp     #FX_SHOT
        bne     :+
        lda     curper          ; zap: pitch dives
        clc
        adc     #8
        sta     curper
        sta     SND_T2
        rts
:       cmp     #FX_EXPL
        bne     :+
        lda     curper          ; rumble: slow downward groan
        clc
        adc     #4
        sta     curper
        sta     SND_T2
:
sdret:  rts

; ---------------------------- bombs ---------------------------------------
; Three slots, three flavours: 0 slow straight '!', 1 fast straight '|',
; 2 the wiggly one (╲╱ alternating, drifting a column per step).
bombmove:
        ldx     #2
bmslot: stx     tmp2
        lda     bombA,x
        beq     bmnext
        dec     bombP,x
        bne     bmnext          ; not this bomb's tick
        ldy     bombT,x
        lda     DIVT,y
        sta     bombP,x         ; reload the per-type pace divisor
        lda     bombG,x         ; erase, unless something overdrew us
        beq     bmnew           ; (never drawn yet)
        sta     tmp3
        lda     bombY,x
        ldy     bombX,x
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     tmp3
        bne     bmnew
        lda     #CH_SPACE
        sta     (PTR),y
bmnew:  ldx     tmp2
        inc     bombY,x
        lda     bombY,x
        cmp     #LIVESROW
        bcc     bmwig
        lda     #0              ; hit the ground row — gone
        sta     bombA,x
bmnext: ldx     tmp2
        dex
        bpl     bmslot
        rts
bmwig:  lda     bombT,x
        cmp     #2
        bne     bmglyph
        lda     bombW,x         ; wiggle: alternate the sideways drift
        eor     #1
        sta     bombW,x
        bne     bmwr
        lda     bombX,x
        beq     bmglyph         ; clamped at the left wall
        dec     bombX,x
        jmp     bmglyph
bmwr:   lda     bombX,x
        cmp     #39
        bcs     bmglyph         ; clamped at the right wall
        inc     bombX,x
bmglyph:                        ; pick the char this bomb wears now
        lda     bombT,x
        cmp     #2
        bne     :+
        lda     bombW,x
        beq     bmw1
        lda     #CH_WIG2
        bne     bmset
bmw1:   lda     #CH_WIG1
        bne     bmset
:       tay
        lda     BGLY,y
bmset:  sta     bombG,x
        lda     bombY,x         ; look at the destination cell
        ldy     bombX,x
        jsr     plotaddr
        ldy     #0
        lda     (PTR),y
        cmp     #CH_SPACE
        beq     bmdraw
        cmp     #CH_SHIELD1
        beq     bmshield
        cmp     #CH_SHIELD2
        beq     bmshield
        cmp     #CH_SHOT
        beq     bmshot
        cmp     #CH_BASE_L
        beq     bmbase
        cmp     #CH_BASE_M
        beq     bmbase
        cmp     #CH_BASE_R
        beq     bmbase
bmdraw: ldx     tmp2            ; space (or something soft): fall onward
        lda     bombG,x
        sta     (PTR),y
        jmp     bmnext
bmshield:                       ; chew the bunker from above
        jsr     erode
        ldx     tmp2
        lda     #0
        sta     bombA,x
        jmp     bmnext
bmshot: ldx     tmp2            ; met the player's shot head-on: both die
        lda     #0
        sta     bombA,x
        sta     shotA
        lda     #42
        ldy     bombX,x
        stx     tmp2
        lda     bombY,x
        tax
        lda     #42
        jsr     popupset
        jmp     bmnext
bmbase: jsr     playerhit
        ldx     tmp2
        lda     #0
        sta     bombA,x
        jmp     bmnext

; erode: shield cell content in A, cell at (PTR),y=0: solid→checker→gone
erode:  cmp     #CH_SHIELD1
        bne     :+
        lda     #CH_SHIELD2
        .byte   $2C             ; BIT abs — skip the next 2-byte load
:       lda     #CH_SPACE
        sta     (PTR),y
        rts

; bombdrop: rate-limited; drops from the lowest live alien in a column.
; Types cycle 0,1,2 so all three flavours stay in the air; the wiggly one
; aims for the player's column like the arcade's rolling shot.
bombdrop:
        lda     bombTmr
        beq     :+
        dec     bombTmr
        rts
:       ldx     #2              ; find a free slot
bd1:    lda     bombA,x
        beq     bd2
        dex
        bpl     bd1
        lda     #8              ; all three flying: try again soon
        sta     bombTmr
        rts
bd2:    stx     tmp3            ; tmp3 = the slot
        lda     nextT
        cmp     #2
        beq     bdaim
        jsr     random          ; straight flavours: a random live column
        and     #$0F
bdmod:  cmp     #11
        bcc     :+
        sbc     #11
        jmp     bdmod
:       sta     tmp             ; starting column; scan until one is live
        ldy     #11
bdscan: lda     tmp
        jsr     lowcol
        bpl     bdgot
        inc     tmp
        lda     tmp
        cmp     #11
        bcc     :+
        lda     #0
        sta     tmp
:       dey
        bne     bdscan
        rts                     ; rack is empty (wavedone will fire)
bdaim:  ldy     #10             ; wiggly: nearest live column to the base
        lda     #$FF
        sta     tmp             ; best distance so far
        sta     bdbest
bda1:   sty     bdcol
        tya
        jsr     lowcol
        bmi     bda3            ; column empty
        stx     bdidx
        lda     basex
        clc
        adc     #1              ; the muzzle column
        sec
        eor     #$FF
        sec
        adc     alienX,x        ; A = alienX - (basex+1)
        bcs     :+
        eor     #$FF            ; absolute value
        adc     #1
:       cmp     tmp
        bcs     bda3
        sta     tmp
        lda     bdidx
        sta     bdbest
bda3:   ldy     bdcol
        dey
        bpl     bda1
        ldx     bdbest
        cpx     #$FF
        beq     bdout           ; nothing alive
        bne     bdspawn
bdgot:                          ; X = alien index to drop from
bdspawn:
        txa
        tay                     ; Y = source alien
        ldx     tmp3            ; X = the slot
        lda     #1
        sta     bombA,x
        lda     alienX,y
        sta     bombX,x
        lda     alienY,y
        sta     bombY,x
        lda     nextT
        sta     bombT,x
        tay
        lda     DIVT,y
        sta     bombP,x
        lda     #0
        sta     bombW,x
        sta     bombG,x
        ldy     nextT           ; cycle the flavour for next time
        iny
        cpy     #3
        bcc     :+
        ldy     #0
:       sty     nextT
        jsr     random
        and     #$1F
        clc
        adc     #30             ; 30-61 ticks between drops
        sta     bombTmr
bdout:  rts

; lowcol: A = formation column 0-10 → X = lowest live alien index, or
; X negative (N set) when the column is dead
lowcol: clc
        adc     #44             ; bottom row first
        tax
lc1:    lda     alienA,x
        bne     lc2
        txa
        sec
        sbc     #11             ; up one formation row
        tax
        bcs     lc1
        ldx     #$FF
        rts                     ; N flag set: empty
lc2:    cpx     #0              ; N clear: found (indexes are 0-54, bit7=0)
        rts

; random: 8-bit maximal Galois LFSR; fresh byte in A (state must stay != 0)
random: lda     seed
        lsr
        bcc     :+
        eor     #$B8
:       sta     seed
        rts

; ---------------------------- drawing -------------------------------------
; plotaddr: point PTR at screen row A (0-24), column Y (0-39)
plotaddr:
        sty     PTR             ; park the column in PTR low
        asl                     ; row*2
        asl                     ; row*4
        asl                     ; row*8
        sta     row8
        lda     #0
        sta     PTR+1
        lda     row8
        asl                     ; row*16
        rol     PTR+1
        asl                     ; row*32
        rol     PTR+1
        clc
        adc     row8            ; + row*8 = row*40
        bcc     :+
        inc     PTR+1
:       clc
        adc     PTR             ; + column
        sta     PTR
        lda     PTR+1
        adc     #$80            ; + $8000 screen base
        sta     PTR+1
        rts

; putchar: screen code X at row A, column Y (clobbers A,PTR)
putchar:
        jsr     plotaddr
        txa
        ldy     #0
        sta     (PTR),y
        rts

; drawtext: zero-terminated ASCII at (A=row, Y=col), text ptr in PTR2.
; Letters fold to screen codes; digits/punct/space pass through.
drawtext:
        jsr     plotaddr
        ldy     #0
dt1:    lda     (PTR2),y
        beq     dt2
        cmp     #$40
        bcc     dt0             ; digit/punct/space already a screen code
        sbc     #$40            ; letter: fold (carry set by cmp)
dt0:    sta     (PTR),y
        iny
        bne     dt1
dt2:    rts

; settext: load PTR2 with A(lo)/X(hi)
settext:
        sta     PTR2
        stx     PTR2+1
        rts

drawhud0:                       ; the score line alone (title reuses it)
        lda     #<hudtxt
        ldx     #>hudtxt
        jsr     settext
        lda     #HUDROW
        ldy     #0
        jsr     drawtext
        jsr     drawscore
        jsr     drawhi
        jmp     drawwave

drawhud:
        jsr     drawhud0
        lda     #<livestxt
        ldx     #>livestxt
        jsr     settext
        lda     #LIVESROW
        ldy     #0
        jsr     drawtext
        jmp     drawlives

; ------------------------- title screen -----------------------------------
titlescreen:
        lda     #$93
        jsr     CHROUT
        jsr     drawhud0        ; last game's score + the high score
        lda     #2
        sta     bcrow
        lda     #10
        sta     bccol
        ldx     #0
ts1:    stx     tmp             ; SPACE, 3x5 block letters
        lda     TSPACE,x
        jsr     bigchar
        lda     bccol
        clc
        adc     #4
        sta     bccol
        ldx     tmp
        inx
        cpx     #5
        bcc     ts1
        lda     #8
        sta     bcrow
        lda     #4
        sta     bccol
        ldx     #0
ts2:    stx     tmp             ; INVADERS
        lda     TINV,x
        jsr     bigchar
        lda     bccol
        clc
        adc     #4
        sta     bccol
        ldx     tmp
        inx
        cpx     #8
        bcc     ts2
        lda     #<advtxt        ; the score advance table
        ldx     #>advtxt
        jsr     settext
        lda     #15
        ldy     #8
        jsr     drawtext
        lda     #<advufo
        ldx     #>advufo
        jsr     settext
        lda     #16
        ldy     #12
        jsr     drawtext
        lda     #<adv30
        ldx     #>adv30
        jsr     settext
        lda     #17
        ldy     #12
        jsr     drawtext
        lda     #<adv20
        ldx     #>adv20
        jsr     settext
        lda     #18
        ldy     #12
        jsr     drawtext
        lda     #<adv10
        ldx     #>adv10
        jsr     settext
        lda     #19
        ldy     #12
        jsr     drawtext
        ldx     #CH_UFO_L       ; live glyphs in front of their prices
        lda     #16
        ldy     #12
        jsr     putchar
        ldx     #CH_UFO_M
        lda     #16
        ldy     #13
        jsr     putchar
        ldx     #CH_UFO_R
        lda     #16
        ldy     #14
        jsr     putchar
        ldx     GLYA
        lda     #17
        ldy     #13
        jsr     putchar
        ldx     GLYA+1
        lda     #18
        ldy     #13
        jsr     putchar
        ldx     GLYA+3
        lda     #19
        ldy     #13
        jsr     putchar
        lda     #<presstxt
        ldx     #>presstxt
        jsr     settext
        lda     #22
        ldy     #9
        jmp     drawtext

; bigchar: A = font letter index; draws 3x5 solid blocks at (bcrow, bccol)
bigchar:
        sta     tmp3
        asl
        asl
        clc
        adc     tmp3            ; letter*5 → offset into the font
        sta     bcoff
        lda     #0
        sta     tmp3            ; row within the glyph
bc1:    lda     bcrow
        clc
        adc     tmp3
        ldy     bccol
        jsr     plotaddr
        ldx     bcoff
        lda     FONT,x
        sta     bcpat           ; bits 2,1,0 = left, middle, right cell
        ldy     #2
bcb:    lsr     bcpat
        bcc     :+
        lda     #CH_SHIELD1     ; solid block
        sta     (PTR),y
:       dey
        bpl     bcb
        inc     bcoff
        inc     tmp3
        lda     tmp3
        cmp     #5
        bcc     bc1
        rts

; drawnum: 16-bit value in num (units of 10) → four decimal digits plus a
; literal trailing '0' at (PTR),y=0..4. Max 6553 units = 65530 points.
drawnum:
        ldy     #0
        lda     #<1000
        sta     sub
        lda     #>1000
        sta     sub+1
        jsr     digit
        lda     #<100
        sta     sub
        lda     #>100
        sta     sub+1
        jsr     digit
        lda     #<10
        sta     sub
        lda     #0
        sta     sub+1
        jsr     digit
        lda     num             ; last digit = remainder (0-9)
        ora     #48
        sta     (PTR),y
        iny
        lda     #48             ; trailing literal 0 (scores are tens)
        sta     (PTR),y
        rts

digit:  ldx     #0
dg1:    lda     num
        sec
        sbc     sub
        lda     num+1
        sbc     sub+1
        bcc     dg2             ; num < sub → digit done
        lda     num
        sec
        sbc     sub
        sta     num
        lda     num+1
        sbc     sub+1
        sta     num+1
        inx
        bne     dg1
dg2:    txa
        ora     #48
        sta     (PTR),y
        iny
        rts

drawscore:
        lda     score
        sta     num
        lda     score+1
        sta     num+1
        lda     #HUDROW
        ldy     #6
        jsr     plotaddr
        jmp     drawnum

drawhi:
        lda     hiscore
        sta     num
        lda     hiscore+1
        sta     num+1
        lda     #HUDROW
        ldy     #16
        jsr     plotaddr
        jmp     drawnum

drawwave:
        lda     #HUDROW
        ldy     #28
        jsr     plotaddr
        lda     wave
        ldx     #0
wv1:    cmp     #10
        bcc     wv2
        sbc     #10
        inx
        bne     wv1
wv2:    pha
        txa
        ora     #48
        ldy     #0
        sta     (PTR),y
        pla
        ora     #48
        iny
        sta     (PTR),y
        rts

drawlives:
        lda     #LIVESROW
        ldy     #6
        jsr     plotaddr
        lda     lives
        ora     #48
        ldy     #0
        sta     (PTR),y
        ; spare-base icons at col 9+ (one per life beyond the active one)
        ldy     #3              ; screen col 9 = PTR offset 3
        ldx     #1
li1:    cpx     lives
        bcs     li2
        lda     #CH_BASE_M
        sta     (PTR),y
        iny
        lda     #CH_SPACE
        sta     (PTR),y
        iny
        inx
        bne     li1
li2:    lda     #CH_SPACE       ; blank one trailing icon slot
        sta     (PTR),y
        rts

drawshields:
        ldx     #3              ; four bunkers
sh1:    lda     shieldcol,x
        sta     tmp
        ldy     tmp
        lda     #SHIELDROW
        jsr     plotaddr
        jsr     shrow
        ldy     tmp
        lda     #SHIELDROW+1
        jsr     plotaddr
        jsr     shrow
        dex
        bpl     sh1
        rts
shrow:  ldy     #3
        lda     #CH_SHIELD1
sh2:    sta     (PTR),y
        dey
        bpl     sh2
        rts

drawbase:
        lda     #BASEROW
        ldy     basex
        jsr     plotaddr
        ldy     #0
        lda     #CH_BASE_L
        sta     (PTR),y
        iny
        lda     #CH_BASE_M
        sta     (PTR),y
        iny
        lda     #CH_BASE_R
        sta     (PTR),y
        rts

; ---------------------------- data ----------------------------------------
        .segment "RODATA"
hudtxt:   .byte "SCORE 00000  HI 00000  WAVE 01", 0
livestxt: .byte "LIVES", 0
shieldcol:.byte 5, 14, 23, 32

; formation tables, index = frow*11 + fcol (frow 0 = top)
ROWOF:  .repeat 5, r
        .repeat 11
        .byte r
        .endrepeat
        .endrepeat
COLOF:  .repeat 5
        .repeat 11, c
        .byte c
        .endrepeat
        .endrepeat
; per-frow glyph frames and points (units of 10): squid 30, crab 20, oct 10
GLYA:   .byte 87, 65, 65, 86, 86        ; frame A: ○ ♠ ♠ ╳ ╳
GLYB:   .byte 81, 88, 88, 90, 90        ; frame B: ● ♣ ♣ ♦ ♦
PTS:    .byte 3, 2, 2, 1, 1
DIVT:   .byte 4, 2, 3                   ; bomb pace: rows fall 1-per-N ticks
BGLY:   .byte CH_BOMB0, CH_BOMB1        ; straight-bomb glyphs by type
UFOVAL: .byte 5, 10, 15, 10             ; off-cycle saucer values (units of 10)
gotxt:  .byte "GAME OVER", 0

; sound tables, indexed by FX id       hb   ufo shot hit ufoh expl
FXPRI:  .byte                           1,   1,  2,   3,  3,   4
FXDUR:  .byte                           5,   4,  8,   6, 12,  45
FXPAT:  .byte                         $0F, $0F, $0F, $55, $33, $6E
FXPER:  .byte                           0,  90, 20,  25,  40, 60
hbtab:  .byte 200, 215, 230, 245        ; the four-note descending bass

; title screen: 3x5 block font (rows top-down, bits 2/1/0 = cells)
;             S              P              A              C
FONT:   .byte 7,4,7,1,7,     7,5,7,4,4,    7,5,7,5,5,     7,4,4,4,7
;             E              I              N              V
        .byte 7,4,7,4,7,     7,2,2,2,7,    5,7,7,7,5,     5,5,5,5,2
;             D              R
        .byte 6,5,5,5,6,     7,5,6,5,5
TSPACE: .byte 0, 1, 2, 3, 4             ; S P A C E
TINV:   .byte 5, 6, 7, 2, 8, 4, 9, 0    ; I N V A D E R S
advtxt:   .byte "*SCORE ADVANCE TABLE*", 0
advufo:   .byte "    = ? MYSTERY", 0
adv30:    .byte "  = 30 POINTS", 0
adv20:    .byte "  = 20 POINTS", 0
adv10:    .byte "  = 10 POINTS", 0
presstxt: .byte "PRESS ANY KEY TO PLAY", 0

        .segment "BSS"
row8:    .res 1
tmp:     .res 1
tmp2:    .res 1
tmp3:    .res 1
num:     .res 2
sub:     .res 2
score:   .res 2                 ; units of 10 points
hiscore: .res 2
lives:   .res 1
wave:    .res 1
basex:   .res 1                 ; base left column (0-37)

; --- dynamic game state, zeroed as a block by newgame (keep contiguous) ---
gzs:
movetmr: .res 1                 ; ticks until the base may move again
shotA:   .res 1                 ; player shot active flag
shotX:   .res 1
shotY:   .res 1
shotCnt: .res 1                 ; shots fired this game (UFO secret counter)
invaded: .res 1                 ; an alien reached the baseline
extraF:  .res 1                 ; 1500-point bonus base already paid
popT:    .res 1                 ; explosion/score flash: ticks left
popX:    .res 1
popY:    .res 1
popN:    .res 1                 ; how many chars the flash is
popB:    .res 3                 ; the chars we flashed (erase-if-unchanged)
ufoA:    .res 1                 ; saucer on screen
ufoX:    .res 1                 ; its left column (glyphs at x, x+1, x+2)
ufoP:    .res 1                 ; ticks until it slides a column
ufoTmr:  .res 2                 ; ticks until the next visit
sndPri:  .res 1                 ; priority of the playing effect (0 = idle)
sndFX:   .res 1                 ; which effect is playing
sndTmr:  .res 1                 ; ticks it has left
curper:  .res 1                 ; its current T2 period
hbIdx:   .res 1                 ; which heartbeat note is next
ufoWb:   .res 1                 ; warble phase
deathT:  .res 1                 ; player-explosion freeze, ticks left
bombA:   .res 3                 ; bomb slots: active flags
bombX:   .res 3
bombY:   .res 3
bombT:   .res 3                 ; flavour 0/1/2
bombP:   .res 3                 ; ticks until this bomb falls a row
bombW:   .res 3                 ; wiggle phase
bombG:   .res 3                 ; glyph currently on screen (0 = none)
bombTmr: .res 1                 ; ticks until the next drop attempt
nextT:   .res 1                 ; next flavour to drop (cycles 0,1,2)
gze:
GZLEN = gze - gzs

; formation state (reset per wave by initform)
formtop: .res 1                 ; screen row of the rack's top row
mcur:    .res 1                 ; march cursor: next index to consider
mdx:     .res 1                 ; step: +1 / -1 (two's complement)
mdrop:   .res 1                 ; this sweep drops instead of stepping
edgeF:   .res 1                 ; a moved alien touched column 0/39
sweepF:  .res 1                 ; animation frame bit (toggles per sweep)
aliveN:  .res 1                 ; live alien count
alienA:  .res 55                ; alive flags
alienX:  .res 55                ; screen column per alien
alienY:  .res 55                ; screen row per alien
seed:    .res 1                 ; LFSR state (never zero)
bdcol:   .res 1                 ; bombdrop scratch: column being scored
bdidx:   .res 1                 ; bombdrop scratch: that column's alien
bdbest:  .res 1                 ; bombdrop scratch: best alien so far
bcrow:   .res 1                 ; bigchar: target row
bccol:   .res 1                 ; bigchar: target column
bcoff:   .res 1                 ; bigchar: font cursor
bcpat:   .res 1                 ; bigchar: row pattern being unpacked
