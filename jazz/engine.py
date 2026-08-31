"""Big-band writing engine: time/swing grid, walking bass, comping, drums, horn sections."""
import math, random
import pretty_midi as pm
from theory import Chord, rootless, shell, section_voicing, nearest_pc

BPM   = 172.266
BEAT  = 60.0/BPM
BAR   = 4*BEAT
SWING = 0.605          # light swing, appropriate for a medium-up 172

def swing(b):
    """Map a straight beat position to a swung one."""
    i = math.floor(b); f = b - i
    if f < 0.5:  f = f*(SWING/0.5)
    else:        f = SWING + (f-0.5)*((1.0-SWING)/0.5)
    return i + f

class Clock:
    """Beat -> seconds, with an optional ritardando tail."""
    def __init__(self, rit_start=None, rit_end=None, final_ratio=0.62):
        self.rs, self.re, self.fr = rit_start, rit_end, final_ratio
    def __call__(self, b):
        if self.rs is None or b <= self.rs:
            return b*BEAT
        base = self.rs*BEAT
        end  = self.re if self.re is not None else b
        span = max(end-self.rs, 1e-9)
        bb   = min(b, end)
        x    = (bb-self.rs)/span
        # linearly increasing beat duration from 1.0 to 1/final_ratio
        k    = (1.0/self.fr - 1.0)
        base += BEAT*(bb-self.rs)*(1.0 + k*x/2.0)          # integral of linear ramp
        if b > end:
            base += BEAT/self.fr*(b-end)
        return base


class Band:
    HUMAN = {'bass':0.008,'piano':0.011,'guitar':0.007,'drums_kit':0.005,'drums_brush':0.006,
             'tenor_solo':0.016,'mutedtpt':0.014}
    def __init__(self, clock, humanize=True):
        self.clock = clock
        self.humanize = humanize
        self.rnd = random.Random(4242)
        self.tr = {}
        self.order = []
    def track(self, name, program, drum=False):
        if name not in self.tr:
            self.tr[name] = pm.Instrument(program=program, is_drum=drum, name=name)
            self.order.append(name)
        return self.tr[name]
    def n(self, name, pitch, b0, blen, vel, program=0, drum=False, swung=True):
        if pitch is None: return
        pitch = int(max(21, min(108, round(pitch))))
        s = swing(b0) if swung else b0
        e = swing(b0+blen) if swung else b0+blen
        t0, t1 = self.clock(s), self.clock(max(e, s+0.04))
        if self.humanize:
            j = self.HUMAN.get(name, 0.012)
            d = self.rnd.gauss(0, j)
            # horns and the lead voice lay back a hair; the rhythm section drives
            if name.startswith(('tpt','tbn','alto','tenor','bari')): d += 0.006
            t0 = max(0.0, t0+d); t1 = max(t0+0.035, t1+d)
        if t1 - t0 < 0.035: t1 = t0 + 0.035
        self.track(name, program, drum).notes.append(
            pm.Note(velocity=int(max(1, min(127, vel))), pitch=pitch, start=t0, end=t1))
    def chord(self, name, pitches, b0, blen, vel, program=0, spread=0.012):
        """Voicing with a touch of human roll."""
        for i, p in enumerate(sorted(pitches)):
            self.n(name, p, b0 + i*spread, blen - i*spread, vel + random.randint(-4, 4), program)
    def write(self, path, tempo=BPM):
        m = pm.PrettyMIDI(initial_tempo=tempo)
        for k in self.order: m.instruments.append(self.tr[k])
        m.write(path)
        return m


# ---------------- GM programs ----------------
P_PIANO=0; P_BASS=32; P_GTR=26; P_MTPT=59; P_TPT=56; P_TBN=57
P_ALTO=65; P_TENOR=66; P_BARI=67; P_VIB=11
K_BRUSH=40; K_JAZZ=32          # drum kits on channel 10

# GM drum notes
KICK=36; SNARE=38; STICK=37; HHC=42; HHP=44; HHO=46
RIDE=51; BELL=53; CRASH=49; CRASH2=57; SPLASH=55
T_HI=50; T_MID=47; T_LO=43; T_FLO=41


