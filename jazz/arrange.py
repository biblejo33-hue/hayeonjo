"""Assemble the full modern-jazz / swing big band arrangement."""
import random, sys
import engine as E
from engine import (Band, Clock, walk, comp, guitar_freddie, drums, fill,
                    brass_stab, sax_pad, line, sc, ct, sect_notes,
                    P_PIANO, P_BASS, P_GTR, P_MTPT, P_TPT, P_TBN, P_ALTO, P_TENOR, P_BARI,
                    K_BRUSH, K_JAZZ, RIDE, BELL, CRASH, CRASH2, SPLASH, SNARE, KICK, HHP, HHC,
                    T_HI, T_MID, T_LO, T_FLO)
from theory import Chord, rootless, nearest_pc
import chart as CH

rnd = random.Random(20260831)
CHART, SECOF = CH.build()
BARS = CH.TOTAL_BARS

RIT_START = 95*4          # ritardando from the top of bar 95
clock = Clock(rit_start=RIT_START, rit_end=98*4, final_ratio=0.55)
band  = Band(clock)

def ch_at(bar, beat=0.0):
    ev = CHART[bar]; c = ev[0][1]
    for p, x in ev:
        if beat >= p - 1e-6: c = x
    return c

# ---------------------------------------------------------------- INTRO (piano alone)
# a written 4-bar opening: rich voicings with a singing top line
INTRO_TOP = [
    (0, [(0.0,1.5,None),(1.5,0.5,78),(2.0,1.0,81),(3.0,0.5,78),(3.5,0.5,76)]),
    (1, [(0.0,1.5,74),(1.5,0.5,73),(2.0,1.5,71),(3.5,0.5,69)]),
    (2, [(0.0,1.0,71),(1.0,0.5,74),(1.5,0.5,73),(2.0,1.5,69),(3.5,0.5,68)]),
    (3, [(0.0,2.0,66),(2.5,0.5,69),(3.0,0.5,71),(3.5,0.5,73)]),
]
for bar, evs in INTRO_TOP:
    c0 = ch_at(bar, 0)
    band.chord('piano', rootless(c0, low=48, high=68), bar*4+0.0, 2.2, 60, P_PIANO)
    if len(CHART[bar]) > 1:
        c1 = CHART[bar][1][1]
        band.chord('piano', rootless(c1, low=48, high=68), bar*4+2.0, 1.8, 58, P_PIANO)
    band.n('piano', ct(c0, 0, 40), bar*4, 1.9, 52, P_PIANO)          # LH root
    line(band, 'piano', P_PIANO, evs, bar*4, vel=74, vjit=5)

# ---------------------------------------------------------------- INTRO band 4-11
walk(band, range(4, 12), CHART, vel=88, seed=11)
comp(band, range(4, 12), CHART, level='sparse', vel=64, seed=12)
drums(band, range(6, 12), 'brush', intensity=0.34, seed=13, fill_every=6)
guitar_freddie(band, range(8, 12), CHART, vel=40, seed=14)

# muted trumpet hints the tune, then hands it to the singer
HINT = [
    (8,  [(1.0,0.5,74),(1.5,0.5,76),(2.0,1.5,78),(3.5,0.5,76)]),
    (9,  [(0.0,1.0,74),(1.0,0.5,73),(1.5,1.5,71),(3.5,0.5,69)]),
    (10, [(0.5,0.5,71),(1.0,0.5,74),(1.5,2.0,73)]),
    (11, [(0.0,1.0,71),(1.5,0.5,69),(2.0,1.0,66)]),
]
for bar, evs in HINT:
    line(band, 'mutedtpt', P_MTPT, evs, bar*4, vel=70, vjit=4)

# ---------------------------------------------------------------- VERSE 1  (12-27)
walk(band, range(12, 28), CHART, vel=92, seed=21)
comp(band, range(12, 28), CHART, level='sparse', vel=62, seed=22)
comp(band, range(20, 28), CHART, level='med', vel=64, seed=23)
guitar_freddie(band, range(12, 28), CHART, vel=44, seed=24)
drums(band, range(12, 28), 'brush', intensity=0.42, seed=25, fill_every=8)

