"""Mix the rendered big band with the isolated vocal — one room, live-band balance."""
import sys, numpy as np, soundfile as sf, scipy.signal as ss, os
SR=44100; OUT="render"
VOCAL = sys.argv[1] if len(sys.argv)>1 else "stems/vocals.wav"
NOVOX = (VOCAL == "none")
DEST  = sys.argv[2] if len(sys.argv)>2 else "jazz_version.wav"

tracks = np.load(f"{OUT}/_tracks.npy", allow_pickle=True).item()
N = next(iter(tracks.values())).shape[1]

def db(x): return 10**(x/20.0)
def pan(x, p):
    """equal-power pan of a stereo source"""
    m = x.mean(0)
    l = np.cos((p+1)*np.pi/4); r = np.sin((p+1)*np.pi/4)
    return np.stack([m*l*1.414*0.75 + x[0]*0.25, m*r*1.414*0.75 + x[1]*0.25])

#                target active-RMS dBFS, pan, reverb send
MIX = {
 'piano':       (-24.0, -0.26, 0.16),
 'bass':        (-25.5,  0.00, 0.05),
 'drums_brush': (-26.5,  0.06, 0.15),
 'drums_kit':   (-25.0,  0.06, 0.13),
 'guitar':      (-34.0, -0.52, 0.10),
 'mutedtpt':    (-25.0, -0.22, 0.30),
 'tenor_solo':  (-21.0,  0.05, 0.26),
 'tenor1':      (-27.5,  0.22, 0.24),
 'tenor2':      (-30.0,  0.34, 0.24),
 'alto1':       (-27.5, -0.32, 0.24),
 'alto2':       (-30.0, -0.20, 0.24),
 'bari':        (-29.0,  0.46, 0.22),
 'tpt1':        (-26.0, -0.42, 0.26),
 'tpt2':        (-29.0, -0.54, 0.26),
 'tbn1':        (-28.0,  0.42, 0.24),
 'tbn2':        (-30.0,  0.54, 0.24),
}

def active_rms_db(v):
    """Loudness while the instrument is actually playing — the honest way to balance
    parts whose sample sets have wildly different output levels."""
    m = np.abs(v).max(0)
    act = v[:, m > m.max()*0.02]
    if act.size == 0: return -120.0
    return 20*np.log10(np.sqrt((act**2).mean())+1e-12)

def room_ir(sr=SR, rt60=1.35, predelay=0.018, seed=7):
    rng=np.random.default_rng(seed)
    n=int(rt60*sr); t=np.arange(n)/sr
    d=np.exp(-6.9*t/rt60)
    ir=rng.standard_normal((2,n))*d
    # early reflections give the room its size
    for tau,g in ((0.011,0.42),(0.019,0.34),(0.027,0.29),(0.041,0.22),(0.058,0.17),(0.079,0.12)):
        k=int(tau*sr); ir[:,k]+=g
    sos=ss.butter(2,[220/(sr/2),7200/(sr/2)],'bandpass',output='sos')
    ir=ss.sosfilt(sos,ir,axis=1)
    ir=np.pad(ir,((0,0),(int(predelay*sr),0)))
    return ir/np.abs(ir).max()*0.5

IR = room_ir()
def verb(x):
    return np.stack([ss.fftconvolve(x[c],IR[c])[:x.shape[1]] for c in range(2)])

def eq(x, name):
    """Carve room for the voice and keep the low-mids from turning to mud."""
    if name == 'bass':
        x = ss.sosfilt(ss.butter(2, 42/(SR/2), 'highpass', output='sos'), x, axis=1)
    elif name == 'piano':
        x = ss.sosfilt(ss.butter(2, 78/(SR/2), 'highpass', output='sos'), x, axis=1)
        b,a = ss.iirnotch(230/(SR/2), 1.1); x = x*0.72 + ss.lfilter(b,a,x,axis=1)*0.45
    elif name.startswith('drums'):
        x = ss.sosfilt(ss.butter(2, 45/(SR/2), 'highpass', output='sos'), x, axis=1)
    elif name.startswith(('tpt','tbn','alto','tenor','bari','muted')):
        x = ss.sosfilt(ss.butter(2, 150/(SR/2), 'highpass', output='sos'), x, axis=1)
        b,a = ss.iirpeak(2900/(SR/2), 1.6); x = x*0.80 + ss.lfilter(b,a,x,axis=1)*0.30
    elif name == 'guitar':
        x = ss.sosfilt(ss.butter(2, 160/(SR/2), 'highpass', output='sos'), x, axis=1)
    return x

dry=np.zeros((2,N),dtype=np.float32); wet=np.zeros((2,N),dtype=np.float32)
for name,(g,p,s) in MIX.items():
    if name not in tracks: continue
    raw = eq(tracks[name].astype(np.float32), name)
    x = pan(raw, p)*db(g - active_rms_db(raw))
    dry += x; wet += x*s
# ---- section dynamics: a real band does not play everything at one volume ----
BARD = 4*60/172.266
AUTO = [(0,-9.0),(4,-7.0),(12,-6.5),(20,-5.0),(28,-3.0),(32,-0.5),(36,1.5),(44,2.0),
        (52,-7.5),(60,-12.0),(64,-11.0),(68,-7.5),(72,-1.5),(76,2.5),(84,3.0),(92,2.0),(98,2.0)]