# ---------------- walking bass ----------------
def walk(band, bars, chart, name='bass', vel=94, active=1.0, seed=0):
    """chart: dict bar -> [(beat_in_bar, Chord), ...]. Generates 4 walking quarters/bar."""
    rnd = random.Random(seed)
    prev = 38                                              # around D2
    keys = sorted(chart)
    for bi in bars:
        ev = chart.get(bi)
        if not ev: continue
        nb = next((b for b in keys if b > bi), None)
        nxt_root = chart[nb][0][1].root if nb is not None else ev[0][1].root
        for beat in range(4):
            ch = ev[0][1]
            for pos, c in ev:
                if beat >= pos - 1e-6: ch = c
            if beat == 0:
                p = nearest_pc(ch.root, prev)
                if p > 50: p -= 12
                if p < 29: p += 12
            elif beat == 3:
                # approach the next root chromatically or from a 5th
                tgt_pc = nxt_root if len(ev) == 1 else ev[-1][1].root
                if nb is not None and beat == 3: tgt_pc = nxt_root
                cand = [(tgt_pc+1) % 12, (tgt_pc-1) % 12, (tgt_pc+7) % 12, (tgt_pc+5) % 12]
                p = nearest_pc(rnd.choice(cand[:2] if rnd.random() < .65 else cand), prev)
            else:
                pool = [(ch.root+t) % 12 for t in ch.tones[:4]] + [(ch.root+s) % 12 for s in ch.scale]
                p = nearest_pc(rnd.choice(pool), prev)
            # keep the line inside a real upright range and moving stepwise
            while p < 28: p += 12
            while p > 55: p -= 12
            if abs(p-prev) > 8:  p += -12 if p > prev else 12
            while p < 28: p += 12
            while p > 55: p -= 12
            v = vel + (6 if beat in (0, 2) else 0) + rnd.randint(-5, 5)
            band.n(name, p, bi*4+beat, 0.94, v, P_BASS)
            # occasional swung 8th pickup on 4-and
            if beat == 3 and rnd.random() < 0.22*active:
                band.n(name, p + rnd.choice([-1, 1, 2]), bi*4+3.5, 0.45, v-14, P_BASS)
            prev = p


# ---------------- piano comping ----------------
COMP_SPARSE = [[1.5], [0.5, 2.0], [2.5], [0.0, 2.5]]
COMP_MED    = [[0.5, 2.0], [1.5, 3.0], [0.0, 1.5, 3.5], [2.5, 3.5], [0.5, 1.5, 3.0]]
COMP_DENSE  = [[0.0, 1.5, 2.5, 3.5], [0.5, 1.5, 2.5, 3.0], [0.0, 0.5, 2.0, 3.5], [1.5, 2.0, 3.5]]

def comp(band, bars, chart, name='piano', level='med', vel=68, seed=1, prog=P_PIANO):
    rnd = random.Random(seed)
    pool = {'sparse': COMP_SPARSE, 'med': COMP_MED, 'dense': COMP_DENSE}[level]
    prev = None
    for bi in bars:
        ev = chart.get(bi)
        if not ev: continue
        pat = rnd.choice(pool)
        for pos in pat:
            ch = ev[0][1]
            for p_, c in ev:
                if pos >= p_ - 1e-6: ch = c
            v = rootless(ch, prev=prev); prev = v
            dur = rnd.choice([0.45, 0.6, 0.85, 1.1])
            band.chord(name, v, bi*4+pos, dur, vel + rnd.randint(-8, 8), prog)
        # occasional left-hand root/7th shell for weight
        if rnd.random() < 0.3:
            ch = ev[0][1]
            band.n(name, 36 + ch.root % 12 + (0 if ch.root >= 4 else 12), bi*4, 0.9, vel-22, prog)


def guitar_freddie(band, bars, chart, name='guitar', vel=46, seed=2):
    """Freddie Green: four short shell voicings to the bar."""
    rnd = random.Random(seed)
    for bi in bars:
        ev = chart.get(bi)
        if not ev: continue
        for beat in range(4):
            ch = ev[0][1]
            for p_, c in ev:
                if beat >= p_ - 1e-6: ch = c
            v = shell(ch)
            band.chord(name, v, bi*4+beat, 0.24, vel + (5 if beat in (1, 3) else -3) + rnd.randint(-4, 4),
                       P_GTR, spread=0.004)


# ---------------- drums ----------------
RIDE_PAT = [0.0, 1.0, 1.5, 2.0, 3.0, 3.5]        # ding · ding-a · ding · ding-a