# tenor sax answers the singer at the end of each 4-bar phrase (call & response)
ANSWERS = {
    15: [(2.0,0.5,69),(2.5,0.5,71),(3.0,0.5,73),(3.5,0.5,74)],
    19: [(2.0,0.5,76),(2.5,0.5,74),(3.0,1.0,71)],
    23: [(2.5,0.5,70),(3.0,0.5,71),(3.5,0.5,74)],
    27: [(2.0,0.5,73),(2.5,0.5,71),(3.0,0.5,69),(3.5,0.5,66)],
}
for bar, evs in ANSWERS.items():
    line(band, 'tenor1', P_TENOR, evs, bar*4, vel=76, vjit=5)

# ---------------------------------------------------------------- PRE-CHORUS (28-35)
walk(band, range(28, 36), CHART, vel=98, seed=31, active=1.4)
comp(band, range(28, 36), CHART, level='med', vel=70, seed=32)
comp(band, range(32, 36), CHART, level='dense', vel=74, seed=33)
guitar_freddie(band, range(28, 36), CHART, vel=48, seed=34)
drums(band, range(28, 32), 'brush', intensity=0.55, seed=35, fill_every=4)
drums(band, range(32, 36), 'ride',  intensity=0.72, seed=36, fill_every=4, crash_bars=(32,))

# horns arrive one family at a time
for bar in (30, 31):
    c = ch_at(bar); band.n('bari', sc(c, 0, 46), bar*4, 3.6, 62, P_BARI)
    band.n('tenor2', sc(c, 2, 60), bar*4, 3.6, 58, P_TENOR)
for bar in (32, 33):
    c = ch_at(bar); sax_pad(band, c, 74, bar*4, 3.6, 62)
for bar in (34, 35):
    c = ch_at(bar, 0); sax_pad(band, c, 76, bar*4, 1.8, 70)
    brass_stab(band, c, 81, bar*4+1.5, 0.45, 92)
    brass_stab(band, ch_at(bar, 2.5), 83, bar*4+2.5, 0.45, 98)

# rising brass shout straight into the chorus
SHOUT_IN = [(2.0,0.5,74),(2.5,0.5,76),(3.0,0.5,78),(3.5,0.5,81)]
for nm, prog, tr in (('tpt1',P_TPT,0), ('tpt2',P_TPT,-4), ('tbn1',P_TBN,-12), ('alto1',P_ALTO,-5)):
    line(band, nm, prog, [(o,d,p+tr) for o,d,p in SHOUT_IN], 35*4, vel=104, vjit=3)

# ---------------------------------------------------------------- helpers for the shout writing
def hits(bar, pattern, near=81, vel=100, brass=True, sax=True, sax_near=74, dur=0.42):
    """pattern: [(beat, dur)] — punchy section hits on the chord of that beat."""
    for item in pattern:
        pos, d = (item if len(item) == 2 else (item[0], dur))
        c = ch_at(bar, pos)
        if brass: brass_stab(band, c, near, bar*4+pos, d, vel)
        if sax:   sax_pad(band, c, sax_near, bar*4+pos, d, vel-14)

def sax_bed(bar, near=74, vel=58, dur=3.6):
    c = ch_at(bar); sax_pad(band, c, near, bar*4, dur, vel)

# ---------------------------------------------------------------- CHORUS 1 (36-51)
walk(band, range(36, 52), CHART, vel=104, seed=41, active=1.3)
comp(band, range(36, 52), CHART, level='dense', vel=76, seed=42)
guitar_freddie(band, range(36, 52), CHART, vel=50, seed=43)
drums(band, range(36, 52), 'ride', intensity=0.86, seed=44, fill_every=4,
      crash_bars=(36, 40, 44, 48))

CHORUS_HITS = {
    0: [(1.5,0.4),(3.0,0.4)],
    1: [(0.5,0.4),(2.5,0.4),(3.5,0.3)],
    2: [(1.0,0.4),(3.5,0.4)],
    3: [(0.0,0.5),(2.0,0.4),(3.0,0.3),(3.5,0.3)],
    4: [(1.5,0.4),(2.5,0.4)],
    5: [(0.5,0.4),(3.0,0.5)],
    6: [(1.0,0.4),(2.5,0.4),(3.5,0.3)],
    7: [(0.0,0.5),(1.5,0.4),(3.0,0.5)],
}
for bar in range(36, 52):
    slot = (bar-4) % 8
    top  = 79 + (3 if slot in (3, 7) else 0) + (2 if bar >= 44 else 0)
    hits(bar, CHORUS_HITS[slot], near=top, vel=96 + (6 if bar >= 44 else 0), sax_near=74)
    if slot in (0, 2, 4, 6): sax_bed(bar, near=71, vel=52)

