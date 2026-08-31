import numpy as np, librosa, soundfile as sf, json
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
A = json.load(open("work/analysis.json"))
rng = np.random.default_rng(7)

# ---- tape varispeed: -1 semitone, drags tempo 174 -> 164.2 (82.1 half-time) ----
R = 2 ** (-1 / 12)
a_q   = (A["beat_a"] * 2) / R          # half-time quarter note, post-shift
t0    = A["first_downbeat"] / R        # first downbeat, post-shift
bar   = a_q * 4
step  = a_q / 4                        # 16th
print(f"post-shift: {60/a_q:.2f} BPM half-time, bar {bar:.4f}s, downbeat {t0:.4f}s")

def st(x, sos): return sosfilt(sos, x)
def bp(lo, hi): return butter(2, [lo/(SR/2), hi/(SR/2)], btype="band", output="sos")
def lp(f, o=2):  return butter(o, f/(SR/2), btype="low",  output="sos")
def hp(f, o=2):  return butter(o, f/(SR/2), btype="high", output="sos")

# ---------------- bed: harmonic kept, original drums mostly removed ----------------
harm, _ = sf.read("work/harmonic.wav");  harm = harm.T
perc, _ = sf.read("work/percussive.wav"); perc = perc.T
bed = harm + 0.08 * perc                                   # a little transient glue
bed = librosa.resample(bed, orig_sr=SR, target_sr=SR / R, axis=1, res_type="soxr_hq")
NS = bed.shape[1]; dur = NS / SR
print(f"bed stretched to {dur:.2f}s")

# where the original drums played -> where the new kit plays
pg = np.abs(perc).mean(axis=0)
pg = np.sqrt(np.convolve(pg**2, np.ones(int(SR*0.25))/int(SR*0.25), mode="same"))
pg = librosa.resample(pg[None,:], orig_sr=SR, target_sr=SR/R, res_type="soxr_hq")[0]
pg = np.pad(pg, (0, max(0, NS-len(pg))))[:NS]
gate = np.clip((pg / (np.percentile(pg, 90) + 1e-9) - 0.16) / 0.34, 0, 1)

# ---------------- drum synthesis ----------------
def env(n, tau, atk=40): 
    e = np.exp(-np.arange(n)/(tau*SR)); e[:atk] *= np.linspace(0,1,atk); return e
def kick():
    n=int(0.45*SR); t=np.arange(n)/SR
    f=48+95*np.exp(-t/0.028); ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)*env(n,0.17)
    x+=np.sin(2*np.pi*47*t)*env(n,0.22)*0.42                # sub weight
    x+=st(rng.normal(0,1,n)*env(n,0.003),hp(1200))*0.35
    return np.tanh(x*1.7)*0.95
def snare():
    n=int(0.30*SR); t=np.arange(n)/SR
    x=st(rng.normal(0,1,n),bp(180,7500))*env(n,0.085)
    x+=(np.sin(2*np.pi*183*t)+0.6*np.sin(2*np.pi*331*t))*env(n,0.055)*0.55
    return np.tanh(x*1.3)*0.55
def hat(open_=False):
    n=int((0.22 if open_ else 0.055)*SR)
    x=st(rng.normal(0,1,n),hp(7200,4))*env(n,0.115 if open_ else 0.017,atk=12)
    return x*(0.20 if open_ else 0.16)
def rim():
    n=int(0.06*SR); t=np.arange(n)/SR
    return (np.sin(2*np.pi*820*t)*env(n,0.011)+st(rng.normal(0,1,n),bp(2000,6000))*env(n,0.005))*0.30
K,S,H,HO,RM = kick(),snare(),hat(),hat(True),rim()

drums = np.zeros((2, NS+SR)); kick_env = np.zeros(NS+SR)
def place(buf, smp, t, g, pan=0.0):
    i = int(t*SR)
    if i < 0 or i >= buf.shape[1]-len(smp): return
    l,r = g*np.sqrt((1-pan)/2)*1.414, g*np.sqrt((1+pan)/2)*1.414
    buf[0,i:i+len(smp)] += smp*l; buf[1,i:i+len(smp)] += smp*r

