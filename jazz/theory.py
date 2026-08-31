"""Jazz harmony helpers: chord parsing, rootless voicings, section voicings, swing grid."""
import random

NOTE_PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
           'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11}

# quality -> (chord tones as semitone offsets, chord-scale offsets)
QUALITY = {
    'maj7':  ([0,4,7,9,11,14],     [0,2,4,7,9,11,14]),        # ionian, 6th allowed
    'maj9':  ([0,4,7,9,11,14],     [0,2,4,7,9,11,14]),
    '6/9':   ([0,4,7,9,14],        [0,2,4,7,9,11,14]),
    'maj7#11':([0,4,7,11,14,18],   [0,2,4,6,7,9,11]),
    'm7':    ([0,3,7,10,14,17],    [0,2,3,5,7,9,10]),         # dorian
    'm9':    ([0,3,7,10,14,17],    [0,2,3,5,7,9,10]),
    'm11':   ([0,3,7,10,14,17],    [0,2,3,5,7,9,10]),
    'm6':    ([0,3,7,9,14],        [0,2,3,5,7,9,11]),
    'm7b5':  ([0,3,6,10,14,17],    [0,2,3,5,6,8,10]),
    '7':     ([0,4,7,9,10,14],     [0,2,4,5,7,9,10]),         # mixolydian (9 & 13)
    '9':     ([0,4,7,9,10,14],     [0,2,4,5,7,9,10]),
    '13':    ([0,4,7,9,10,14],     [0,2,4,5,7,9,10]),
    '7#11':  ([0,4,7,10,14,18,21], [0,2,4,6,7,9,10]),         # lydian dominant
    '7#9':   ([0,4,7,10,15,20],    [0,1,3,4,6,8,10]),         # altered
    '7alt':  ([0,4,10,13,15,20],   [0,1,3,4,6,8,10]),
    '7b9':   ([0,4,7,10,13,21],    [0,1,3,4,6,7,9,10]),       # half-whole
    '7sus':  ([0,5,7,10,14,21],    [0,2,4,5,7,9,10]),
    'dim7':  ([0,3,6,9,14],        [0,2,3,5,6,8,9,11]),
    'maj':   ([0,4,7,14],          [0,2,4,7,9,11,14]),
    'm':     ([0,3,7,14],          [0,2,3,5,7,9,10]),
}

class Chord:
    __slots__=('name','root','qual','tones','scale','bass')
    def __init__(self, name):
        self.name = name
        s = name
        bass = None
        if '/' in s and not s.endswith('6/9'):
            s, b = s.split('/'); bass = NOTE_PC[b]
        i = 1
        if len(s) > 1 and s[1] in '#b': i = 2
        self.root = NOTE_PC[s[:i]]
        q = s[i:] or 'maj'
        if q not in QUALITY:
            q = {'':'maj','M7':'maj7','min7':'m7'}.get(q, q)
        self.qual = q
        self.tones = QUALITY[q][0]
        self.scale = QUALITY[q][1]
        self.bass = bass if bass is not None else self.root

    def pcs(self):
        return sorted({(self.root+t) % 12 for t in self.tones})

    def scale_pcs(self):
        return sorted({(self.root+t) % 12 for t in self.scale})

    def is_dom(self):
        return self.qual.startswith('7') or self.qual in ('9','13')

    def is_minor(self):
        return self.qual.startswith('m') and not self.qual.startswith('maj')


# ---- rootless piano voicings (Bill Evans style, 3rd/7th on top or bottom) ----
def rootless(ch, low=52, high=74, prev=None):
    """Return 4-note rootless voicing (list of midi notes) voice-led from prev."""
    r = ch.root
    if ch.qual in ('maj7','maj9','6/9','maj7#11'):
        sets = [[4,7,11,14],[11,14,16,21],[4,9,11,14]]      # 3-5-7-9 / 7-9-3-6 / 3-6-7-9
    elif ch.qual in ('m7','m9','m11','m6'):
        sets = [[3,7,10,14],[10,14,15,19],[3,5,10,14]]
    elif ch.qual == 'm7b5':
        sets = [[3,6,10,14],[10,13,15,18]]
    elif ch.qual in ('7','9','13','7sus'):
        sets = [[4,9,10,14],[10,14,16,21],[4,7,10,14]]      # 3-13-7-9 / 7-9-3-13
    elif ch.qual in ('7#11',):
        sets = [[4,10,14,18],[10,14,18,21]]
    elif ch.qual in ('7#9','7alt','7b9'):
        sets = [[4,10,15,20],[10,15,20,25],[4,10,13,20]]
    elif ch.qual == 'dim7':
        sets = [[3,6,9,14],[6,9,12,15]]
    else:
        sets = [[4,7,11,14]] if not ch.is_minor() else [[3,7,10,14]]

    best, bestcost = None, 1e9
    for s in sets:
        for oct_ in range(2, 7):
            v = sorted(r + 12*oct_ + x for x in s)
            if v[0] < low or v[-1] > high: continue
            if prev:
                cost = sum(min(abs(n-p) for p in prev) for n in v) + abs(v[-1]-prev[-1])*1.5
            else:
                cost = abs(v[0]-57) + abs(v[-1]-69)
            if cost < bestcost: best, bestcost = v, cost
    if best is None:
        best = sorted(r + 60 + x for x in sets[0])
    return best


def shell(ch, low=45, high=64):
    """3-note guitar shell voicing: root-ish, 3rd, 7th."""
    r = ch.root
    if ch.qual in ('maj7','maj9','6/9','maj7#11'): iv=[0,4,11]
    elif ch.is_minor():                            iv=[0,3,10]
    elif ch.qual=='dim7':                          iv=[0,3,6]
    elif ch.qual in ('7#9','7alt'):                iv=[0,4,10]
    elif ch.qual=='7sus':                          iv=[0,5,10]
    else:                                          iv=[0,4,10]
    for oct_ in range(3,6):
        v = [r+12*oct_+x for x in iv]
        if v[0]>=low and v[-1]<=high: return v
    return [r+48+x for x in iv]


def section_voicing(ch, top, n=5, tight=True):
    """Harmonize `n` parts downward from `top` using chord tones + tensions.
    Classic close-position 'block' / drop-2 sax soli sound."""
    pool = sorted({(ch.root+t) % 12 for t in ch.tones} |
                  ({(ch.root+9)%12} if ch.qual in ('maj7','maj9','6/9') else set()))
    # snap the lead voice onto a chord tone so the section never clashes with the lead
    if top % 12 not in pool:
        top = min((top-2, top-1, top+1, top+2), key=lambda x: (x % 12 not in pool, abs(x-top)))
        if top % 12 not in pool:
            top = min((top+d for d in range(-3,4)), key=lambda x: (x % 12 not in pool, abs(x-top)))
    notes=[top]; cur=top
    while len(notes) < n:
        cur -= 1
        guard = 0
        while cur % 12 not in pool and guard < 12:
            cur -= 1; guard += 1
        # avoid unisons / too-close intervals at the bottom
        if notes[-1]-cur < 2: cur -= 1; continue
        notes.append(cur)
    notes = sorted(notes)
    if not tight and len(notes) >= 3:      # drop-2: 2nd voice from top down an octave
        notes[-2] -= 12
        notes = sorted(notes)
    return notes


def nearest_pc(pc, ref):
    """Midi note with pitch class pc nearest to ref."""
    base = ref - (ref % 12) + pc
    cands = [base-12, base, base+12]
    return min(cands, key=lambda x: abs(x-ref))