# the sax section answers the singer at the end of each phrase
CH_ANSWER = {
    39: [(2.0,0.5,76),(2.5,0.5,78),(3.0,0.5,81),(3.5,0.5,83)],
    43: [(2.0,0.5,81),(2.5,0.5,78),(3.0,1.0,74)],
    47: [(2.5,0.5,74),(3.0,0.5,76),(3.5,0.5,79)],
    51: [(1.5,0.5,83),(2.0,0.5,81),(2.5,0.5,78),(3.0,1.0,76)],
}
for bar, evs in CH_ANSWER.items():
    line(band, 'tpt1', P_TPT, evs, bar*4, vel=104, vjit=4)
    line(band, 'alto1', P_ALTO, [(o,d,p-12) for o,d,p in evs], bar*4, vel=88, vjit=4)

# ---------------------------------------------------------------- VERSE 2 (52-59) — back to the combo
walk(band, range(52, 60), CHART, vel=93, seed=51, active=1.5)
comp(band, range(52, 60), CHART, level='med', vel=64, seed=52)
guitar_freddie(band, range(52, 60), CHART, vel=42, seed=53)
drums(band, range(52, 60), 'brush', intensity=0.44, seed=54, fill_every=8)

OBBLIGATO = {
    53: [(2.0,0.5,69),(2.5,0.5,71),(3.0,1.0,74)],
    55: [(1.5,0.5,73),(2.0,0.5,71),(2.5,1.0,68),(3.5,0.5,66)],
    57: [(2.0,0.5,64),(2.5,0.5,66),(3.0,0.5,69),(3.5,0.5,71)],
    59: [(1.0,0.5,73),(1.5,0.5,71),(2.0,0.5,69),(2.5,1.5,66)],
}
for bar, evs in OBBLIGATO.items():
    line(band, 'tenor1', P_TENOR, evs, bar*4, vel=74, vjit=5)

# ---------------------------------------------------------------- BRIDGE (60-67) — hushed
walk(band, range(60, 68), CHART, vel=80, seed=61, active=0.6)
comp(band, range(60, 68), CHART, level='sparse', vel=54, seed=62)
drums(band, range(60, 68), 'brush', intensity=0.22, seed=63, fill_every=8)
for bar in (66, 67):
    sax_bed(bar, near=69, vel=46)

# ---------------------------------------------------------------- TENOR SAX SOLO (68-75)
walk(band, range(68, 76), CHART, vel=96, seed=71, active=1.4)
comp(band, range(68, 76), CHART, level='med', vel=68, seed=72)
guitar_freddie(band, range(72, 76), CHART, vel=44, seed=73)
drums(band, range(68, 72), 'brush', intensity=0.46, seed=74, fill_every=4)
drums(band, range(72, 76), 'ride',  intensity=0.74, seed=75, fill_every=4, crash_bars=(72,))

SOLO_LINE = {
    68: [(1.0,0.5,66),(1.5,0.5,69),(2.0,0.5,71),(2.5,0.5,74),(3.0,1.0,73)],
    69: [(0.0,0.5,74),(0.5,0.5,71),(1.0,0.5,69),(1.5,0.5,66),(2.0,0.5,68),(2.5,0.5,70),(3.0,1.0,72)],
    70: [(0.0,0.5,71),(0.5,0.5,73),(1.0,1.0,76),(2.0,0.5,74),(2.5,0.5,73),(3.0,1.0,68)],
    71: [(0.0,0.5,70),(0.5,0.5,72),(1.0,0.5,74),(1.5,0.5,76),(2.0,1.5,77),(3.5,0.5,74)],
    72: [(0.0,1.0,73),(1.0,0.5,71),(1.5,0.5,69),(2.0,0.5,67),(2.5,0.5,66),(3.0,1.0,64)],
    73: [(0.0,0.5,66),(0.5,0.5,67),(1.0,1.0,69),(2.0,0.5,70),(2.5,0.5,73),(3.0,1.0,75)],
    74: [(0.0,1.5,74),(1.5,0.5,73),(2.0,0.5,71),(2.5,0.5,69),(3.0,1.0,66)],
    75: [(0.0,0.5,64),(0.5,0.5,67),(1.0,0.5,71),(1.5,0.5,74),(2.0,0.5,75),(2.5,0.5,73),(3.0,1.0,70)],
}
for bar, evs in SOLO_LINE.items():
    line(band, 'tenor_solo', P_TENOR, evs, bar*4, vel=96, vjit=6)