SWING = 0.22                                   # offbeat 8ths pushed late
KICK_ST, SNR_ST, HAT_ST = {0,10}, {4,12}, {0,2,4,6,8,10,12,14}
nbars = int((dur - t0)/bar) + 1
for b in range(-2, nbars):
    bt = t0 + b*bar
    g = gate[min(NS-1, max(0, int((bt+bar/2)*SR)))]
    if g < 0.05: continue
    for s in range(16):
        t = bt + s*step + (SWING*step if s % 4 == 2 else 0) + rng.normal(0, 0.0035)
        if s in KICK_ST or (s == 6 and b % 4 == 3):
            place(drums, K, t, g*rng.uniform(0.88,1.0)); 
            i=int(t*SR)
            if 0<=i<NS: kick_env[i]=1.0
        if s in SNR_ST: place(drums, S, t, g*rng.uniform(0.85,1.0))
        if s in HAT_ST:
            v = 1.0 if s % 4 == 0 else 0.62
            if s == 14 and b % 4 == 3: place(drums, HO, t, g*0.9*v, 0.18)
            else: place(drums, H, t, g*v*rng.uniform(0.8,1.0), 0.18)
        if s in (7,15) and b % 2 == 1: place(drums, RM, t, g*0.5, -0.25)
drums = drums[:, :NS]; kick_env = kick_env[:NS]

# ---------------- Rhodes-style FM keys, chords read from the audio ----------------
ymono=librosa.load("work/original.mp3",sr=SR,mono=True)[0]
bassy=st(ymono,bp(55,260))
cb=librosa.feature.chroma_cqt(y=bassy,sr=SR,hop_length=512,
                              fmin=librosa.note_to_hz('C2'),n_octaves=3)
cf=librosa.feature.chroma_cqt(y=librosa.effects.harmonic(ymono),sr=SR,hop_length=512)
ct=librosa.frames_to_time(np.arange(cb.shape[1]),sr=SR,hop_length=512)/R
NN=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

raw=[]
for b in range(nbars):
    bt=t0+b*bar; m=(ct>=bt)&(ct<bt+bar)
    if m.sum()==0: raw.append(None); continue
    vb=cb[:,m].mean(1); vf=cf[:,m].mean(1)
    root=int(np.argmax(vb))
    raw.append((root, 1 if vf[(root+3)%12]>vf[(root+4)%12] else 0))

# the track is loop-based: majority-vote each position of the 4-bar cycle
from collections import Counter
loop=[]
for p in range(4):
    votes=[c for i,c in enumerate(raw) if c and i%4==p]
    loop.append(Counter(votes).most_common(1)[0][0] if votes else None)
print("4-bar loop:", " ".join(NN[r]+('m' if q else '') for r,q in loop),
      "(sounding a semitone lower after the tape shift)")

def voicing(root,minor):
    base=52+((root-4)%12)                              # sits in E3..D#4, under the vocal
    iv=[0,3,7,10] if minor else [0,4,7,11]
    return [base+i-12 if i>8 else base+i for i in iv]
def ep(midi,dur_s,amp):
    n=int(dur_s*SR); t=np.arange(n)/SR
    f=440*2**((midi-69-1)/12)                          # -1 semitone, matching the bed
    e=env(n,0.9,atk=int(0.012*SR)); idx=2.6*np.exp(-t/0.28)+0.25
    x=np.sin(2*np.pi*f*t+idx*np.sin(2*np.pi*f*t))*e
    x+=0.35*np.sin(2*np.pi*f*1.002*t+idx*0.7*np.sin(2*np.pi*f*t))*e
    return x*amp

