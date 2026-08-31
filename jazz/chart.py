"""The jazz chart. Source loop is  Bm | Bm | E | E | A | A | D | D  (vi-II7-V7-I in D).
Loop position of a target bar = (bar - 4) % 8, which keeps every section aligned
with the original vocal."""
from theory import Chord

def C(n): return Chord(n)

# loop templates: 8 bars, each a list of (beat_in_bar, chord)
VERSE = [
    [(0,'Bm9')], [(0,'Bm11')], [(0,'E13')], [(0,'Bb7#11')],
    [(0,'A13')], [(0,'A13')], [(0,'Dmaj9')], [(0,'F#m7'),(2,'B7#9')],
]
VERSE_PLAIN = [
    [(0,'Bm9')], [(0,'Bm9')], [(0,'E9')], [(0,'E13')],
    [(0,'A13')], [(0,'A13')], [(0,'Dmaj9')], [(0,'D6/9'),(2,'A13')],
]
PRECHORUS = [
    [(0,'Bm9')], [(0,'Bm11'),(2,'C#m7b5')], [(0,'E13')], [(0,'E7#9'),(2,'Bb13')],
    [(0,'A13')], [(0,'A13'),(2,'Eb7#11')], [(0,'Dmaj9')], [(0,'Em9'),(2,'A7alt')],
]
CHORUS = [
    [(0,'Bm9')], [(0,'Bm11'),(3,'E7#9')], [(0,'E13')], [(0,'E13'),(3,'Bb13')],
    [(0,'A13')], [(0,'A13'),(3,'Eb13')], [(0,'Dmaj9')], [(0,'D6/9'),(2,'Em9'),(3,'A13')],
]
CHORUS2 = [
    [(0,'Bm9')], [(0,'Bm11'),(2,'Bb7#11')], [(0,'E13')], [(0,'E7#9')],
    [(0,'A13')], [(0,'A13'),(2,'Eb7#11')], [(0,'Dmaj9')], [(0,'F#m7'),(2,'B7#9')],
]
BRIDGE = [
    [(0,'Bm9')], [(0,'Bm11')], [(0,'E9')], [(0,'E13')],
    [(0,'A13')], [(0,'A13')], [(0,'Dmaj9')], [(0,'Em9'),(2,'A13')],
]
SOLO = [
    [(0,'Bm9')], [(0,'Bm11'),(2,'Bb7#11')], [(0,'E13')], [(0,'Bb7#11')],
    [(0,'A13')], [(0,'A13'),(2,'Eb7#11')], [(0,'Dmaj9')], [(0,'Em9'),(2,'A7alt')],
]
INTRO4 = [                                   # free 4-bar piano opening
    [(0,'Dmaj9')], [(0,'Bm11')], [(0,'Em9'),(2,'A13')], [(0,'Dmaj9'),(2,'D#dim7')],
]

# ---- section map: (start_bar, n_bars, name, template) ----
SECTIONS = [
    (0,  4,  'intro_piano',  INTRO4),
    (4,  8,  'intro_band',   VERSE_PLAIN),
    (12, 8,  'verse1a',      VERSE_PLAIN),
    (20, 8,  'verse1b',      VERSE),
    (28, 8,  'prechorus',    PRECHORUS),
    (36, 8,  'chorus1a',     CHORUS),
    (44, 8,  'chorus1b',     CHORUS2),
    (52, 8,  'verse2',       VERSE),
    (60, 8,  'bridge',       BRIDGE),
    (68, 8,  'sax_solo',     SOLO),
    (76, 8,  'final1',       CHORUS),
    (84, 8,  'final2',       CHORUS2),
    (92, 6,  'ending',       [[(0,'Bm9')],[(0,'E13')],[(0,'A13')],[(0,'Dmaj9')],
                              [(0,'Em9'),(2,'A13')],[(0,'D6/9')]]),
]
TOTAL_BARS = 98

def build():
    chart, secof = {}, {}
    for start, n, name, tpl in SECTIONS:
        for i in range(n):
            bar = start + i
            if name == 'intro_piano':   slot = i
            elif name == 'ending':      slot = i
            else:                       slot = (bar - 4) % 8
            chart[bar] = [(b, C(c)) for b, c in tpl[slot % len(tpl)]]
            secof[bar] = name
    return chart, secof

if __name__ == '__main__':
    ch, so = build()
    for b in range(TOTAL_BARS):
        if b % 4 == 0: print()
        print(f"  bar{b:>3} [{so.get(b,'-'):>12}]  " + " | ".join(f"{p}:{c.name}" for p, c in ch[b]))
