import numpy as np, librosa, soundfile as sf, os, scipy.signal as ss
SRC="/root/.claude/uploads/78895e4a-7b28-5945-8eae-1ed477f41d4b/125a20d2-LG_asitwas_remix.mp3"
OUT="stems"; os.makedirs(OUT,exist_ok=True)
SR=44100; N=4096; H=512
BEAT=60/172.266; BAR=4*BEAT; LOOP=8*BAR; GRID=0.0232

y,sr=librosa.load(SRC,sr=SR,mono=False)
L,R=y[0],y[1]
mid=(L+R)/2.0
pre=int(round(GRID*sr))
x=np.concatenate([np.zeros(max(0,-pre)), mid[max(0,pre):]])   # align t=0 to the downbeat

S=librosa.stft(x,n_fft=N,hop_length=H); M=np.abs(S); PH=np.exp(1j*np.angle(S))
F,T=M.shape
P=int(round(LOOP*sr/H))
print("frames",T,"loop period frames",P)

def loop_bg(Mag,P):
    nrep=int(np.ceil(Mag.shape[1]/P)); pad=nrep*P-Mag.shape[1]
    A=np.pad(Mag,((0,0),(0,pad)),mode='edge').reshape(Mag.shape[0],nrep,P)
    bg=np.median(A,axis=1)
    return np.minimum(Mag,np.tile(bg,(1,nrep))[:,:Mag.shape[1]])

BG=loop_bg(M,P)                       # 8-bar repeating backing
BG=np.maximum(BG,loop_bg(M,P//2))     # also catch the 4-bar drum layer
FG=np.maximum(M-BG,0)
mv=librosa.util.softmask(FG,2.4*BG,power=2.0)
Sv=M*mv

# REPET-SIM: anything that recurs elsewhere in the track is still backing
w=int(librosa.time_to_frames(1.2,sr=sr,hop_length=H))
filt=np.minimum(Sv,librosa.decompose.nn_filter(Sv,aggregate=np.median,metric='cosine',width=w))
Sv=Sv*librosa.util.softmask(Sv-filt,1.8*filt,power=2.0)

# keep the harmonic (sung) part, let a little transient through for consonants
Hm,Pc=librosa.decompose.hpss(Sv,margin=(1.0,3.0))
Sv=Hm+0.35*Pc

v=librosa.istft(Sv*PH,hop_length=H,n_fft=N,length=len(x))
v=np.concatenate([np.zeros(max(0,pre)),v])[:len(mid)]
sos=ss.butter(4,140/(sr/2),'highpass',output='sos'); v=ss.sosfiltfilt(sos,v)
sos=ss.butter(4,11000/(sr/2),'lowpass',output='sos'); v=ss.sosfiltfilt(sos,v)
v=v/np.abs(v).max()*0.9
sf.write(f"{OUT}/vocals2.wav",np.stack([v,v]).T.astype('float32'),sr,subtype='PCM_24')
print("wrote vocals2.wav")

env=librosa.feature.rms(y=v.astype('float32'),frame_length=4096,hop_length=1024)[0]
t=librosa.frames_to_time(np.arange(len(env)),sr=sr,hop_length=1024)
thr=np.percentile(env,55)
on=env>thr; segs=[];st=None
for i,b in enumerate(on):
    if b and st is None: st=t[i]
    if not b and st is not None:
        if t[i]-st>0.5: segs.append((round(st,2),round(t[i],2)))
        st=None
if st is not None: segs.append((round(st,2),round(t[-1],2)))
print("sung phrases (bar# = (t-0.0232)/1.3932):")
for s,e in segs: print(f"  {s:6.2f}->{e:6.2f}  bar {((s-0.0232)/1.3932):5.1f} -> {((e-0.0232)/1.3932):5.1f}")