keys=np.zeros((2,NS+SR))
for b in range(nbars):
    c=loop[b%4]
    if c is None: continue
    g=gate[min(NS-1,max(0,int((t0+b*bar+bar/2)*SR)))]
    if g<0.20: continue
    notes=voicing(*c)
    for hit,ln,amp in ((0.0,bar*0.62,0.115),(bar*0.5+SWING*step,bar*0.42,0.070)):
        for ni,mn in enumerate(notes):
            place(keys,ep(mn,ln,amp*g*rng.uniform(0.9,1.0)),
                  t0+b*bar+hit+ni*0.011,1.0,(ni-1.5)*0.22)
keys=keys[:,:NS]

# ---------------- reverb (decaying-noise IR), vinyl, wow & flutter ----------------
ir_n=int(1.9*SR); ir=rng.normal(0,1,(2,ir_n))*np.exp(-np.arange(ir_n)/(0.42*SR))
ir=np.array([st(st(c,lp(4800)),hp(180)) for c in ir]); ir[:,:int(0.028*SR)]=0
ir/=np.abs(ir).sum(axis=1,keepdims=True)*0.55
def verb(x): return np.array([fftconvolve(x[c],ir[c])[:x.shape[1]] for c in range(2)])

crackle=np.zeros((2,NS))
for c in range(2):
    imp=np.zeros(NS); idx=rng.choice(NS,int(NS/SR*520),replace=False)
    imp[idx]=rng.normal(0,1,len(idx))*rng.uniform(0.2,1.0,len(idx))
    crackle[c]=st(imp,bp(1400,7000))*0.140+st(rng.normal(0,1,NS),bp(300,9000))*0.0090

def wow(x):
    t=np.arange(NS)/SR
    d=(0.0022*np.sin(2*np.pi*0.55*t)+0.0004*np.sin(2*np.pi*6.3*t)+0.0026)*SR
    src=np.arange(NS)-d; i0=np.floor(src).astype(int); fr=src-i0
    i0=np.clip(i0,0,NS-2)
    return np.array([x[c][i0]*(1-fr)+x[c][i0+1]*fr for c in range(2)])

# ---------------- mix ----------------
duck=np.convolve(kick_env,np.exp(-np.arange(int(0.30*SR))/(0.085*SR)),mode="full")[:NS]
duck=1-0.26*np.clip(duck,0,1)

bed=wow(bed)
bed=np.array([st(st(c,lp(11500,3)),hp(38)) for c in bed])
mid=(bed[0]+bed[1])/2; side=(bed[0]-bed[1])/2
side=side+0.45*st(side,hp(800))                              # widen the highs only
bed=np.array([mid+side, mid-side])
mix  = bed*duck*1.00
mix += 0.30*verb(bed*0.35)                       # slowed + reverb air
mix += drums*0.55 + 0.16*verb(drums*np.array([[0.35],[0.35]]))
mix += keys*1.05 + 0.34*verb(keys)
mix += crackle
mix  = np.tanh(mix*1.12)*0.92
mix  = np.array([st(c,lp(13500,2)) for c in mix])

fi=int(1.2*SR); mix[:,:fi]*=np.linspace(0,1,fi); mix[:,-fi:]*=np.linspace(1,0,fi)
mix *= 0.97/np.abs(mix).max()
sf.write("out/as_it_was_lofi.wav", mix.T, SR, subtype="PCM_24")
sf.write("out/preview_45s.wav", mix[:, int(46*SR):int(91*SR)].T, SR, subtype="PCM_24")

def db(x): return 20*np.log10(np.sqrt((x**2).mean())+1e-12)
print(f"\nwrote out/as_it_was_lofi.wav  {mix.shape[1]/SR:.2f}s  peak {np.abs(mix).max():.3f}")
print(f"  drums play over {100*np.mean(gate>0.05):.0f}% of the track")
print(f"  layer RMS  bed {db(bed):.1f}  drums {db(drums*0.55):.1f} "
      f" keys {db(keys*1.05):.1f}  vinyl {db(crackle):.1f}  mix {db(mix):.1f} dBFS")