# brass backgrounds push the solo into the last chorus
for bar in (73, 74, 75):
    hits(bar, [(1.5,0.4),(3.0,0.4)], near=79, vel=84, sax=False)
line(band, 'tpt1', P_TPT, [(2.0,0.5,76),(2.5,0.5,79),(3.0,0.5,81),(3.5,0.5,84)], 75*4, vel=108, vjit=3)
line(band, 'tbn1', P_TBN, [(2.0,0.5,64),(2.5,0.5,67),(3.0,0.5,69),(3.5,0.5,72)], 75*4, vel=102, vjit=3)

# ---------------------------------------------------------------- FINAL CHORUS (76-91)
STOP = {80, 88}
fin = [b for b in range(76, 92) if b not in STOP]
walk(band, fin, CHART, vel=108, seed=81, active=1.6)
comp(band, fin, CHART, level='dense', vel=80, seed=82)
guitar_freddie(band, fin, CHART, vel=52, seed=83)
drums(band, range(76, 92), 'ride', intensity=1.0, seed=84, fill_every=4,
      crash_bars=(76, 84, 90), stop_time=tuple(STOP))

SHOUT_HITS = {
    0: [(0.0,0.5),(1.5,0.4),(3.0,0.4)],
    1: [(0.5,0.4),(2.0,0.4),(3.5,0.3)],
    2: [(0.0,0.4),(1.0,0.4),(2.5,0.4)],
    3: [(1.5,0.4),(2.5,0.4),(3.5,0.4)],
    4: [(0.0,0.5),(2.0,0.4),(3.5,0.3)],
    5: [(0.5,0.4),(1.5,0.4),(3.0,0.4)],
    6: [(0.0,0.4),(1.5,0.4),(2.5,0.4),(3.5,0.3)],
    7: [(0.0,0.5),(2.0,0.5),(3.0,0.4),(3.5,0.4)],
}
for bar in range(76, 92):
    slot = (bar-4) % 8
    if bar in STOP:
        # stop-time: the whole band punches, then drops out under the voice
        c = ch_at(bar)
        brass_stab(band, c, 86, bar*4, 0.55, 118); sax_pad(band, c, 78, bar*4, 0.55, 104)
        band.n('bass', nearest_pc(c.root, 40), bar*4, 0.5, 112, P_BASS)
        band.chord('piano', rootless(c), bar*4, 0.5, 96, P_PIANO)
        brass_stab(band, c, 84, bar*4+2.5, 0.45, 112); sax_pad(band, c, 76, bar*4+2.5, 0.45, 98)
        band.n('bass', nearest_pc(c.root, 40)-5, bar*4+2.5, 0.45, 106, P_BASS)
        band.chord('piano', rootless(c), bar*4+2.5, 0.45, 92, P_PIANO)
        continue
    top = 84 + (2 if slot in (3, 7) else 0)
    hits(bar, SHOUT_HITS[slot], near=top, vel=110, sax_near=77)
    if slot in (0, 2, 4, 6): sax_bed(bar, near=73, vel=58, dur=3.4)

# a new counter-melody riding behind the last chorus vocal
COUNTER = {
    77: [(0.0,0.5,74),(0.5,0.5,76),(1.0,1.0,78),(2.5,0.5,76),(3.0,1.0,74)],
    79: [(0.0,0.5,76),(0.5,0.5,78),(1.0,1.5,81),(3.0,1.0,78)],
    81: [(0.0,0.5,73),(0.5,0.5,74),(1.0,1.0,76),(2.5,0.5,74),(3.0,1.0,71)],
    83: [(0.0,0.5,74),(1.0,0.5,76),(1.5,0.5,78),(2.0,1.0,81),(3.5,0.5,83)],
    85: [(0.0,0.5,78),(0.5,0.5,76),(1.0,1.0,74),(2.5,0.5,76),(3.0,1.0,78)],
    87: [(0.0,0.5,81),(0.5,0.5,78),(1.0,1.5,76),(3.0,1.0,74)],
    89: [(0.0,0.5,76),(0.5,0.5,78),(1.0,0.5,81),(1.5,0.5,83),(2.0,1.5,86)],
    91: [(0.0,0.5,84),(0.5,0.5,83),(1.0,0.5,81),(1.5,0.5,78),(2.0,2.0,76)],
}
for bar, evs in COUNTER.items():
    line(band, 'tenor1', P_TENOR, [(o,d,p-12) for o,d,p in evs], bar*4, vel=88, vjit=5)
    line(band, 'tpt2',   P_TPT,   evs, bar*4, vel=98, vjit=5)