env=np.zeros(N,dtype=np.float32)
for i in range(len(AUTO)-1):
    b0,g0=AUTO[i]; b1,g1=AUTO[i+1]
    a=int(b0*BARD*SR); b=min(int(b1*BARD*SR),N)
    if b<=a: continue
    env[a:b]=np.linspace(g0,g1,b-a) if abs(g1-g0)>0 else g0
env[int(AUTO[-1][0]*BARD*SR):]=AUTO[-1][1]
env=ss.lfilter(*ss.butter(2,1.2/(SR/2),'low'),env)          # smooth the moves
gain=db(env)
dry*=gain; wet*=gain
mix = dry + verb(wet)*0.9

# ---- the vocal, placed on the new timeline -------------------------------------
v = np.zeros((2,N),dtype='float32') if NOVOX else sf.read(VOCAL, dtype='float32', always_2d=True)[0].T.astype('float32')
if v.shape[0]==1: v=np.vstack([v,v])
BAR=4*60/172.266
def place(src_a, src_b, tgt_a, fin=0.02, fout=0.30):
    a,b=int(src_a*SR),int(src_b*SR); seg=v[:,a:b].copy()
    ni,no=int(fin*SR),int(fout*SR)
    seg[:,:ni]*=np.linspace(0,1,ni); seg[:,-no:]*=np.linspace(1,0,no)
    t=int(tgt_a*SR); L=min(seg.shape[1], N-t)
    out=np.zeros((2,N),dtype=np.float32); out[:,t:t+L]=seg[:,:L]
    return out

VOX  = place(0.0,   78.10, 16.6952)          # verse 1 -> bridge, moved 12 bars later
VOX += place(33.30, 55.80, 72.4232+33.30)    # the chorus vocal returns for the shout chorus

# the voice rides a gentler curve of its own so the quiet sections stay quiet
VAUTO=[(0,0.0),(12,0.0),(52,-1.5),(60,-3.5),(68,-3.5),(76,0.5),(98,0.5)]
venv=np.zeros(N,dtype=np.float32)
for i in range(len(VAUTO)-1):
    b0,g0=VAUTO[i]; b1,g1=VAUTO[i+1]
    a_=int(b0*BARD*SR); b_=min(int(b1*BARD*SR),N)
    if b_>a_: venv[a_:b_]=np.linspace(g0,g1,b_-a_)
venv[int(VAUTO[-1][0]*BARD*SR):]=VAUTO[-1][1]
venv=ss.lfilter(*ss.butter(2,1.2/(SR/2),'low'),venv)
VOX*=db(venv)
sos=ss.butter(2,150/(SR/2),'highpass',output='sos'); VOX=ss.sosfilt(sos,VOX,axis=1)
# a little air and a plate-ish tail so the voice sits in the same room
b,a=ss.iirpeak(4200/(SR/2),1.2); VOX=ss.lfilter(b,a*1.0,VOX,axis=1)*0.85+VOX*0.35
# put the voice at a fixed loudness relative to the band instead of guessing a fader
VOX *= db(-18.5 - active_rms_db(VOX))
b,a = ss.iirpeak(2500/(SR/2), 1.4); VOX = VOX*0.82 + ss.lfilter(b,a,VOX,axis=1)*0.34   # presence
VOXW = verb(VOX*0.16)

# gentle sidechain: the band leans back a little whenever the singer is on
vd = np.abs(VOX).max(0)
vd = ss.sosfilt(ss.butter(2, 6/(SR/2), 'low', output='sos'), vd)
vd = vd/ (np.percentile(vd, 97)+1e-9)
duck = db(-3.0*np.clip(vd, 0, 1))
mix = mix*duck + VOX + VOXW*0.75

# ---- bus glue ------------------------------------------------------------------
def comp(x, thr=0.55, ratio=1.9, atk=0.010, rel=0.22):
    env=np.abs(x).max(0)
    a=np.exp(-1/(atk*SR)); r=np.exp(-1/(rel*SR))
    e=np.zeros_like(env); g=0.0
    for i in range(len(env)):                      # simple but honest envelope follower
        g = a*g+(1-a)*env[i] if env[i]>g else r*g+(1-r)*env[i]
        e[i]=g
    over=np.maximum(e/thr,1.0)
    return x*(over**(1/ratio-1))
try:
    from numba import njit
except Exception:
    pass
mix = comp(mix)
mix = np.tanh(mix*0.98)*0.99
mix /= max(np.abs(mix).max(),1e-9); mix*=0.94
tail=np.abs(mix).max(0)
last=int(np.max(np.nonzero(tail>2e-4))) if np.any(tail>2e-4) else mix.shape[1]
mix=mix[:, :min(mix.shape[1], last+int(0.5*SR))]
f=int(0.45*SR); mix[:,-f:]*=np.linspace(1,0,f)
sf.write(DEST, mix.T, SR, subtype='PCM_24')
print("wrote", DEST, "%.1fs  peak %.3f  rms %.4f"%(mix.shape[1]/SR, np.abs(mix).max(), np.sqrt((mix**2).mean())))