def drums(band, bars, feel='ride', intensity=0.6, seed=3, name=None, fill_every=8,
          crash_bars=(), stop_time=()):
    rnd = random.Random(seed)
    kit  = K_BRUSH if feel == 'brush' else K_JAZZ
    name = name or ('drums_brush' if feel == 'brush' else 'drums_kit')
    def d(note, b, dur, vel):
        band.n(name, note, b, dur, vel, kit, drum=True)
    for k, bi in enumerate(bars):
        if bi in stop_time:
            d(CRASH, bi*4, 0.5, 108); d(KICK, bi*4, 0.4, 112); d(SNARE, bi*4, 0.3, 104)
            continue
        base = 52 + int(46*intensity)
        for pos in RIDE_PAT:
            if feel == 'brush' and pos in (1.5, 3.5) and rnd.random() < 0.35: continue
            v = base + (8 if pos in (0.0, 2.0) else -6) + rnd.randint(-5, 5)
            d(RIDE if feel != 'brush' else HHC, bi*4+pos, 0.4, v)
        # hi-hat "chick" on 2 and 4 — the spine of the swing feel
        for pos in (1.0, 3.0):
            d(HHP, bi*4+pos, 0.3, 62 + int(24*intensity) + rnd.randint(-4, 4))
        # brush sweep on the backbeat
        if feel == 'brush':
            for pos in (0.0, 2.0):
                d(SNARE, bi*4+pos, 0.9, 34 + int(16*intensity) + rnd.randint(-4, 4))
        # feathered kick
        if intensity > 0.45:
            for beat in range(4):
                d(KICK, bi*4+beat, 0.3, 20 + int(12*intensity))
        # snare/kick comping accents
        nacc = 1 + int(round(2.6*intensity))
        for _ in range(nacc):
            if rnd.random() > 0.42 + 0.5*intensity: continue
            pos = rnd.choice([0.5, 1.5, 2.5, 3.5, 2.0, 3.0])
            v = 62 + int(44*intensity) + rnd.randint(-8, 8)
            if rnd.random() < 0.62: d(SNARE, bi*4+pos, 0.3, v)
            else:                   d(KICK,  bi*4+pos, 0.3, v-6)
        if bi in crash_bars:
            d(CRASH, bi*4, 1.2, 96 + int(24*intensity))
        # phrase-ending fill
        if fill_every and (k+1) % fill_every == 0 and k != len(bars)-1:
            fill(band, name, kit, bi, intensity, rnd)

def fill(band, name, kit, bi, intensity, rnd):
    def d(note, b, dur, vel): band.n(name, note, b, dur, vel, kit, drum=True)
    style = rnd.choice(['triplet', 'snare8', 'toms'])
    v0 = 78 + int(40*intensity)
    if style == 'triplet':
        for i, pos in enumerate([2.0, 2.33, 2.66, 3.0, 3.33, 3.66]):
            d(rnd.choice([SNARE, SNARE, T_MID, T_HI]), bi*4+pos, 0.2, v0+i*2, )
    elif style == 'snare8':
        for i, pos in enumerate([3.0, 3.5]):
            d(SNARE, bi*4+pos, 0.25, v0+i*6)
        d(T_LO, bi*4+2.5, 0.25, v0)
    else:
        for i, (nt, pos) in enumerate([(T_HI,2.5),(T_MID,3.0),(T_LO,3.33),(T_FLO,3.66)]):
            d(nt, bi*4+pos, 0.25, v0+i*3)


# ---------------- horns ----------------
def sect_notes(ch, top, n):
    return section_voicing(ch, top, n, tight=(n <= 4))

def brass_stab(band, ch, top, b0, dur, vel, tpt=True, tbn=True):
    """Short, punchy 4-part brass hit."""
    v = sect_notes(ch, top, 4)
    if tpt:
        band.n('tpt1', v[3], b0, dur, vel, P_TPT)
        band.n('tpt2', v[2], b0, dur, vel-6, P_TPT)
    if tbn:
        band.n('tbn1', v[1]-12, b0, dur, vel-4, P_TBN)
        band.n('tbn2', v[0]-12, b0, dur, vel-8, P_TBN)

def sax_pad(band, ch, top, b0, dur, vel):
    """Five-part sax section, close voicing — the warm bed under the brass."""
    v = sect_notes(ch, top, 5)
    for nm, p, dv in (('alto1', v[4], 0), ('alto2', v[3], -5), ('tenor1', v[2], -4),
                      ('tenor2', v[1], -6), ('bari', v[0]-12, -3)):
        prog = P_ALTO if nm.startswith('alto') else (P_TENOR if nm.startswith('tenor') else P_BARI)
        band.n(nm, p, b0, dur, vel+dv, prog)

def line(band, name, prog, events, b0, vel=88, vjit=6):
    """events: [(beat_offset, dur, pitch)] — a single melodic voice."""
    rnd = random.Random(int(b0*97) & 0xffff)
    for off, dur, p in events:
        if p is None: continue
        band.n(name, p, b0+off, dur, vel+rnd.randint(-vjit, vjit), prog)

def sc(ch, deg, near=72):
    """Chord-scale degree -> midi pitch nearest `near`. deg may be negative."""
    s = ch.scale
    o, i = divmod(deg, len(s))
    return nearest_pc((ch.root + s[i]) % 12, near) + 12*o

def ct(ch, idx, near=72):
    """Chord tone by index."""
    t = ch.tones
    return nearest_pc((ch.root + t[idx % len(t)]) % 12, near)