# screaming lead trumpet on the last eight
for bar, evs in {
    89: [(3.0,1.0,88)],
    90: [(0.0,1.5,89),(2.0,0.5,86),(2.5,1.5,88)],
    91: [(0.0,2.0,91),(2.5,0.5,88),(3.0,1.0,86)],
}.items():
    line(band, 'tpt1', P_TPT, evs, bar*4, vel=118, vjit=2)

# ---------------------------------------------------------------- ENDING (92-97)
walk(band, range(92, 96), CHART, vel=104, seed=91, active=1.2)
comp(band, range(92, 96), CHART, level='med', vel=78, seed=92)
guitar_freddie(band, range(92, 95), CHART, vel=48, seed=93)
drums(band, range(92, 96), 'ride', intensity=0.9, seed=94, fill_every=4, crash_bars=(92,))

for bar in range(92, 95):
    hits(bar, [(0.0,0.5),(1.5,0.4),(3.0,0.5)], near=84, vel=110, sax_near=76)

# bar 95: the band lands together, then the ritardando takes hold
c95 = ch_at(95)
hits(95, [(0.0,0.9),(2.0,0.9)], near=86, vel=114, sax_near=78)
band.n('drums_kit', CRASH, 95*4, 2.0, 112, K_JAZZ, drum=True)

# bar 96: Em9 -> A13, spelled out slowly
for pos, cc, near in ((0.0, ch_at(96,0), 84), (2.0, ch_at(96,2.0), 86)):
    brass_stab(band, cc, near, 96*4+pos, 1.6, 108)
    sax_pad(band, cc, near-8, 96*4+pos, 1.6, 96)
    band.chord('piano', rootless(cc), 96*4+pos, 1.7, 86, P_PIANO)
    band.n('bass', nearest_pc(cc.root, 40), 96*4+pos, 1.8, 104, P_BASS)
    band.n('drums_kit', SNARE, 96*4+pos, 0.4, 96, K_JAZZ, drum=True)
band.n('drums_kit', T_LO, 96*4+3.0, 0.5, 100, K_JAZZ, drum=True)
band.n('drums_kit', T_FLO, 96*4+3.5, 0.5, 104, K_JAZZ, drum=True)

# bar 97: the final D6/9 — everybody, then let it ring
cf = Chord('D6/9')
band.chord('piano', [50, 57, 62, 66, 69, 73, 76], 97*4, 5.0, 96, P_PIANO, spread=0.02)
band.n('bass', 38, 97*4, 5.0, 108, P_BASS)
band.n('bass', 26, 97*4, 5.0, 96, P_BASS)
for nm, prog, p in (('tpt1',P_TPT,88),('tpt2',P_TPT,83),('tbn1',P_TBN,73),('tbn2',P_TBN,66),
                    ('alto1',P_ALTO,78),('alto2',P_ALTO,73),('tenor1',P_TENOR,69),
                    ('tenor2',P_TENOR,66),('bari',P_BARI,50)):
    band.n(nm, p, 97*4, 3.4, 112, prog)
band.n('drums_kit', CRASH, 97*4, 5.0, 118, K_JAZZ, drum=True)
band.n('drums_kit', CRASH2, 97*4, 5.0, 110, K_JAZZ, drum=True)
band.n('drums_kit', KICK, 97*4, 1.0, 118, K_JAZZ, drum=True)

m = band.write('/home/user/hayeonjo/jazz/jazz_arrangement.mid')
tot = sum(len(i.notes) for i in m.instruments)
print("tracks:")
for i in m.instruments:
    print(f"   {i.name:<12} prog={i.program:<3} drum={int(i.is_drum)}  notes={len(i.notes)}")
print("total notes:", tot, " end time: %.2fs" % m.get_end_time())
